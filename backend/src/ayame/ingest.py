import bisect
import re
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from loguru import logger

from .config import settings
from .models import Chunk, ChunkMetadata
from . import retriever, transcribe


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


def chunk_segments(
    segments: list[tuple[float, str]], size: int, overlap: int
) -> list[tuple[float, str]]:
    # セグメントを正規化して連結しつつ、char位置→開始秒の対応表を作る
    offsets: list[int] = []
    starts: list[float] = []
    parts: list[str] = []
    pos = 0
    for start_sec, text in segments:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            continue
        if parts:
            pos += 1  # 連結時の空白分
        offsets.append(pos)
        starts.append(start_sec)
        parts.append(normalized)
        pos += len(normalized)

    full = " ".join(parts)
    if not full:
        return []

    chunks: list[tuple[float, str]] = []
    cursor = 0
    while cursor < len(full):
        end = cursor + size
        # cursor位置以下の最後のセグメント開始秒を採用
        idx = bisect.bisect_right(offsets, cursor) - 1
        start_sec = starts[max(idx, 0)]
        chunks.append((start_sec, full[cursor:end]))
        if end >= len(full):
            break
        cursor += size - overlap

    return chunks


def prepare_chunks(path: Path, subject: str, session: int) -> list[Chunk]:
    ingested_at = datetime.now(timezone.utc).isoformat()
    source = path.name
    suffix = path.suffix.lower()

    # (page, start, kind, text) に正規化してから Chunk 化
    located: list[tuple[int, float, str, str]] = []
    if suffix in transcribe.MEDIA_EXTS:
        segments = transcribe.transcribe(path)
        for start_sec, chunk in chunk_segments(
            segments, settings.chunking.size, settings.chunking.overlap
        ):
            located.append((0, start_sec, "media", chunk))
    else:
        pages = extract_pages(path)
        if not pages:
            logger.error(f"No text extracted from {path.name}")
            return []
        for page_num, text in pages:
            for page, chunk in chunk_text(
                text, page_num, settings.chunking.size, settings.chunking.overlap
            ):
                located.append((page, 0.0, "pdf", chunk))

    return [
        Chunk(
            text=chunk_text_,
            metadata=ChunkMetadata(
                subject=subject,
                session=session,
                page=page,
                source=source,
                ingested_at=ingested_at,
                start=start_sec,
                kind=kind,
            ),
            chunk_index=i,
        )
        for i, (page, start_sec, kind, chunk_text_) in enumerate(located)
    ]
