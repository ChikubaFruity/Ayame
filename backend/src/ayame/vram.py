import ollama
from loguru import logger

from .config import settings


def unload_ollama() -> None:
    for model in {settings.models.generate, settings.models.embed}:
        try:
            # keep_alive=0 で即VRAMアンロード
            ollama.generate(model=model, keep_alive=0)
            logger.info(f"Unloaded Ollama model from VRAM: {model}")
        except Exception as e:
            logger.warning(f"Failed to unload {model}: {e}")
