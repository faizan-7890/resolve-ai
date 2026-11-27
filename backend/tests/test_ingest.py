"""
Knowledge base ingestion tests: JSON ingestion, file upload (.txt, .md, .docx),
validation, document listing, and admin-only deletion.
"""
import io
import sys
import types


def _make_docx_bytes(text: str) -> bytes:
    import docx

    document = docx.Document()
    document.add_paragraph(text)
    buf = io.BytesIO()
    document.save(buf)
    return buf.getvalue()


def test_ingest_json_document_success(client, auth_headers):
    res = client.post(
        "/api/ingest/",
        headers=auth_headers,
        json={
            "title": "Billing Policy Overview",
            "content": "Standard subscriptions renew monthly. Refunds are available within 30 days of purchase.",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["document_id"] >= 1
    assert data["chunks_count"] >= 1


def test_ingest_json_validation_error(client, auth_headers):
    res = client.post(
        "/api/ingest/",
        headers=auth_headers,
        json={"title": "Hi", "content": "Too short"},
    )
    assert res.status_code == 422


def test_upload_txt_and_md_documents(client, auth_headers):
    txt_content = b"Password reset links expire after 15 minutes. Request a new link from login."
    txt_res = client.post(
        "/api/ingest/upload",
        headers=auth_headers,
        files={"file": ("password_guide.txt", txt_content, "text/plain")},
    )
    assert txt_res.status_code == 201
    assert txt_res.json()["document_title"] == "password guide"
    assert txt_res.json()["chunks_count"] >= 1

    md_content = b"# SLA Policy\n\nEnterprise SLA guarantees 99.9% uptime and 1-hour escalation."
    md_res = client.post(
        "/api/ingest/upload",
        headers=auth_headers,
        files={"file": ("enterprise-sla.md", md_content, "text/markdown")},
    )
    assert md_res.status_code == 201
    assert md_res.json()["document_title"] == "enterprise sla"
    assert md_res.json()["chunks_count"] >= 1


def test_upload_docx_document(client, auth_headers, monkeypatch):
    try:
        docx_bytes = _make_docx_bytes(
            "Enterprise SLA guarantees 99.9% uptime and priority 1-hour incident escalation."
        )
    except ImportError:
        # Fallback stub if native lxml DLL loading is restricted in host sandbox
        fake_docx = types.ModuleType("docx")

        class _FakePara:
            def __init__(self, text):
                self.text = text

        class _FakeDoc:
            def __init__(self, _stream):
                self.paragraphs = [
                    _FakePara("Enterprise SLA guarantees 99.9% uptime and priority 1-hour incident escalation.")
                ]

        fake_docx.Document = _FakeDoc
        monkeypatch.setitem(sys.modules, "docx", fake_docx)
        docx_bytes = b"PK\x03\x04stub-docx-bytes"

    docx_res = client.post(
        "/api/ingest/upload",
        headers=auth_headers,
        files={
            "file": (
                "enterprise-sla.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert docx_res.status_code == 201
    assert docx_res.json()["document_title"] == "enterprise sla"
    assert docx_res.json()["chunks_count"] >= 1


def test_upload_rejects_empty_and_unsupported_files(client, auth_headers):
    empty_res = client.post(
        "/api/ingest/upload",
        headers=auth_headers,
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert empty_res.status_code == 400

    bad_type_res = client.post(
        "/api/ingest/upload",
        headers=auth_headers,
        files={"file": ("malware.exe", b"MZ\x90\x00binary", "application/octet-stream")},
    )
    assert bad_type_res.status_code == 422


def test_list_and_admin_only_delete_document(client, auth_headers, admin_headers):
    ingest_res = client.post(
        "/api/ingest/",
        headers=auth_headers,
        json={
            "title": "Shipping Policy",
            "content": "Standard shipping takes 3 to 5 business days across the continental region.",
        },
    )
    doc_id = ingest_res.json()["document_id"]

    list_res = client.get("/api/ingest/documents", headers=auth_headers)
    assert list_res.status_code == 200
    assert any(d["id"] == doc_id for d in list_res.json())

    # Standard user cannot delete
    forbidden_res = client.delete(f"/api/ingest/documents/{doc_id}", headers=auth_headers)
    assert forbidden_res.status_code == 403

    # Admin can delete
    delete_res = client.delete(f"/api/ingest/documents/{doc_id}", headers=admin_headers)
    assert delete_res.status_code == 200

    # Deleting again yields 404
    missing_res = client.delete(f"/api/ingest/documents/{doc_id}", headers=admin_headers)
    assert missing_res.status_code == 404
