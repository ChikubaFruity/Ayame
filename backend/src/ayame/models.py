from dataclasses import dataclass, field


@dataclass
class ChunkMetadata:
    subject: str
    session: int
    page: int
    source: str
    ingested_at: str
    start: float = 0.0
    kind: str = "pdf"


@dataclass
class Chunk:
    text: str
    metadata: ChunkMetadata
    chunk_index: int


@dataclass
class RetrievedChunk:
    text: str
    metadata: ChunkMetadata
    distance: float


@dataclass
class Source:
    subject: str
    session: int
    page: int
    source: str
    start: float = 0.0
    kind: str = "pdf"
