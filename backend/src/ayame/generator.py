from collections.abc import Iterator

import ollama

from .config import settings
from .models import RetrievedChunk, Source

_SYSTEM_PROMPT = (
    "あなたは大学の講義資料に基づいて質問に答えるアシスタントです。"
    "提供されたコンテキストのみを使用して回答してください。"
    "コンテキストに答えがない場合は「資料に記載がありません」と答えてください。"
)


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_parts = []
    for chunk in chunks:
        m = chunk.metadata
        label = f"[出典: {m.subject} 第{m.session}回 p.{m.page + 1}]"
        context_parts.append(f"{label}\n{chunk.text}")

    context = "\n\n".join(context_parts)
    return f"コンテキスト:\n{context}\n\n質問: {question}"


def _messages(question: str, chunks: list[RetrievedChunk]) -> list[dict]:
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": build_prompt(question, chunks)},
    ]


def _options() -> dict:
    return {
        "temperature": settings.generation.temperature,
        "top_p": settings.generation.top_p,
        "top_k": settings.generation.top_k,
    }


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    response = ollama.chat(
        model=settings.models.generate,
        messages=_messages(question, chunks),
        options=_options(),
    )
    return response.message.content


def generate_stream(question: str, chunks: list[RetrievedChunk]) -> Iterator[str]:
    stream = ollama.chat(
        model=settings.models.generate,
        messages=_messages(question, chunks),
        options=_options(),
        stream=True,
    )
    for part in stream:
        content = part.message.content
        if content:
            yield content


def generate(question: str, chunks: list[RetrievedChunk]) -> str:
    answer = generate_answer(question, chunks)
    return f"{answer}\n\n---\n{_format_sources(chunks)}"


def collect_sources(chunks: list[RetrievedChunk]) -> list[Source]:
    seen: set[tuple[str, int, int]] = set()
    sources: list[Source] = []
    for chunk in chunks:
        m = chunk.metadata
        key = (m.source, m.session, m.page)
        if key not in seen:
            seen.add(key)
            sources.append(Source(m.subject, m.session, m.page, m.source))
    return sources


def _format_sources(chunks: list[RetrievedChunk]) -> str:
    lines = ["[出典]"]
    for s in collect_sources(chunks):
        lines.append(f"  - {s.subject} 第{s.session}回 p.{s.page + 1} ({s.source})")
    return "\n".join(lines)
