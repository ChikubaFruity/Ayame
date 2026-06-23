import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sse_starlette.sse import EventSourceResponse

from .. import generator, retriever
from .. import ingest as ingest_module
from .schemas import (
    DocumentModel,
    IngestResponse,
    QueryRequest,
    QueryResponse,
    SourceModel,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/documents", response_model=list[DocumentModel])
def documents() -> list[DocumentModel]:
    return [DocumentModel(**d) for d in retriever.list_documents()]


@router.post("/ingest", response_model=IngestResponse)
async def ingest(
    file: UploadFile = File(...),
    subject: str = Form(...),
    session: int = Form(...),
) -> IngestResponse:
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDFファイルのみ対応しています")

    with tempfile.TemporaryDirectory() as tmp:
        pdf_path = Path(tmp) / file.filename
        pdf_path.write_bytes(await file.read())

        chunks = ingest_module.prepare_chunks(pdf_path, subject, session)
        if not chunks:
            raise HTTPException(
                status_code=422,
                detail="テキストを抽出できませんでした（スキャンPDFの可能性）",
            )

        retriever.delete_source(pdf_path.name)
        embeddings = retriever.embed_chunks(chunks)
        retriever.store_chunks(chunks, embeddings)

    return IngestResponse(source=file.filename, chunks=len(chunks))


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    chunks = retriever.search(req.question, top_k=req.top_k)
    if not chunks:
        return QueryResponse(answer="関連する資料が見つかりませんでした。", sources=[])

    answer = generator.generate_answer(req.question, chunks)
    sources = [SourceModel.from_source(s) for s in generator.collect_sources(chunks)]
    return QueryResponse(answer=answer, sources=sources)


@router.get("/chat")
def chat(question: str, top_k: int | None = None) -> EventSourceResponse:
    chunks = retriever.search(question, top_k=top_k)

    def event_stream():
        if not chunks:
            yield {"event": "token", "data": "関連する資料が見つかりませんでした。"}
            yield {"event": "sources", "data": json.dumps([])}
            yield {"event": "done", "data": ""}
            return

        for token in generator.generate_stream(question, chunks):
            yield {"event": "token", "data": token}

        sources = [
            SourceModel.from_source(s).model_dump()
            for s in generator.collect_sources(chunks)
        ]
        yield {"event": "sources", "data": json.dumps(sources, ensure_ascii=False)}
        yield {"event": "done", "data": ""}

    return EventSourceResponse(event_stream())
