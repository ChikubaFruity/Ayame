import ollama

from .config import settings
from .models import RetrievedChunk

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


def generate(question: str, chunks: list[RetrievedChunk]) -> str:
    user_prompt = build_prompt(question, chunks)

    response = ollama.chat(
        model=settings.models.generate,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        options={
            "temperature": settings.generation.temperature,
            "top_p": settings.generation.top_p,
            "top_k": settings.generation.top_k,
        },
    )

    answer = response.message.content

    sources = _format_sources(chunks)
    return f"{answer}\n\n---\n{sources}"


def _format_sources(chunks: list[RetrievedChunk]) -> str:
    seen: set[tuple[str, int, int]] = set()
    lines = ["[出典]"]
    for chunk in chunks:
        m = chunk.metadata
        key = (m.source, m.session, m.page)
        if key not in seen:
            seen.add(key)
            lines.append(f"  - {m.subject} 第{m.session}回 p.{m.page + 1} ({m.source})")
    return "\n".join(lines)
