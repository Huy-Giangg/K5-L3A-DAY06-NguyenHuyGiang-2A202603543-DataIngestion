"""Read and normalize source data."""
import unicodedata
from pathlib import Path
import pypdf
from .models import DocumentPage


def normalize_text(text: str) -> str:
    """Normalize Unicode and clean excessive whitespace without discarding paragraph structure."""
    if not text:
        return ""
    # Normalize unicode to NFKC
    normalized = unicodedata.normalize("NFKC", text)
    # Replace non-breaking spaces
    normalized = normalized.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    # Clean up horizontal whitespace line-by-line
    lines = [line.strip() for line in normalized.split("\n")]
    cleaned = "\n".join(lines)
    # Collapse 3+ newlines to 2
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned.strip()


def load_pdf(
    path: Path,
    document_id: str,
    source: str,
    start_page: int = 21,
    end_page: int = 55
) -> list[DocumentPage]:
    """Extract pages from start_page to end_page (1-based physical index); retain metadata."""
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    reader = pypdf.PdfReader(str(path))
    total_physical_pages = len(reader.pages)
    end_page = min(end_page, total_physical_pages)

    pages: list[DocumentPage] = []
    empty_pages = []

    for p in range(start_page - 1, end_page):
        physical_page_num = p + 1
        raw_text = reader.pages[p].extract_text() or ""
        text = normalize_text(raw_text)

        if len(text) < 50:
            empty_pages.append(physical_page_num)

        # Assign structured metadata
        chapter = "Key Takeaways" if physical_page_num <= 24 else "Chapter 1"
        section = "Executive Summary" if physical_page_num <= 24 else "External Debt Trends"

        page_obj = DocumentPage(
            document_id=document_id,
            source=source,
            page=physical_page_num,
            text=text,
            metadata={
                "chapter": chapter,
                "section": section,
                "char_count": len(text)
            }
        )
        pages.append(page_obj)

    if empty_pages:
        print(f"[Ingestion Notice] Empty or minimal text on pages: {empty_pages}")

    return pages
