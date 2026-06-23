from __future__ import annotations

from collections.abc import Callable

from loguru import logger

import chromadb
import ollama

from .config import settings
from .models import Chunk, RetrievedChunk, ChunkMetadata

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(settings.chroma_path))
        _collection = _client.get_or_create_collection(
            name=settings.chroma.collection,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


_EMBED_BATCH = 4


def embed_texts(texts: list[str]) -> list[list[float]]:
    response = ollama.embed(model=settings.models.embed, input=texts)
    return response.embeddings


def embed_chunks(
    chunks: list[Chunk],
    batch_size: int = _EMBED_BATCH,
    on_progress: Callable[[int], None] | None = None,
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        embeddings.extend(embed_texts([c.text for c in batch]))
        if on_progress:
            on_progress(len(batch))
    return embeddings


def delete_source(source: str) -> None:
    collection = _get_collection()
    existing = collection.get(where={"source": source}, limit=1)
    if existing["ids"]:
        logger.info(f"Re-ingesting '{source}': removing existing chunks")
        collection.delete(where={"source": source})


def store_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    if not chunks:
        return

    collection = _get_collection()
    ids = [f"{c.metadata.source}_{c.chunk_index}" for c in chunks]
    metadatas = [
        {
            "subject": c.metadata.subject,
            "session": c.metadata.session,
            "page": c.metadata.page,
            "source": c.metadata.source,
            "ingested_at": c.metadata.ingested_at,
        }
        for c in chunks
    ]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=metadatas,
    )
    logger.info(f"Stored {len(chunks)} chunks in ChromaDB")


def list_documents() -> list[dict]:
    collection = _get_collection()
    if collection.count() == 0:
        return []

    result = collection.get(include=["metadatas"])
    docs: dict[str, dict] = {}
    for meta in result["metadatas"]:
        key = meta["source"]
        if key not in docs:
            docs[key] = {
                "subject": meta["subject"],
                "session": int(meta["session"]),
                "source": meta["source"],
                "chunks": 0,
            }
        docs[key]["chunks"] += 1
    return sorted(docs.values(), key=lambda d: (d["subject"], d["session"]))


def search(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    k = top_k if top_k is not None else settings.retrieval.top_k
    collection = _get_collection()

    if collection.count() == 0:
        return []

    query_embedding = embed_texts([query])[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    retrieved = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        retrieved.append(
            RetrievedChunk(
                text=doc,
                metadata=ChunkMetadata(
                    subject=meta["subject"],
                    session=int(meta["session"]),
                    page=int(meta["page"]),
                    source=meta["source"],
                    ingested_at=meta["ingested_at"],
                ),
                distance=dist,
            )
        )

    return retrieved
