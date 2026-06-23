from pydantic import BaseModel

from ..models import Source


class SourceModel(BaseModel):
    subject: str
    session: int
    page: int
    source: str

    @classmethod
    def from_source(cls, s: Source) -> "SourceModel":
        return cls(subject=s.subject, session=s.session, page=s.page + 1, source=s.source)


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
