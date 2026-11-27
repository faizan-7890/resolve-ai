"""
RAG query, LangGraph triage (sync & SSE stream), ticket authorization (IDOR),
pagination, export headers, and knowledge-base logback tests.
"""
import json
from app.api.routes import tickets as tickets_route
from app.models.document import Document


def test_direct_query_and_validation(client, auth_headers):
    client.post(
        "/api/ingest/",
        headers=auth_headers,
        json={
            "title": "Headquarters Policy",
            "content": "Our main headquarters is located at 100 Innovation Way, Suite 400, San Francisco, CA.",
        },
    )

    res = client.post(
        "/api/query/",
        headers=auth_headers,
        json={"query": "What is the headquarters mailing address?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["decision"] in {"Answer", "Clarify", "Escalate"}
    assert isinstance(data["retrieved_context"], list)

    empty_res = client.post("/api/query/", headers=auth_headers, json={})
    assert empty_res.status_code == 422


def test_sync_diagnose_triage_paths_and_kb_logback(client, auth_headers, db):
    # Answer path -> Resolved + logged back to KB
    t1 = client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Headquarters mailing address",
            "description": "Where is the corporate headquarters mailing address located?",
            "category": "General",
            "urgency": "Low",
        },
    ).json()

    diag_res = client.post(f"/api/tickets/{t1['id']}/diagnose", headers=auth_headers)
    assert diag_res.status_code == 200
    assert diag_res.json()["decision"] == "Answer"

    detail = client.get(f"/api/tickets/{t1['id']}", headers=auth_headers).json()
    assert detail["status"] == "Resolved"
    assert detail["resolution"]
    assert db.query(Document).filter(Document.title.like(f"Resolved Ticket #{t1['id']}:%")).first() is not None

    # Clarify path -> Awaiting Clarification
    t2 = client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Confused about plan",
            "description": "I am confused about how this works, please explain.",
            "category": "General",
            "urgency": "Medium",
        },
    ).json()
    diag2 = client.post(f"/api/tickets/{t2['id']}/diagnose", headers=auth_headers)
    assert diag2.status_code == 200
    assert diag2.json()["decision"] == "Clarify"
    assert client.get(f"/api/tickets/{t2['id']}", headers=auth_headers).json()["status"] == "Awaiting Clarification"

    # Escalate path -> Escalated
    t3 = client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Billing refund escalation",
            "description": "Please escalate this to a human manager for a billing refund.",
            "category": "Billing",
            "urgency": "High",
        },
    ).json()
    diag3 = client.post(f"/api/tickets/{t3['id']}/diagnose", headers=auth_headers)
    assert diag3.status_code == 200
    assert diag3.json()["decision"] == "Escalate"
    assert client.get(f"/api/tickets/{t3['id']}", headers=auth_headers).json()["status"] == "Escalated"


def test_sse_stream_diagnose_persists_once_without_duplicate_run(client, auth_headers, db, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("run_agent_triage should not be called by /diagnose/stream")

    monkeypatch.setattr(tickets_route, "run_agent_triage", fail_if_called)

    ticket = client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Office address inquiry",
            "description": "Can you confirm the office address for corporate mail?",
            "category": "General",
            "urgency": "Low",
        },
    ).json()

    events = []
    with client.stream("GET", f"/api/tickets/{ticket['id']}/diagnose/stream", headers=auth_headers) as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))

    steps = [e["step"] for e in events]
    assert "retrieval" in steps
    assert "evaluator" in steps
    assert steps[-1] == "complete"
    assert events[-1]["decision"] == "Answer"

    detail = client.get(f"/api/tickets/{ticket['id']}", headers=auth_headers).json()
    assert detail["status"] == "Resolved"
    assert detail["resolution"] == events[-1]["response"]
    assert db.query(Document).filter(Document.title.like(f"Resolved Ticket #{ticket['id']}:%")).first() is not None


def test_ticket_similar_activity_and_export_headers(client, auth_headers):
    ticket = client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Exportable ticket",
            "description": "Testing similar matches, activity logs, and markdown export.",
            "category": "Technical",
            "urgency": "Medium",
        },
    ).json()

    sim_res = client.get(f"/api/tickets/{ticket['id']}/similar", headers=auth_headers)
    assert sim_res.status_code == 200
    assert isinstance(sim_res.json(), list)

    act_res = client.get(f"/api/tickets/{ticket['id']}/activity", headers=auth_headers)
    assert act_res.status_code == 200
    assert len(act_res.json()) >= 1

    exp_res = client.get(f"/api/tickets/{ticket['id']}/export", headers=auth_headers)
    assert exp_res.status_code == 200
    assert exp_res.headers["content-disposition"] == f'attachment; filename="resolveai-ticket-{ticket["id"]}.md"'
    assert "Exportable ticket" in exp_res.text


def test_ticket_idor_isolation_and_admin_access(client, auth_headers, second_auth_headers, admin_headers):
    ticket = client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Private user ticket",
            "description": "Only owner and admin should access or modify this ticket.",
            "category": "General",
            "urgency": "Low",
        },
    ).json()
    tid = ticket["id"]

    # Another standard user is blocked across every ticket endpoint
    assert client.get(f"/api/tickets/{tid}", headers=second_auth_headers).status_code == 403
    assert client.post(f"/api/tickets/{tid}/diagnose", headers=second_auth_headers).status_code == 403
    assert client.get(f"/api/tickets/{tid}/diagnose/stream", headers=second_auth_headers).status_code == 403
    assert client.post(f"/api/tickets/{tid}/clarify/generate", headers=second_auth_headers).status_code == 403
    assert client.post(f"/api/tickets/{tid}/clarify", headers=second_auth_headers, json={"answer": "hijack"}).status_code == 403
    assert client.post(f"/api/tickets/{tid}/clarify/answer", headers=second_auth_headers, json={"answers": []}).status_code == 403
    assert client.get(f"/api/tickets/{tid}/similar", headers=second_auth_headers).status_code == 403
    assert client.get(f"/api/tickets/{tid}/activity", headers=second_auth_headers).status_code == 403
    assert client.get(f"/api/tickets/{tid}/export", headers=second_auth_headers).status_code == 403
    assert client.delete(f"/api/tickets/{tid}", headers=second_auth_headers).status_code == 403

    # Admin can inspect
    assert client.get(f"/api/tickets/{tid}", headers=admin_headers).status_code == 200


def test_ticket_list_pagination_and_backward_compatibility(client, auth_headers):
    for idx in range(3):
        res = client.post(
            "/api/tickets/",
            headers=auth_headers,
            json={
                "title": f"Paginated ticket {idx}",
                "description": f"Pagination test payload number {idx} with enough text.",
                "category": "General",
                "urgency": "Low",
            },
        )
        assert res.status_code == 201

    # Unpaginated returns list + X-Total-Count header
    list_res = client.get("/api/tickets/", headers=auth_headers)
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)
    assert int(list_res.headers["x-total-count"]) >= 3

    # Paginated returns structured envelope
    page_res = client.get("/api/tickets/?page=1&limit=2", headers=auth_headers)
    assert page_res.status_code == 200
    body = page_res.json()
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["limit"] == 2
    assert body["total"] >= 3
    assert body["pages"] >= 2
