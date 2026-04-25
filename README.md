# timelapse

絵画制作過程の写真から **Instagram Reels 用タイムラプス動画** を生成するツールです。

**CLI** と **ブラウザ編集 UI (timelapse-web)** の 2 つのインターフェースを提供します。CLI はコマンド 1 本でシンプルに動画を生成でき、Web UI ではトリミング・Ken Burns・トランジションを視覚的に編集しながらレンダできます。どちらも同一の FFmpeg グラフ生成エンジンを使うため、出力品質は完全に一致します。

---

## 機能一覧

### CLI

- 写真ディレクトリを指定するだけで Reels 仕様 (1080×1920 / H.264 / 30fps) の MP4 を生成
- ファイル名順・EXIF 撮影日時順の両ソートに対応
- 横長・縦長・正方形など異なるサイズの写真が混在していても自動調整 (黒帯 or 中央クロップ)
- JPEG / PNG / HEIC / WebP など主要フォーマットに対応
- rich によるカラー進捗表示

### Web UI (timelapse-web)

- **画像ライブラリ** — フォルダをブラウザ上で選択し、サムネイル一覧から追加
- **トリミング** — 1:1 または 9:16 で任意範囲をクロップ
- **Ken Burns** — 開始矩形・終了矩形をドラッグで指定してズームパンアニメーションを付与
- **トランジション** — 隣接クリップ間に 5 種 (カット / フェード / クロスフェード / 左ワイプ / 右ワイプ / 上スライド) を設定
- **プロキシプレビュー** — 540×960 / 15fps の軽量版をブラウザで確認
- **プロジェクト保存/読込** — `*.tlproj.json` 形式で任意のパスに保存
- **自動二段階レンダ** — クリップ数が多い場合 (> 25) は filter_complex の肥大を回避して自動切替

---

## 必要環境

| ソフトウェア | バージョン |
|------------|-----------|
| Python | 3.11 以上 |
| FFmpeg | 4.0 以上 |
| uv (推奨) | — |

### FFmpeg のインストール

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

---

## セットアップ

```bash
# リポジトリをクローン
git clone <repo_url>
cd timelapse

# 依存関係をインストール
uv sync

# CLI が使えるか確認
uv run timelapse --version
```

### 開発用セットアップ

```bash
uv sync --dev
uv run pytest
```

---

## 使い方

### 基本

```bash
uv run timelapse generate ./photos
```

`./photos` ディレクトリ内の画像をファイル名順に並べ、`output.mp4` を生成します。

### オプション一覧

```
timelapse generate [OPTIONS] INPUT_DIR

引数:
  INPUT_DIR             写真が格納されたディレクトリ (必須)

オプション:
  -o, --output PATH     出力 MP4 ファイルパス          [default: output.mp4]
  -d, --duration FLOAT  1枚あたりの表示秒数            [default: 0.3]
  --fps FLOAT           フレームレート                 [default: 30.0]
  -s, --sort            ソート順 (filename / exif)     [default: filename]
  -f, --fit             アスペクト比調整 (pad / crop)  [default: pad]
  --dry-run             エンコードせず設定だけ確認
  -v, --verbose         詳細ログを表示
```

### 使用例

```bash
# 出力先・表示時間を指定
uv run timelapse generate ./photos -o timelapse.mp4 -d 0.5

# EXIF 撮影日時順でソート
uv run timelapse generate ./photos --sort exif

# 横長写真を中央クロップで縦型に変換
uv run timelapse generate ./photos --fit crop

# 設定確認だけ行う (エンコードしない)
uv run timelapse generate ./photos --dry-run

# 動画を速くする (1枚 0.1 秒 = 10fps 相当)
uv run timelapse generate ./photos -d 0.1 -o fast.mp4
```

---

## 対応画像フォーマット

| 拡張子 | 形式 |
|--------|------|
| `.jpg` / `.jpeg` | JPEG |
| `.png` | PNG |
| `.heic` / `.heif` | HEIC (iPhone 標準) |
| `.webp` | WebP |
| `.bmp` | BMP |
| `.tiff` / `.tif` | TIFF |

---

## Instagram Reels 出力仕様

