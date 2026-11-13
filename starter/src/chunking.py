"""Implement fixed-size and structure-aware chunking."""
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int = 500, overlap: int = 50) -> list[Chunk]:
    """Split text into fixed-size overlapping character windows while retaining metadata."""
    text = page.text
    if not text:
        return []

    chunks: list[Chunk] = []
    step = max(1, size - overlap)
    idx = 0
    start = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunk_text = text[start:end].strip()

        if len(chunk_text) >= 20:  # Avoid empty/noise chunks
            idx += 1
            chunk_id = f"{page.document_id}_p{page.page}_fix_{idx:03d}"
            chunk_metadata = dict(page.metadata)
            chunk_metadata["strategy"] = "fixed_size"
            chunk_metadata["chunk_index"] = idx

            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata=chunk_metadata,
                )
            )

        if end == len(text):
            break
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int = 800) -> list[Chunk]:
    """Split text by natural paragraphs, merging short ones and respecting sentence boundaries."""
    text = page.text
    if not text:
        return []

    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not raw_paragraphs:
        raw_paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    grouped_blocks: list[str] = []
    current_block = ""

    for para in raw_paragraphs:
        if not current_block:
            current_block = para
        elif len(current_block) + len(para) + 2 <= max_size:
            current_block += "\n\n" + para
        else:
            grouped_blocks.append(current_block)
            current_block = para

    if current_block:
        grouped_blocks.append(current_block)

    chunks: list[Chunk] = []
    idx = 0

    for block in grouped_blocks:
        # If block is still oversized, break by sentences
        if len(block) > max_size:
            sentences = block.split(". ")
            sub_block = ""
            for s in sentences:
                s_with_dot = s if s.endswith(".") else s + "."
                if not sub_block:
                    sub_block = s_with_dot
                elif len(sub_block) + len(s_with_dot) + 1 <= max_size:
                    sub_block += " " + s_with_dot
                else:
                    idx += 1
                    chunk_id = f"{page.document_id}_p{page.page}_para_{idx:03d}"
                    meta = dict(page.metadata)
                    meta["strategy"] = "by_paragraph"
                    meta["chunk_index"] = idx
                    chunks.append(
                        Chunk(
                            chunk_id=chunk_id,
                            document_id=page.document_id,
                            source=page.source,
                            page=page.page,
                            text=sub_block.strip(),
                            metadata=meta,
                        )
                    )
                    sub_block = s_with_dot
            if sub_block:
                idx += 1
                chunk_id = f"{page.document_id}_p{page.page}_para_{idx:03d}"
                meta = dict(page.metadata)
                meta["strategy"] = "by_paragraph"
                meta["chunk_index"] = idx
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=page.document_id,
                        source=page.source,
                        page=page.page,
                        text=sub_block.strip(),
                        metadata=meta,
                    )
                )
        else:
            idx += 1
            chunk_id = f"{page.document_id}_p{page.page}_para_{idx:03d}"
            meta = dict(page.metadata)
            meta["strategy"] = "by_paragraph"
            meta["chunk_index"] = idx
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=block.strip(),
                    metadata=meta,
                )
            )

    return chunks
