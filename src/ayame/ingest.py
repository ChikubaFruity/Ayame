import re
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from loguru import logger

from .config import settings
from .models import Chunk, ChunkMetadata
from . import retriever


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    pages = []
    doc = pymupdf.open(str(pdf_path))
    for page_num, page in enumerate(doc):
        text = page.get_text()
        if not text.strip():
            logger.warning(f"Page {page_num + 1}: no text found (possibly scanned)")
            continue
        pages.append((page_num, text))
    doc.close()
    return pages


def chunk_text(text: str, page: int, size: int, overlap: int) -> list[tuple[int, str]]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks = []
    start = 0
    while start < len(normalized):
        end = start + size
        chunk = normalized[start:end]
        chunks.append((page, chunk))
        if end >= len(normalized):
            break
        start += size - overlap

    return chunks


def prepare_chunks(pdf_path: Path, subject: str, session: int) -> list[Chunk]:
    ingested_at = datetime.now(timezone.utc).isoformat()
    source = pdf_path.name

    pages = extract_pages(pdf_path)
    if not pages:
        logger.error(f"No text extracted from {pdf_path.name}")
        return []

    raw_chunks: list[tuple[int, str]] = []
    for page_num, text in pages:
        raw_chunks.extend(
            chunk_text(text, page_num, settings.chunking.size, settings.chunking.overlap)
        )

    return [
        Chunk(
            text=chunk_text_,
            metadata=ChunkMetadata(
                subject=subject,
                session=session,
                page=page_num,
                source=source,
                ingested_at=ingested_at,
            ),
            chunk_index=i,
        )
        for i, (page_num, chunk_text_) in enumerate(raw_chunks)
    ]