| 項目 | 値 |
|------|---|
| コンテナ | MP4 |
| 映像コーデック | H.264 (High Profile, Level 4.0) |
| 解像度 | 1080 × 1920 (9:16) |
| フレームレート | 30fps |
| 映像ビットレート | 5 Mbps (最大 8 Mbps) |
| 音声コーデック | AAC-LC |
| 音声ビットレート | 128 kbps |
| サンプルレート | 48 kHz / ステレオ |
| 色空間 | BT.709 / yuv420p |
| faststart | 有効 (ストリーミング再生対応) |

### セーフゾーン

Reels の画面には UI 要素が上下に重なります。主要な被写体は中央領域 **1080 × 1220px** に収めることを推奨します。

```
┌───────────────┐ ← 上端
│  [上部 UI]    │ 約 250px: プロフィール・メニュー
├───────────────┤
│               │
│  安全領域     │ 約 1220px: 絵画が見える領域
│  1080×1220    │
│               │
├───────────────┤
│  [下部 UI]    │ 約 450–650px: キャプション・いいね・コメント
└───────────────┘ ← 下端 (1920px)
```

---

## アスペクト比の調整モード

### `--fit pad` (デフォルト)

元のアスペクト比を保ったまま、余白を黒帯で埋めます。絵画全体が見えることを優先する場合に適しています。

```
┌─────────────────┐
│ [黒帯]          │
├─────────────────┤
│                 │
│   元の画像      │
│                 │
├─────────────────┤
│ [黒帯]          │
└─────────────────┘
```

### `--fit crop`

中央を基準にクロップし、黒帯なしで画面を埋めます。フル画面で見せたい場合に適しています。

---

## ソート順

| オプション | 動作 |
|-----------|------|
| `filename` (デフォルト) | ファイル名の自然順 (`img9.jpg` → `img10.jpg`) |
| `exif` | EXIF の撮影日時順。日時情報がない画像はファイル名順で末尾に追加 |

---

## ロードマップ (CLI)

- **Phase 2**: BGM 追加 (フェードイン/アウト)・テキストオーバーレイ
- **Phase 3**: クロスフェードトランジション・手ブレ補正・明るさ正規化
- **Phase 4**: Instagram Graph API 経由での直接アップロード

詳細は [PLAN.md](PLAN.md) を参照してください。

---

## Web 編集 UI (timelapse-web)

CLI と同一のレンダラーをブラウザ上から操作できる編集 Web アプリです。`src/timelapse_web/` (FastAPI バックエンド) と `web/` (React フロントエンド) で構成されています。

### 必要環境 (Web UI 追加分)

| ソフトウェア | バージョン |
|------------|-----------|
| Node.js | 18 以上 |
| pnpm | 9 以上 |

```bash
# pnpm のインストール (未インストールの場合)
npm install -g pnpm
```

### セットアップ

```bash
# 1. Python 側: Web 用依存を追加インストール
uv sync --extra web

# 2. フロントエンドをビルド (web/dist/ に出力)
cd web && pnpm install && pnpm build && cd ..
```

### 起動

```bash
uv run timelapse-web serve
```

起動後、ブラウザで **http://127.0.0.1:8765** を開きます。

```
オプション:
  --host TEXT   バインドホスト  [default: 127.0.0.1]
  --port INT    ポート番号      [default: 8765]
  --reload      開発用ホットリロード
```

### 基本的な使い方

1. **画像フォルダを選択** — 左ペイン「フォルダを選択」でフォルダをブラウズし、サムネイル一覧を表示
2. **タイムラインに追加** — 追加したい画像をクリックして選択し「追加」、または「全て追加」
3. **クリップを編集** — タイムライン上のクリップを選択して右ペインで編集
   - **秒数変更**: 各クリップの表示時間をスライダーまたは数値入力で調整
   - **トリミング**: 「トリミング」タブで 1:1 または 9:16 の切り抜き範囲を指定
   - **Ken Burns**: 「Ken Burns」タブでズームパンの開始・終了矩形をドラッグで設定
