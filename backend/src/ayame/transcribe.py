import gc
from pathlib import Path

from loguru import logger

from .config import settings
from . import vram

MEDIA_EXTS = {
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",
    ".mp4", ".mov", ".mkv", ".webm", ".avi",
}

_model = None


def _get_model():
    global _model
    if _model is None:
        # 未インストール環境でもPDF取り込みを動かすため関数内import
        from faster_whisper import WhisperModel

        logger.info(
            f"Loading whisper '{settings.whisper.model}' "
            f"({settings.whisper.device}/{settings.whisper.compute_type})"
        )
        _model = WhisperModel(
            settings.whisper.model,
            device=settings.whisper.device,
            compute_type=settings.whisper.compute_type,
        )
    return _model


def unload() -> None:
    global _model
    if _model is not None:
        _model = None
        gc.collect()  # ctranslate2はオブジェクト破棄でVRAMを解放
        logger.info("Unloaded whisper model from VRAM")


def transcribe(media_path: Path) -> list[tuple[float, str]]:
    # gemmaとwhisperをGPUに同時常駐させない（前にollama・後にwhisperをアンロード）
    vram.unload_ollama()
    try:
        model = _get_model()
        segments, info = model.transcribe(
            str(media_path),
            language=settings.whisper.language,
            vad_filter=True,
        )
        result = [(seg.start, seg.text) for seg in segments]
        logger.info(f"Transcribed {media_path.name}: {len(result)} segments")
        return result
    finally:
        unload()
