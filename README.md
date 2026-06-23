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
cd ayame/backend
uv sync
```

> ディレクトリ構成: Pythonコア+APIは `backend/`、Web UIは `frontend/`。
> CLI / API 系のコマンドはすべて `backend/` で実行する。

## 使い方

### PDFを取り込む

```bash
# backend/ で実行
uv run ayame ingest --path 講義資料.pdf --subject 機械学習 --session 3
```

| オプション | 説明 |
|---|---|
| `--path` | PDFファイルのパス |
| `--subject` | 科目名 |
| `--session` | 講義回（整数） |

### 質問する

```bash
uv run ayame query "過学習を防ぐ手法を教えて"
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

## Webアプリ（NotebookLM風UI）

CLIに加えて、ブラウザからPDF取り込み・質問ができるWeb UIを同梱。

構成:

- バックエンド: FastAPI（既存のPython RAGコアをAPI化）
- フロントエンド: Next.js (TypeScript)

### 起動

バックエンド（ポート8000）:

```bash
cd backend
uv run ayame-server
```

フロントエンド（別ターミナル、ポート3000）:

```bash
cd frontend
npm install   # 初回のみ
npm run dev
```

ブラウザで http://localhost:3000 を開く。左パネルでPDFを取り込み、右側で質問するとトークン単位でストリーミング回答され、出典（科目・回・ページ）が表示される。

### リモートアクセス（Tailscale）

iPad/スマホや友人と共有する場合は [Tailscale](https://tailscale.com/) を利用する。

- サーバ機とクライアント機にTailscaleを導入
- バックエンドは既定で `0.0.0.0:8000` にbind（`HOST` / `PORT` 環境変数で変更可）
- フロントの参照先APIを環境変数で指定する（`frontend/.env.local`）:

```bash
# frontend/.env.local — <tailscale-host> はMagicDNS名 or Tailscale IP
NEXT_PUBLIC_API_BASE=http://<tailscale-host>:8000
```

- バックエンド側でフロントのオリジンをCORS許可（`*.ts.net` は既定で許可済み。それ以外は環境変数で追加）:

```bash
ALLOW_ORIGINS=http://<tailscale-host>:3000 uv run ayame-server
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
| Web API | FastAPI + sse-starlette |
| Web UI | Next.js (TypeScript) |

## ロードマップ

- [x] Webアプリ（FastAPI + Next.js、PDFチャット）
- [ ] PDFインラインビューア + 本文ハイライト
- [ ] マルチモーダル取り込み（動画/音声=faster-whisper, CSV）
- [ ] 認証・Cloudflare Tunnelでの公開
