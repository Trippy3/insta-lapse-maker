# Insta-Lapse-Maker

絵画制作過程の写真群から **Instagram Reels 用タイムラプス動画** (1080×1920 / 30fps / H.264) を生成するツールです。次の 3 通りの使い方があります:

- 🖥️ **Web UI** — ブラウザ上でクリップ・カメラワーク・トランジションを GUI で編集
- ⌨️ **CLI** — フォルダを指定するだけでワンショット生成
- 🤖 **AI エージェント (Skills)** — [Claude Code](https://claude.com/claude-code) などのエージェントに「こんな雰囲気でタイムラプス作って」と話しかけるだけで、計画提案 → 承認 → レンダまで案内してもらう

<img width="1693" height="844" alt="timelaspe_maker" src="https://github.com/user-attachments/assets/7f27867e-c9b0-4cb6-9430-4bc43579f6f0" />


---

## クイックスタート (3 分で動かす)

事前に **Python 3.11+**, **Node.js 18+ (pnpm)**, **FFmpeg 4.0+** が必要です。

```bash
git clone https://github.com/Trippy3/insta-lapse-maker.git
cd insta-lapse-maker

# 依存をインストールしてフロントをビルド
uv sync --extra web
cd web && pnpm install && pnpm build && cd ..

# サーバー起動
uv run timelapse-web serve
```

ブラウザで <http://127.0.0.1:8765> を開けば編集 UI が表示されます。

> 編集 UI を立ち上げず、フォルダを指定するだけで動画化したい場合は [CLI 版](#cli-版) のセクションへ。

---

## できること

- 📁 **フォルダから一括追加** — 写真フォルダをブラウザ上で選び、サムネイル一覧から並びを編集
- ✂️ **トリミング** — 任意比率で切り抜き範囲を指定
- 🎥 **カメラワーク** — 開始矩形・終了矩形をドラッグするだけのズームパン
- 🔀 **トランジション** — カット / フェード / クロスフェード / ワイプ / スライドの 5 種
- 🔡 **テキストオーバーレイ** — 任意位置にフェードイン/アウト付きの文字を重ねる
- ⚡ **プロキシプレビュー** — 540×960 の軽量版でブラウザ即時確認
- 💾 **プロジェクト保存** — `*.tlproj.json` 形式で任意のパスに保存・読込

---

## Web 版を使う

### セットアップ詳細

#### 1. 必要環境

| ソフトウェア | バージョン |
|------------|-----------|
| Python | 3.11 以上 |
| Node.js / pnpm | 18 以上 / 9 以上 |
| FFmpeg | 4.0 以上 |
| uv | 推奨 |

```bash
# FFmpeg
sudo apt install ffmpeg          # Ubuntu / Debian
brew install ffmpeg              # macOS

# pnpm (未インストールの場合)
npm install -g pnpm
```

#### 2. インストール

```bash
git clone https://github.com/Trippy3/insta-lapse-maker.git
cd insta-lapse-maker
uv sync --extra web
cd web && pnpm install && pnpm build && cd ..
```

#### 3. 起動

```bash
uv run timelapse-web serve
```

| オプション | 説明 |
|-----------|------|
| `--host TEXT` | バインドホスト (default: `127.0.0.1`) |
| `--port INT` | ポート番号 (default: `8765`) |
| `--reload` | ホットリロード (開発用) |

#### 環境変数

| 変数名 | 既定値 | 説明 |
|--------|--------|------|
| `TIMELAPSE_WEB_HOST` | `127.0.0.1` | バインドホスト |
| `TIMELAPSE_WEB_PORT` | `8765` | ポート番号 |
| `TIMELAPSE_WEB_CACHE` | `~/.cache/timelapse-web` | サムネイル / プロキシ / レンダのキャッシュ |
| `TIMELAPSE_WEB_FS_ROOTS` | ホームディレクトリ | フォルダブラウザの走査許可パス (`:` 区切り) |

### 使い方

1. **画像フォルダを選択** — 左ペイン「フォルダを選択」でブラウズ → サムネイル一覧
2. **タイムラインに追加** — 画像をクリック選択して「追加」、または「全て追加」
3. **クリップを編集** — タイムラインで選択し右ペインで:
   - **秒数** — 表示時間を数値入力で調整
   - **トリミング** — 任意の切り抜き範囲を指定
   - **カメラワーク** — 開始/終了矩形をドラッグでズームパン設定
4. **トランジションを設定** — クリップ間の `┊` ボタンから種別・秒数を選択
5. **プレビュー** — 「プロキシ」で 540×960 / 15fps の確認動画を生成
6. **書き出し** — 出力先を指定し「レンダ」で 1080×1920 / 30fps の最終 MP4 を生成

### よくある質問・トラブルシュート

**Q. 起動時に `ffmpeg not found` と出る**
A. `ffmpeg -version` が通るか確認してください。Linux なら `sudo apt install ffmpeg`、macOS なら `brew install ffmpeg`。

**Q. フォルダブラウザで自分の写真フォルダが見えない**
A. 既定ではホームディレクトリ配下のみ走査します。外付けドライブなどを参照したい場合は環境変数 `TIMELAPSE_WEB_FS_ROOTS` を設定してください。

**Q. 画像数が多いとレンダが失敗する**
A. クリップ数 > 25 で自動的に二段階レンダに切り替わります。それでも失敗する場合は `~/.cache/timelapse-web/` を削除して再起動してください。

**Q. プロジェクトファイルはどこに保存される?**
A. ユーザーが指定したパスに `*.tlproj.json` として保存されます。画像は絶対パスで参照され、コピーは作りません。

---

## CLI 版

編集が不要で、フォルダを指定するだけで動画化したい場合に使います。

```bash
uv run timelapse generate ./photos -o timelapse.mp4 -d 0.5
```

詳細なオプションと使用例は [`docs/cli.md`](docs/cli.md) を参照してください。

---

## AI エージェントから使う (Skills)

[Claude Code](https://claude.com/claude-code) などのエージェントに「こんな雰囲気で動画作って」と話しかけるだけで、計画提案・承認・レンダまでを案内してもらえます。

### セットアップ

```bash
uv sync
ln -sf "$(pwd)/skills/timelapse-maker" ~/.claude/skills/timelapse-maker
```

シンボリックリンクされていれば Claude Code 起動時に自動で読み込まれます。

### 使い方

Claude Code に自然な依頼を送るだけです:

```
/home/user/painting_photos の写真でタイムラプスを作りたい。ゆっくり見せたい感じで。
```

エージェントが画像を確認し、雰囲気と枚数から表示秒数・トランジション・カメラワークを選んで制作計画を提示します。承認後は動画 (`.mp4`) と編集用プロジェクト (`.tlproj.json`) が画像と同じ場所に保存され、後者は Web UI でそのまま再編集できます。

判断ロジック・制約の詳細は [`skills/timelapse-maker/SKILL.md`](skills/timelapse-maker/SKILL.md) を参照してください。

---

## 出力動画について

すべての出力は Instagram Reels 仕様 (1080×1920 / H.264 / 30fps / AAC) に準拠します。セーフゾーン・対応画像フォーマット・アスペクト比モードの詳細は [`docs/reels-spec.md`](docs/reels-spec.md) を参照してください。

---

## 開発者向け

### 開発モード起動

フロントエンドをホットリロードしながら開発する場合、バックエンドとフロントを別プロセスで起動します。

```bash
# ターミナル 1: バックエンド (ポート 8765)
uv run timelapse-web serve --reload

# ターミナル 2: フロントエンド dev サーバー (ポート 5173)
cd web && pnpm dev
```

`http://localhost:5173` を開くと、Vite が `/api` リクエストを uvicorn へプロキシします。

### テスト・型チェック

```bash
# Python テスト (全件)
uv run pytest

# FFmpeg を必要としない単体テストのみ
uv run pytest -m "not integration"

# カバレッジ
uv run pytest --cov=timelapse --cov-report=html

# フロントエンド型チェック / ビルド
cd web && pnpm typecheck
cd web && pnpm build
```

### アーキテクチャ概要

```
src/
├── timelapse/             # CLI (バッチ生成)
│   ├── cli.py             # Typer エントリポイント
│   ├── reels_spec.py      # 出力仕様の定数 (CLI / Web / Agent 共有)
│   ├── discovery.py       # 画像列挙・ソート (filename / EXIF)
│   ├── normalize.py       # リサイズ・パディング・EXIF 回転
│   ├── encoder.py         # FFmpeg 呼び出し
│   ├── similarity.py      # 重複画像検出 (find-similar)
│   └── system.py          # FFmpeg 検出
├── timelapse_agent/       # AI エージェント連携 CLI (Skills 用)
│   ├── cli.py             # inspect / scaffold / render の 3 サブコマンド
│   ├── inspector.py       # 画像メタデータの JSON 出力
│   └── planner.py         # 雛形プロジェクト (.tlproj.json) 生成
└── timelapse_web/         # FastAPI バックエンド
    ├── api/               # REST + SSE エンドポイント
    ├── models/
    │   ├── project.py     # Pydantic データモデル (*.tlproj.json スキーマ)
    │   └── jobs.py        # レンダジョブ定義
    └── services/
        ├── filtergraph.py # filter_complex 生成 (CLI / Web / Agent 共通)
        ├── renderer.py    # FFmpeg 実行・進捗配信・二段階レンダ
        ├── job_queue.py   # 単一ワーカーキュー
        ├── project_store.py  # *.tlproj.json の永続化 (原子的書き込み)
        ├── thumbnail.py   # サムネイル / プロキシ生成
        └── native_picker.py  # OS ネイティブファイルダイアログ

web/src/                   # React 19 + Vite + Zustand フロントエンド
└── features/              # 機能別コンポーネント
                           # timeline / crop / kenburns / transitions /
                           # overlay (text) / preview / library / render /
                           # fspicker / project

skills/timelapse-maker/    # Claude Code 向け Skill 定義
└── SKILL.md               # エージェントの判断ロジックと実行手順
```

CLI / Web UI / AI エージェントの 3 通りはすべて `filtergraph.py` と `reels_spec.py` を共有しており、出力品質は完全に一致します。AI エージェント版は内部で `timelapse_agent` CLI を呼び、生成されたプロジェクトは Web UI でそのまま開けます。

バックエンド設計の詳細は [`docs/web-architecture.md`](docs/web-architecture.md)、機能別の設計と受け入れ基準は [`docs/web-plan.md`](docs/web-plan.md) を参照してください。

### ドキュメント一覧

| パス | 内容 |
|------|------|
| [`docs/cli.md`](docs/cli.md) | CLI のオプション一覧・使用例 |
| [`docs/reels-spec.md`](docs/reels-spec.md) | Reels 出力仕様・セーフゾーン・対応フォーマット |
| [`docs/web-architecture.md`](docs/web-architecture.md) | Web バックエンド設計 |
| [`docs/web-plan.md`](docs/web-plan.md) | Web UI 機能別の設計・受け入れ基準 |
| [`PLAN.md`](PLAN.md) | CLI ロードマップ |

---

## ライセンス

MIT
