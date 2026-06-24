import tomllib
from pathlib import Path

from pydantic import BaseModel


class ModelSettings(BaseModel):
    generate: str
    embed: str


class GenerationSettings(BaseModel):
    temperature: float
    top_p: float
    top_k: int


class ChunkingSettings(BaseModel):
    size: int
    overlap: int


class WhisperSettings(BaseModel):
    model: str
    device: str
    compute_type: str
    language: str


class RetrievalSettings(BaseModel):
    top_k: int


class PathSettings(BaseModel):
    chroma_dir: str


class ChromaSettings(BaseModel):
    collection: str


class Settings(BaseModel):
    models: ModelSettings
    generation: GenerationSettings
    chunking: ChunkingSettings
    whisper: WhisperSettings
    retrieval: RetrievalSettings
    paths: PathSettings
    chroma: ChromaSettings

    @property
    def chroma_path(self) -> Path:
        return _project_root() / self.paths.chroma_dir


def _project_root() -> Path:
    return Path(__file__).parent.parent.parent


def load_config() -> Settings:
    config_path = _project_root() / "config.toml"
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    s = Settings(**data)
    s.chroma_path.mkdir(parents=True, exist_ok=True)
    return s


settings = load_config()
