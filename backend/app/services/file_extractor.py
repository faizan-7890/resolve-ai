"""
File extraction service for the ResolveAI knowledge base ingestor.
Supports PDF, DOCX, and plain text file types.
"""
import io
import logging

logger = logging.getLogger(__name__)


def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """
    Extracts plain text from uploaded file bytes.

    Supports:
      - PDF files (.pdf) via pypdf
      - Word documents (.docx) via python-docx
      - Plain text files (.txt, .md, .csv, etc.)

    Args:
        file_bytes: Raw bytes of the uploaded file
        filename: Original filename (used to determine file type)

    Returns:
        Extracted plain text string

    Raises:
        ValueError: If the file type is unsupported or extraction fails
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    elif filename_lower.endswith(".docx"):
        return _extract_docx(file_bytes)
    elif any(filename_lower.endswith(ext) for ext in [".txt", ".md", ".csv", ".log", ".rst"]):
        return _extract_text(file_bytes)
    else:
        raise ValueError(
            f"Unsupported file type: '{filename}'. "
            "Supported formats: PDF (.pdf), Word (.docx), plain text (.txt, .md, .csv, .log)"
        )


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
        full_text = "\n\n".join(pages)
        if not full_text.strip():
            raise ValueError("PDF appears to contain no extractable text (may be image-based/scanned).")
        return full_text
    except ImportError:
        raise ValueError("PDF extraction requires 'pypdf'. Install it with: pip install pypdf")
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError(f"Failed to extract text from PDF: {e}")


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from a Word .docx file using python-docx."""
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        if not full_text.strip():
            raise ValueError("DOCX file appears to be empty.")
        return full_text
    except ImportError:
        raise ValueError("DOCX extraction requires 'python-docx'. Install it with: pip install python-docx")
    except Exception as e:
        logger.error(f"DOCX extraction error: {e}")
        raise ValueError(f"Failed to extract text from DOCX: {e}")


def _extract_text(file_bytes: bytes) -> str:
    """Decode plain text file bytes."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            return file_bytes.decode("latin-1")
        except Exception as e:
            raise ValueError(f"Failed to decode text file: {e}")
