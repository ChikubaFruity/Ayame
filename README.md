# ayame

講義資料PDFをローカルLLMで質問応答するRAGシステム。データはすべてローカルに保持し、出典をチャンク単位（科目・回・ページ）で表示する。

## 特徴

- **完全ローカル** — Ollama + ChromaDB、外部APIなし
- **細粒度の出典** — 科目・講義回・ページ番号を付与
- **シンプルなCLI** — `ingest` と `query` の2コマンドで完結
- **設定ファイル一本** — モデルやチャンクサイズを `config.toml` で管理

## 要件

- Python 3.11+
- [Ollama](https://ollama.com/) がローカルで稼働していること
- 以下のモデルを事前に pull しておくこと

```bash
ollama pull nomic-embed-text
ollama pull gemma4:12b    # デフォルト生成モデル
```

## インストール

```bash
git clone https://github.com/yourname/ayame.git
cd ayame
pip install -e .
```

## 使い方

### PDFを取り込む

```bash
ayame ingest --path 講義資料.pdf --subject 機械学習 --session 3
```

| オプション | 説明 |
|---|---|
| `--path` | PDFファイルのパス |
| `--subject` | 科目名 |
| `--session` | 講義回（整数） |

### 質問する

```bash
ayame query "過学習を防ぐ手法を教えて"
```

出力例：

```
回答:
過学習を防ぐ主な手法は以下の通りです。
- ドロップアウト
- 正則化（L1/L2）
- データ拡張

┌────────────────┬──────┬────────┬───────┐
│ ファイル       │ 科目 │ 講義回 │ ページ│
├────────────────┼──────┼────────┼───────┤
│ 講義資料.pdf   │ ML   │      3 │     7 │
│ 講義資料.pdf   │ ML   │      3 │     9 │
└────────────────┴──────┴────────┴───────┘
```

## 設定

`config.toml` で主要パラメータを変更できる。

```toml
[models]
generate = "gemma4:12b"       # 回答生成モデル（Ollamaで利用可能なものに変更可）
embed    = "nomic-embed-text" # 埋め込みモデル

[chunking]
size    = 800  # チャンクサイズ（文字数）
overlap = 150  # 隣接チャンクとの重複文字数

[retrieval]
top_k = 5  # 検索で取得するチャンク数
```

## 技術スタック

| 役割 | ライブラリ |
|---|---|
| LLM推論 | [Ollama](https://ollama.com/) |
| ベクトルDB | ChromaDB |
| PDF抽出 | PyMuPDF |
| CLI | Typer |
| 表示 | Rich |

## ロードマップ

- [ ] Discord Bot フロントエンド
- [ ] 音声ファイル取り込み（faster-whisper）
