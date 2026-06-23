from pathlib import Path

import typer
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

from . import ingest as ingest_module
from . import retriever
from . import generator

_EMBED_BATCH = 4

app = typer.Typer(help="ローカルNotebookLM")
console = Console()


@app.command()
def ingest(
    path: Path = typer.Option(..., "--path", help="取り込むPDFファイルのパス", exists=True, file_okay=True),
    subject: str = typer.Option(..., "--subject", help="科目名"),
    session: int = typer.Option(..., "--session", help="第N回"),
) -> None:
    """PDFを取り込んでChromaDBに保存する"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        # ステップ1: テキスト抽出 + チャンク分割
        extract_task = progress.add_task("[cyan]テキスト抽出中...", total=None)
        chunks = ingest_module.prepare_chunks(path, subject, session)
        progress.update(extract_task, description="[green]テキスト抽出完了", total=1, completed=1)

        if not chunks:
            console.print("[red]テキストを抽出できませんでした。スキャンPDFの可能性があります。")
            raise typer.Exit(1)

        # ステップ2: 重複削除
        retriever.delete_source(path.name)

        # ステップ3: 埋め込み（バッチ処理、進捗表示）
        embed_task = progress.add_task(
            "[cyan]埋め込み処理中...", total=len(chunks)
        )
        all_embeddings: list[list[float]] = []
        for i in range(0, len(chunks), _EMBED_BATCH):
            batch = chunks[i : i + _EMBED_BATCH]
            all_embeddings.extend(retriever.embed_texts([c.text for c in batch]))
            progress.advance(embed_task, len(batch))
        progress.update(embed_task, description="[green]埋め込み完了")

        # ステップ4: ChromaDB 保存
        save_task = progress.add_task("[cyan]ChromaDBに保存中...", total=None)
        retriever.store_chunks(chunks, all_embeddings)
        progress.update(save_task, description="[green]保存完了", total=1, completed=1)

    console.print(f"[green]✓[/green] {path.name} を取り込みました（{len(chunks)} チャンク）")


@app.command()
def query(
    question: str = typer.Argument(..., help="質問文"),
) -> None:
    """質問して出典付きで回答を得る"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]関連資料を検索中...", total=None)
        chunks = retriever.search(question)
        progress.update(task, description="[cyan]回答を生成中...")

        if not chunks:
            progress.stop()
            console.print("[yellow]関連する資料が見つかりませんでした。")
            raise typer.Exit(0)

        answer_with_sources = generator.generate(question, chunks)
        progress.update(task, description="[green]完了")

    parts = answer_with_sources.split("\n\n---\n", 1)
    answer_text = parts[0]
    sources_text = parts[1] if len(parts) > 1 else ""

    console.print()
    console.rule("[bold]回答")
    console.print(answer_text)

    if sources_text:
        console.print()
        _print_sources_table(chunks)


def _print_sources_table(chunks) -> None:
    seen: set[tuple[str, int, int]] = set()
    table = Table(title="出典", show_header=True, header_style="bold magenta")
    table.add_column("科目", style="cyan")
    table.add_column("回", justify="right")
    table.add_column("ページ", justify="right")
    table.add_column("ファイル名")

    for chunk in chunks:
        m = chunk.metadata
        key = (m.source, m.session, m.page)
        if key not in seen:
            seen.add(key)
            table.add_row(m.subject, f"第{m.session}回", str(m.page + 1), m.source)

    console.print(table)
