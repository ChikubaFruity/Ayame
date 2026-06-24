# ayame

講義資料PDF・音声・動画をローカルLLMで質問応答するRAGシステム。データはすべてローカルに保持し、出典をチャンク単位（科目・回・ページ/タイムスタンプ）で表示する。

## 特徴

- **完全ローカル** — Ollama + ChromaDB、外部APIなし
- **多様な入力** — PDFに加え音声・動画を faster-whisper で文字起こしして取り込み
- **細粒度の出典** — 科目・講義回・ページ番号（メディアは mm:ss）を付与
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

- 音声・動画を取り込む場合:
  - システムに `ffmpeg` を導入（動画コーデックのデコード用）
  - GPU(CUDA)で文字起こしする場合は CUDA12 / cuDNN9 / cuBLAS が必要
    （不足時は `config.toml` の `[whisper] device = "cpu"` に変更）
  - 初回取り込み時に whisper モデル（既定 `large-v3`）が自動ダウンロードされる

## インストール

```bash
git clone https://github.com/yourname/ayame.git
cd ayame/backend
uv sync
```

> ディレクトリ構成: Pythonコア+APIは `backend/`、Web UIは `frontend/`。
> CLI / API 系のコマンドはすべて `backend/` で実行する。

## 使い方

### 資料を取り込む（PDF / 音声 / 動画）

```bash
# backend/ で実行
uv run ayame ingest --path 講義資料.pdf --subject 機械学習 --session 3
uv run ayame ingest --path 講義録画.mp4 --subject 機械学習 --session 3  # 文字起こしして取り込み
```

| オプション | 説明 |
|---|---|
| `--path` | PDF / 音声(mp3,wav,m4a,flac,ogg,aac) / 動画(mp4,mov,mkv,webm,avi) のパス |
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

CLIに加えて、ブラウザからPDF・音声・動画の取り込みと質問ができるWeb UIを同梱。

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

ブラウザで http://localhost:3000 を開く。左パネルで資料（PDF・音声・動画）を取り込み、右側で質問するとトークン単位でストリーミング回答され、出典（科目・回・ページ/タイムスタンプ）が表示される。

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

[whisper]
model        = "large-v3"  # faster-whisperのモデル
device       = "cuda"      # cuda | cpu
compute_type = "float16"   # float16 | int8 | int8_float16
language     = "ja"

[retrieval]
top_k = 5  # 検索で取得するチャンク数
```

> 文字起こしと生成モデルは VRAM 競合を避けるため同時にGPUへ常駐させない。
> 取り込み時に Ollama のモデルを一時アンロード→文字起こし→whisperをアンロード→埋め込み、の順で処理する。

## 技術スタック

| 役割 | ライブラリ |
|---|---|
| LLM推論 | [Ollama](https://ollama.com/) |
| ベクトルDB | ChromaDB |
| PDF抽出 | PyMuPDF |
| 文字起こし | faster-whisper |
| CLI | Typer |
| 表示 | Rich |
| Web API | FastAPI + sse-starlette |
| Web UI | Next.js (TypeScript) |

## ロードマップ

- [x] Webアプリ（FastAPI + Next.js、PDFチャット）
- [x] 動画/音声取り込み（faster-whisper、タイムスタンプ出典）
- [ ] PDFインラインビューア + 本文ハイライト
- [ ] マルチモーダル取り込み（CSV）
- [ ] 認証・Cloudflare Tunnelでの公開
