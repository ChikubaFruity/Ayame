from pydantic import BaseModel

from ..models import Source


class SourceModel(BaseModel):
    subject: str
    session: int
    page: int
    source: str
    start: float = 0.0
    kind: str = "pdf"

    @classmethod
    def from_source(cls, s: Source) -> "SourceModel":
        page = s.page if s.kind == "media" else s.page + 1
        return cls(
            subject=s.subject,
            session=s.session,
            page=page,
            source=s.source,
            start=s.start,
            kind=s.kind,
        )


class IngestResponse(BaseModel):
    source: str
    chunks: int


class QueryRequest(BaseModel):
    question: str
    top_k: int | None = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceModel]


class DocumentModel(BaseModel):
    subject: str
    session: int
    source: str
    chunks: int