4. **トランジションを設定** — タイムライン上のクリップ間にある `┊` ボタンをクリックして種別・秒数を選択
5. **プレビュー** — 「プロキシ」ボタンで 540×960 / 15fps の確認用動画を生成・再生
6. **レンダ** — 出力先を選択して「レンダ」ボタンで最終 MP4 (1080×1920 / 30fps) を生成

### 環境変数

| 変数名 | 既定値 | 説明 |
|--------|--------|------|
| `TIMELAPSE_WEB_HOST` | `127.0.0.1` | バインドホスト |
| `TIMELAPSE_WEB_PORT` | `8765` | ポート番号 |
| `TIMELAPSE_WEB_CACHE` | `~/.cache/timelapse-web` | サムネイル・プロキシ・レンダキャッシュ |
| `TIMELAPSE_WEB_FS_ROOTS` | ホームディレクトリ | FS ブラウザ API が走査を許可するパス (`:` 区切りで複数指定可) |

### プロジェクトファイル

プロジェクトは `*.tlproj.json` 形式でユーザー指定の任意のパスに保存・読込します。画像ファイルは絶対パスで参照します (コピーはしません)。

```
~/.cache/timelapse-web/
├── thumbs/    # サムネイル (JPEG 変換済み)
├── proxy/     # プロキシ動画 (540×960)
└── renders/   # 出力先を指定しなかった場合の最終レンダ
```

### 開発用セットアップ (Vite + uvicorn)

フロントエンドをホットリロードしながら開発する場合は、バックエンドとフロントを別プロセスで起動します。

```bash
# ターミナル 1: バックエンド (ポート 8765)
uv run timelapse-web serve --reload

# ターミナル 2: フロントエンド dev サーバー (ポート 5173)
cd web && pnpm dev
```

`http://localhost:5173` を開くと、Vite が `/api` リクエストを uvicorn へプロキシします。

### ロードマップ (Web UI)

| Phase | 機能 | 状態 |
|-------|------|------|
| 1 | 基本動画生成 | ✅ 完了 |
| 2 | トリミング + FS ピッカー | ✅ 完了 |
| 3 | Ken Burns (ズームパン) | ✅ 完了 |
| 4 | 5 種トランジション + 二段階レンダ | ✅ 完了 |
| 5 | テキストオーバーレイ | 🔲 未着手 |
| 6 | ライブプレビュー | ⏸ 保留 |

詳細な設計・受け入れ基準は [docs/web-plan.md](docs/web-plan.md) を参照してください。

---

## 開発

```bash
# テスト実行 (全件)
uv run pytest

# テスト (FFmpeg が不要な単体テストのみ)
uv run pytest -m "not integration"

# カバレッジ確認
uv run pytest --cov=timelapse --cov-report=html

# フロントエンド型チェック
cd web && pnpm typecheck
```

### プロジェクト構造

```
timelapse/
├── src/
│   ├── timelapse/             # CLI ツール本体
│   │   ├── cli.py             # Typer エントリポイント
│   │   ├── reels_spec.py      # Reels 仕様定数 (解像度・コーデック等)
│   │   ├── discovery.py       # 画像列挙・ソート
│   │   ├── normalize.py       # リサイズ・パディング・EXIF 回転
│   │   ├── encoder.py         # FFmpeg 呼び出し
│   │   └── system.py          # FFmpeg 検出・バージョン確認
│   └── timelapse_web/         # Web アプリ (FastAPI)
│       ├── api/               # REST エンドポイント
│       ├── models/project.py  # プロジェクトデータモデル (Pydantic)
│       ├── services/
│       │   ├── filtergraph.py # FFmpeg filter_complex 生成
│       │   └── renderer.py    # FFmpeg 実行・進捗配信
│       └── config.py          # 環境変数設定
├── web/                       # React フロントエンド
│   └── src/features/          # 機能別コンポーネント
│       ├── kenburns/          # Ken Burns エディタ (react-konva)
│       ├── transitions/       # トランジションピッカー
│       ├── crop/              # トリミングエディタ
│       └── fspicker/          # FS ブラウザモーダル
├── tests/                     # pytest テスト
└── docs/web-plan.md           # Web UI 設計書
```

---

## ライセンス

MIT
