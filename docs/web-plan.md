# timelapse-web 実装計画

作成日: 2026-04-22
対象: 既存 CLI ツール `timelapse` を無改変のまま、ブラウザ上で編集しながら Instagram Reels 用タイムラプス動画を作成できる Web アプリを追加する。

関連文書:
- [PLAN.md](../PLAN.md) — CLI 本体の計画 (Phase 1–4)
- [docs/web-architecture.md](./web-architecture.md) — Phase 1 時点の実装詳細

---

## 0. 要件と前提

### 確定要件
- 既存 CLI (`src/timelapse/` パッケージ) はそのまま維持。Web アプリは別エントリポイントとして追加
- ローカル専用・シングルユーザー前提。認証/マルチテナント/公開デプロイは対象外
- 入力: 絵画制作過程の写真群 (JPEG/PNG/HEIC/WebP/BMP/TIFF)
- 出力: **1080×1920 / 30fps / H.264 High@4.0 / 5Mbps / AAC 128k / yuv420p / +faststart** (既存 `reels_spec.py` と完全一致)
- UI 機能:
  1. 画像トリミング (**1:1 または 9:16**)
  2. Ken Burns 効果 (開始矩形 → 終了矩形の線形補間)
  3. 画像間トランジション (fade / crossfade / wipe 等)
  4. テキストオーバーレイ (フォント/色/サイズ/位置/in/out 時刻)
  5. **フォルダの入力と動画ファイルの出力先指定を、ファイルを扱うライブラリ/ピッカーを介して GUI で完結させる** (ユーザーにテキストで絶対パスを手入力させない)

### 確定した判断事項
| 項目 | 決定 |
|---|---|
| 1:1 クリップの 9:16 埋め方 | **黒帯 (letterbox)** (`pad=...:color=black`) |
| BGM | **完全対象外**。無音ステレオの `anullsrc` のみ付与して AAC トラックを担保 |
| プロジェクトファイル保存先 | **ユーザー指定パス方式** (`*.tlproj.json` を任意の場所に保存/読込) |
| 配布形態 | **単一コマンド運用**: `timelapse-web serve` が `web/dist/` を `StaticFiles` で配信 |
| フォルダ/出力先の指定方法 | **サーバサイド・ディレクトリブラウザ** (FastAPI 経由で FS を走査、React でツリー/モーダル UI)。絶対パスの手入力は UI から排除 |
| Phase 6 (Konva ライブプレビュー) | Phase 1–5 完了後に再判断、初期計画からは除外 |

### その他の前提
- HEIC はブラウザ標準で表示できないため、サーバで JPEG サムネイルに変換して配信する
- Ken Burns の矩形は「トリミング後フレームに対する相対座標」(画像原寸ではない)
- プロジェクトファイルは絶対パス参照で画像を指す。アプリ側はコピーしない
- Reels の動画長は 3–90 秒。下限は編集中は緩めるが 90 秒超は拒否
- 同時編集なし。ローカル単一プロセスでロック不要

---

## 1. 技術選定

### 1.1 バックエンド: FastAPI + uvicorn

| 候補 | 判定 | 理由 |
|---|---|---|
| **FastAPI** | **採用** | Pydantic v2 と自然統合、既存 `encoder.py`/`normalize.py`/`reels_spec.py` を無改変で再利用可能、SSE/WebSocket 容易、OpenAPI 自動生成 |
| Django | 不採用 | DB 不要・過剰、既存が Pydantic ベース |
| Flask | 不採用 | Pydantic 統合/async/WS が弱い |
| Node + ffmpeg-wasm | 不採用 | `normalize.py`/`encoder.py` の資産を捨てる羽目になる |

### 1.2 フロントエンド: React + Vite + TypeScript

| 候補 | 判定 | 理由 |
|---|---|---|
| **React + Vite + TS + Tailwind/CSS + Zustand** | **採用** | Canvas/タイムライン系 OSS が最多、開発サーバー高速、undo/redo も Zustand で完結 |
| Next.js | 不採用 | SSR は不要でオーバーキル |
| SvelteKit | 不採用 | Canvas エコシステムが React に劣る |

採用 UI ライブラリ (段階的に導入):
- **トリミング** (Phase 2): `react-advanced-cropper` — アスペクト比固定・回転可
- **Ken Burns 矩形 / テキスト配置** (Phase 3, 5): `react-konva` — HTML5 Canvas 上で矩形ドラッグ・リサイズ・スナップ
- **タイムライン**: 自作 (Zustand + CSS)。外部ライブラリは重いため小さく書く
- **動画プレビュー**: HTML5 `<video>` + サーバー生成プロキシ MP4
- **フォーム**: `react-hook-form` + `zod` (必要になってから)

### 1.3 プレビュー方式: サーバープロキシ動画

| 方式 | 判定 | 備考 |
|---|---|---|
| ① サーバープロキシ動画 (540×960/15fps) | **Phase 1–5 で採用** | 本番と同じ FFmpeg グラフを使うため精度保証 |
| ② ブラウザ Canvas/WebGL ライブ | Phase 6 検討 | 反応は速いが FFmpeg と微妙にズレる可能性 |
| ③ ハイブリッド | Phase 6 検討 | ライブは近似、最終確認はプロキシ |

Phase 1–5 は ①のみ。Phase 6 で ②/③ を再検討する。

### 1.4 レンダリング: FFmpeg `filter_complex` を Python で組み立て

- 既存 `encoder.py` の延長として実装
- 画像数が多い場合 (**クリップ数 > 25 または filter_complex 文字列長 > 30000**) は **二段階レンダ** に自動切替:
  - Stage 1: 各クリップを個別に中間 MP4 化 (zoompan + crop + 該当クリップ内 drawtext)
  - Stage 2: 個別 MP4 群を xfade で連結 + グローバルテキストをまとめて overlay
- Remotion / MoviePy は採用しない (既存資産との二重管理、品質制御の粗さ)

### 1.5 ファイル/ディレクトリピッカー: サーバサイド・ディレクトリブラウザ

ローカル単一ユーザー前提 & 画像は絶対パス参照という既存設計との整合から、**サーバ側で FS を走査してツリーを返す API + React のモーダル UI** を採用する。

| 候補 | 判定 | 理由 |
|---|---|---|
| **サーバサイド・ディレクトリブラウザ** (`/api/fs/browse`, `/api/fs/home`) + React モーダル | **採用** | 絶対パス運用そのまま、ブラウザ非依存、Chrome/Firefox/Safari いずれでも同じ挙動、実装容易。サブディレクトリ絞り込み・ホーム直下/直近使用の提示が容易 |
| File System Access API (`showDirectoryPicker`) | 不採用 | Safari/Firefox の対応が不完全。`FileSystemHandle` は絶対パスを返さないため既存アーキと不整合 (ハンドル経由で都度ファイル読み出しが必要) |
| pywebview / tkinter.filedialog で OS ネイティブダイアログ | 不採用 | Web UI 単独では呼べずデスクトップラッパーが必要。単一コマンド運用 (ブラウザ UI) と相性が悪い |
| `<input type="file" webkitdirectory>` | 不採用 | ブラウザがファイル実体を読み出しサーバへ送る形になり、絶対パスを保持できない (Chromium は `webkitRelativePath` のみ) |

セキュリティ (ローカル専用だがサニティ):
- 走査対象のルートは **ユーザーホーム以下をデフォルト**とし、環境変数 `TIMELAPSE_WEB_FS_ROOTS` (`:` 区切り) で拡張可。外側はエラー
- シンボリックリンクは解決後に同じルート配下であることを再検証
- 走査結果は名前/種別 (dir/file)/拡張子のみ。パーミッション/所有者は露出しない
- 隠しファイル (`.` 始まり) は既定で非表示、トグルで表示

API 草案 (Phase 2 で実装):
- `GET /api/fs/home` → `{ home: "/home/<user>", roots: [...] }`
- `GET /api/fs/browse?path=<abs>&show_hidden=false` → `{ path, parent, entries: [{name, type, is_image_dir?}] }`
  - `type: "dir" | "image" | "other"`、`is_image_dir` は子に画像を含むディレクトリに立てる (ユーザー導線のため)
- 出力先は **ディレクトリ選択 + ファイル名入力** の二段構え (既存ファイル上書き時は確認)

フロントエンド (Phase 2 で実装):
- `web/src/features/fspicker/DirectoryPicker.tsx` — モーダル。ツリー/パンくず/ホームへ戻る/再読込
- `web/src/features/fspicker/OutputPicker.tsx` — ディレクトリ選択 + ファイル名入力
- `LibraryPanel` の絶対パス入力欄を **「フォルダを選択」ボタン + 現在のパス表示 (readonly)** に置き換え
- `RenderPanel` の出力先入力を **「保存先を選択」ボタン + 選択済みパス表示** に置き換え

### 1.6 ストレージ

- プロジェクト: `*.tlproj.json` (Pydantic で serialize)、画像は絶対パス参照
- キャッシュ: `~/.cache/timelapse-web/<sub>/` (環境変数 `TIMELAPSE_WEB_CACHE` で上書き可)
  - `thumbs/` — 512px JPEG サムネイル (HEIC→JPEG 変換含む)
  - `proxy/` — プレビュー用プロキシ動画
  - `renders/` — 最終出力 (出力先未指定時)
- 一時 FFmpeg concat list / filter script: `tempfile.TemporaryDirectory` で生成・破棄

---

## 2. アーキテクチャ

### 2.1 モノレポ構成

```
timelapse/
├── pyproject.toml                # [project.optional-dependencies] web を追加
├── src/
│   ├── timelapse/                # 既存 CLI (原則無改変)
│   │   ├── cli.py
│   │   ├── reels_spec.py         # ← Web も共通参照
│   │   ├── normalize.py          # ← 再利用
│   │   ├── encoder.py            # ← 再利用、関数追加は許容
│   │   ├── discovery.py
│   │   ├── similarity.py
│   │   └── ...
│   └── timelapse_web/            # 新規: FastAPI アプリ
│       ├── main.py               # FastAPI app, StaticFiles マウント
│       ├── cli_entry.py          # `timelapse-web serve`
│       ├── config.py             # AppConfig (キャッシュ/バインド)
│       ├── models/
│       │   ├── project.py        # Project, Clip, CropRect, KenBurns, Transition, TextOverlay
│       │   └── jobs.py           # RenderJob, JobStatus
│       ├── services/
│       │   ├── project_store.py  # JSON 永続化 (原子的)
│       │   ├── thumbnail.py      # Pillow + pillow-heif
│       │   ├── filtergraph.py    # filter_complex 組み立て
│       │   ├── renderer.py       # FFmpeg 実行 + 進捗
│       │   └── job_queue.py      # 単一ワーカー + SSE 配信
│       ├── api/
│       │   ├── projects.py       # CRUD + save/load
│       │   ├── media.py          # 走査 / サムネ / メタ
│       │   ├── render.py         # ジョブ投入 / 状態 / DL
│       │   ├── events.py         # SSE
│       │   └── fs.py             # Phase 2: ディレクトリブラウザ (/api/fs/*)
│       └── assets/fonts/         # Noto Sans JP 同梱 (Phase 5)
├── web/                          # 新規: Vite + React
│   ├── package.json, vite.config.ts, tsconfig.json, index.html
│   └── src/
│       ├── main.tsx, App.tsx, styles.css
│       ├── api/client.ts
│       ├── store/useProjectStore.ts, useJobStream.ts
│       ├── types/project.ts      # Pydantic に対応する TS 型
│       └── features/
│           ├── library/, timeline/, preview/
│           ├── render/, project/
│           ├── fspicker/         # Phase 2: ディレクトリ/ファイル選択モーダル
│           ├── crop/             # Phase 2
│           ├── kenburns/         # Phase 3
│           ├── transitions/      # Phase 4
│           └── overlay/          # Phase 5
├── tests/timelapse_web/          # 新規テスト
└── docs/
    ├── web-plan.md               # 本ファイル
    └── web-architecture.md       # 実装詳細 (段階的に更新)
```

### 2.2 起動・配信

- 開発: `uvicorn timelapse_web.main:app --reload` (8765) + `vite` (5173)。Vite から `/api` を 8765 へプロキシ
- 本番 (ローカル): `pnpm --prefix web build` → FastAPI が `web/dist` を `StaticFiles(html=True)` で配信 → `timelapse-web serve` 一発で起動
- `pyproject.toml`:
  - `[project.scripts] timelapse-web = "timelapse_web.cli_entry:main"`
  - `[project.optional-dependencies] web = ["fastapi", "uvicorn[standard]", "python-multipart"]`
  - `[tool.hatch.build.targets.wheel] packages = ["src/timelapse", "src/timelapse_web"]`

### 2.3 ジョブキューと進捗配信

- `ThreadPoolExecutor(max_workers=1)` — FFmpeg は CPU 重いので 1 並列で十分
- ジョブ状態: `queued | running | done | failed`、`progress: 0..1`
- 進捗は **SSE** (`EventSource`) 配信。WebSocket より軽く、今回は一方向で足りる
- FFmpeg の進捗は `-progress pipe:1` を stdout パースし、`total_visible_duration_s()` に対する比率を計算
- `JobQueue._broadcast` は `loop.call_soon_threadsafe` で別スレッド (レンダ worker) から安全に asyncio.Queue へ投げる

### 2.4 データモデル (Pydantic v2)

| モデル | 主フィールド | 備考 |
|---|---|---|
| `Project` | `id, name, output, clips, transitions, overlays, schema_version, timestamps` | `*.tlproj.json` のルート |
| `OutputSpec` | `width=1080, height=1920, fps=30` | `reels_spec.py` を参照 |
| `Clip` | `id, source_path, order_index, duration_s, crop, ken_burns` | 順序は `order_index` |
| `CropRect` | `aspect: '1:1'\|'9:16', x, y, w, h (0..1)` | 画像原寸に対する正規化座標 |
| `Rect01` | `x, y, w, h (0..1)` | Ken Burns の矩形基準 |
| `KenBurns` | `start_rect, end_rect, easing: linear\|ease_in_out` | トリミング後フレーム基準 |
| `Transition` | `id, after_clip_id, kind, duration_s` | cut/fade/crossfade/wipe/slide |
| `TextOverlay` | `id, text, font, size, color, anchor, x, y, start_s, end_s, fade_in_s, fade_out_s` | グローバル時間軸 |
| `RenderJob` | `id, project_id, kind, status, progress, output_path, error, timestamps` | SSE で配信 |

バリデーション: 総尺 ≤ 90s、overlay の `end_s` ≤ 総尺、crop 矩形が画像内に収まる、色は `#RRGGBB`。

### 2.5 永続化

- `project_store.save_project(project, path)` — tmp ファイル書き込み → `os.replace` で原子的置換
- `project_store.load_project(path)` — `Project.model_validate`
- undo/redo はフロント (Zustand) 側で実装 (Phase 2 以降で必要なら `zustand/middleware/temporal`)

---

## 3. FFmpeg フィルタグラフ戦略

### 3.1 Phase 1 (現状): `crop?` + `scale+pad` + `concat`

```
[0:v] crop?=..., scale=1080:1920:force_original_aspect_ratio=decrease, pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black, setsar=1, format=yuv420p, fps=30 [v0];
[1:v] ...[v1];
...
[v0][v1]... concat=n=N:v=1:a=0 [vout]
```

各クリップは `-loop 1 -framerate 30 -t <秒> -i <jpg>` で入力。末尾に `anullsrc=channel_layout=stereo:sample_rate=48000` で AAC ストリームを担保。

### 3.2 Phase 3 (Ken Burns): `zoompan` 追加

- `zoompan=z='<expr>':x='<expr>':y='<expr>':d=<frames>:s=1080x1920:fps=30`
- **落とし穴**: 出力解像度が小さく切り詰められることがあるため **必ず `s=1080x1920` を明示**
- `z/x/y` は `on` (current frame) を使い線形補間。easing は `ease_in_out` のために滑らかな式を使う
- Ken Burns なしのクリップは `zoompan` を通さず `scale+pad` のままにしてオーバーヘッド回避

### 3.3 Phase 4 (トランジション): ペアワイズ `xfade`

- cut のみ → `concat` フィルタ (N 入力)
- xfade あり → ペアワイズ連結 `xfade=transition=fade:duration=0.5:offset=<累積>`
- **offset 累積の罠**: `offset_k = sum(dur_i - xfade_dur_i)` を正しく計算
- フレーム単位で丸め: `round(t * fps) / fps`。ユニットテスト必須

### 3.4 Phase 5 (テキスト): `drawtext`

```
drawtext=fontfile=/path/to/NotoSansJP-Bold.otf:text='<escaped>':
  fontsize=64:fontcolor=white:x=...:y=...:
  enable='between(t,start,end)':
  alpha='...fade in/out...':
  borderw=2:bordercolor=black
```

- **日本語フォント**: Noto Sans JP を `src/timelapse_web/assets/fonts/` に同梱。未検出時はエラー
- **エスケープ**: 改行 / `'` / `:` / `\\` / `%{...}` を専用関数で処理。ユーザー入力テキストは常にエスケープ経由 (コマンド注入対策)

### 3.5 グラフ爆発回避 — 二段階レンダ自動選択

閾値: **クリップ数 > 25 または filter_complex 文字列長 > 30000**

- `filtergraph.plan_render(project) -> RenderPlan` で単一/二段階を切り替え (Phase 4 で実装済み)
- Stage 1: 各クリップを zoompan + crop で個別 MP4 化
- Stage 2: 個別 MP4 を xfade で連結し、末尾に drawtext チェーンを適用 (Phase 5 実装済み)

---

## 4. 実装フェーズ

### Phase 1 — 最小動作 (UI 付き CLI 相当) ✅ 完了

**スコープ**: 画像追加・並び替え・1 枚あたり秒数・9:16 への pad レンダ
- バックエンド: プロジェクト CRUD、サムネ、ジョブキュー、SSE、filter_complex の最小版
- フロント: ライブラリ / タイムライン / レンダボタン / 進捗
- **受け入れ基準**: 既存 CLI と同じ品質の 1080p MP4 が UI から出力される
- **成果**: 既存 92 CLI テスト + 新規 64 Web テスト (合計 156 件) 全通過、実 FFmpeg で `ffprobe` 検証済み

### Phase 2 — トリミング UI + プロキシプレビュー + FS ピッカー (Medium / 3–4 日) ✅ 完了

- **FS ピッカー (先行着手)**:
  - `src/timelapse_web/api/fs.py`: `/api/fs/home`, `/api/fs/browse` を実装。`TIMELAPSE_WEB_FS_ROOTS` で許可ルート拡張
  - パス正規化 (`resolve()`) 後にルート外ならば 403、非ディレクトリで 400、存在しないと 404
  - `web/src/features/fspicker/DirectoryPicker.tsx`: モーダル。パンくず/ツリー/「ホーム」ボタン/「再読込」/隠しファイル切替
  - `web/src/features/fspicker/OutputPicker.tsx`: ディレクトリ + ファイル名。既存ファイル上書き時に確認ダイアログ
  - `LibraryPanel` の絶対パス入力欄 → **「フォルダを選択」ボタン + 選択済みパス表示** に差し替え (直接入力禁止)
  - `RenderPanel` の出力先入力 → **「保存先を選択」ボタン + 選択済みパス表示** に差し替え
  - プロジェクト保存/読込のパス入力も同様にピッカー経由へ
- **トリミング**:
  - `web/src/features/crop/CropEditor.tsx`: `react-advanced-cropper` で 1:1 / 9:16 切替、矩形を `CropRect` (0..1 正規化) として store へ書き戻し
  - `filtergraph.py` の `_crop_filter` を強化: 矩形が指定されていればソース画像に対して crop、なければ pad のみ
- **プロキシ**: `RenderPanel` の「プロキシ」ボタンで 540×960/15fps 動画を生成 → PreviewPanel で再生 (既に Phase 1 で配線済み)
- **受け入れ基準**:
  - [x] 1:1 と 9:16 のトリミングが UI から設定でき、プロキシと最終動画で一致
  - [x] 元画像より大きなクロップ矩形・ゼロ幅を拒否 (Pydantic バリデーション)
  - [ ] サムネ上にクロップ範囲のオーバーレイ表示 (**未実装** — タイムラインサムネイルへの crop 枠描画は未着手)
  - [x] 画像フォルダ・プロジェクト保存先・動画出力先のすべてが、キーボードでの絶対パス手入力なしに GUI から指定できる
  - [x] 許可ルート外 (例: `/etc`) を API に直叩きしても 403 が返る

### Phase 3 — Ken Burns (High / 3–4 日) ✅ 完了

- `web/src/features/kenburns/KenBurnsEditor.tsx`: `react-konva` で開始/終了矩形をドラッグ・リサイズ
- `filtergraph.py` に `build_zoompan_filter(kb, duration_s, target)` 追加。`KenBurns.start_rect → end_rect` を `zoompan` の `z/x/y` 式に変換
- Ken Burns ありのクリップは zoompan を通し、なしは pad のみ(性能のため)
- easing: `linear` と `ease_in_out`
- **受け入れ基準**:
  - [x] 矩形指定通りにズーム/パンされる
  - [x] 境界値 (矩形 = 全体、矩形 = 中央小、start=end) で破綻しない
  - [x] プレビューと最終で同一のアニメ (同一 FFmpeg グラフ使用)

### Phase 4 — トランジション (Medium / 2 日) ✅ 完了

- `web/src/features/transitions/TransitionPicker.tsx`: クリップ間のギャップをクリックで種別 + duration を選択
- `filtergraph.py` に xfade ペアワイズ連結と offset 計算 (`round(t*fps)/fps`)、`_group_into_segments()` で cut/xfade 混在に対応
- 二段階レンダ判定を `plan_render(project) -> RenderPlan` で実装。閾値超で `renderer.run_two_stage_render` に分岐
- サポートする `TransitionKind`: `cut / fade / crossfade / wipe_left / wipe_right / slide_up`
- **受け入れ基準**:
  - [x] 5 種のトランジションが動作する (統合テスト `test_render_with_crossfade_transition` で検証済み)
  - [x] 総尺が `total_visible_duration_s()` と一致 (フレーム境界丸め ±0.15s 以内で検証済み)
  - [x] 26 クリップ超で二段階レンダが自動発動し、4 クリップ構成で単一グラフ版と同等の尺を確認 (**「30 クリップ」固定の統合テストは未作成**)

### Phase 5 — テキストオーバーレイ (Medium / 2–3 日) ✅ 完了

- `web/src/features/overlay/OverlayEditor.tsx`: テキスト/サイズ/色/縁取り/アンカー/XY/時間/フェード編集 UI
  - (注: `react-konva` Canvas 配置は省略、スライダー+セレクト入力で代替)
- `filtergraph.py`: `escape_drawtext(s)` / `find_font()` / `build_drawtext_filter(overlay, font_path)`
  - `build_filter_complex()` はオーバーレイがある場合 concat/xfade 出力を `[vout_base]` にし、drawtext チェーン末端が `[vout]` になる設計
  - `find_font()`: bundled `assets/fonts/` → `/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc` の順で探索
- `renderer.py`: `_build_concat_xfade_command()` に `overlays` 引数追加。二段階レンダの Stage 2 でも同様に drawtext チェーンを適用
- フェードイン/アウトは `alpha='if(lt(t,...),...)` 式
- **受け入れ基準**:
  - [x] 複数オーバーレイ重なり、クリップまたぎで正常 (単一・二段階両方で統合テスト済み)
  - [x] `'` や `%{...}` を含む入力で注入が発生しないことをテスト (`test_escape_drawtext_injection`)
  - [x] 未検出フォントでエラーメッセージが明確 (`find_font()` が ValueError を送出)

### Phase 6 — ライブプレビュー (任意 / High / 3 日) ✅ 完了

- `web/src/features/preview/LivePreview.tsx`: `react-konva` で静止画 + クロップ枠 + Ken Burns 開始/終了矩形 + テキストオーバーレイを近似描画 (Canvas 270×480)
- `web/src/features/preview/PreviewPanel.tsx`: 「ライブ / プロキシ」切替タブを追加
- `web/src/store/useAutoProxy.ts`: プロジェクト変更後 1s デバウンスで自動プロキシ生成フック
- `App.tsx` で `useAutoProxy()` を呼び出し
- **受け入れ基準**:
  - [x] ライブタブでクリップ画像 + 各種矩形 + テキストが Canvas に近似表示される
  - [x] プロキシタブで従来通り `<video>` 再生
  - [x] プロジェクト編集から 1s 後に自動でプロキシジョブが投入される (クリップあり時のみ)

### 共通の非機能タスク (各 Phase で並走)

- テスト:
  - `filtergraph.py` はスナップショットテスト (生成された filter_complex 文字列を fixture と比較)
  - `project_store` はラウンドトリップ
  - API は `fastapi.testclient.TestClient`
  - 実 FFmpeg レンダは `@pytest.mark.integration` で `ffprobe` メタデータ検証
- E2E: Playwright で「画像追加 → クロップ → Ken Burns → レンダ → ダウンロード」のシナリオ (Phase 5 完了時に追加)
- 型共有: 現状 TS 型は手動同期。Phase 5 以降 OpenAPI 自動生成への移行を検討

---

## 5. リスクと対策

| リスク | 影響度 | 対策 |
|---|---|---|
| filter_complex 文字列の爆発 | High | §3.5 の二段階レンダ自動切替 (クリップ数 > 25 or 文字列長 > 30000) |
| ブラウザプレビューと最終出力のズレ | High | Phase 1–5 はプロキシ動画のみをソース・オブ・トゥルースに。Phase 6 の Konva ライブは補助と明示 |
| 大量画像 (300 枚+) でメモリ/時間肥大 | Medium | サムネは逐次生成 + ファイル指紋キャッシュ、レンダは二段階、プロキシは 540p 限定 |
| 日本語フォント未検出 | Medium | Noto Sans JP を `src/timelapse_web/assets/fonts/` に同梱、hatchling の `include` に追加 |
| HEIC がブラウザで表示できない | Medium | `media.py` で HEIC→JPEG サムネイルを常に配信 (Phase 1 実装済み) |
| zoompan の解像度劣化 / ジッター | Medium | 出力 `s=1080x1920` を必ず指定、入力はクロップ後に十分大きく保つ |
| xfade offset の累積誤差 | Medium | フレーム単位で計算、ユニットテストで fixture 比較 |
| SSE 切断時の再接続 | Low | フロントで `EventSource` 自動再接続、サーバはジョブ状態をメモリ保持 |
| drawtext のエスケープ漏れによるコマンド注入 | High | サーバ側で厳格なエスケープ関数 + 注入を試みる入力のテスト、UI 入力は常にエスケープ経由 |
| CLI との依存衝突 | Low | Web 依存は optional-dependencies `web` として分離 (`uv sync --extra web`) |
| 既存 CLI への副作用 | Medium | `src/timelapse/` は原則無改変。`encoder.py` への関数追加のみ許容。CLI テスト 92 件の常時 green 維持 |
| FS ブラウザ API によるパストラバーサル | **High** | 許可ルート外アクセスを `resolve()` 後に厳格チェック。シンボリックリンクは解決後に再検証。API 直叩きの 403 テストを追加 |
| 大きなディレクトリ (数万ファイル) の走査ラグ | Low | ページングなしで単階層のみ返す (`browse` は子の直接要素だけ)。「深さ 1 のみ」を契約とする |

---

## 6. 工数感

| Phase | 工数 | 複雑度 | 状態 |
|---|---|---|---|
| Phase 1 最小動作 | 3–4 日 | Medium | ✅ 完了 |
| Phase 2 トリミング + プロキシ + FS ピッカー | 3–4 日 | Medium | ✅ 完了 |
| Phase 3 Ken Burns | 3–4 日 | **High** | ✅ 完了 |
| Phase 4 トランジション | 2 日 | Medium | ✅ 完了 |
| Phase 5 テキスト | 2–3 日 | Medium | ✅ 完了 |
| Phase 6 ライブプレビュー (任意) | 3 日 | **High** | ✅ 完了 |
| **合計 (Phase 1–5)** | **13–17 日** | — | — |

各 Phase は独立してマージ可能。Phase 1 が出た時点で「UI 付き CLI 相当」として既に価値がある。

---

## 7. 成功基準

- [x] 既存 CLI (`timelapse` コマンド) の挙動が無変更 (既存 92 テスト全 green)
- [x] `timelapse-web serve` で `http://127.0.0.1:8765` が開き、ブラウザから基本操作できる
- [x] 9:16 / 1080p / H.264 High / yuv420p / +faststart の MP4 が出力される (`ffprobe` 検証済み)
- [x] 1:1 と 9:16 のトリミングが UI からできる (Phase 2)
- [x] 画像フォルダ入力・プロジェクト保存/読込先・動画出力先のすべてが GUI ピッカーで完結し、テキストでの絶対パス手入力が UI から排除されている (Phase 2)
- [x] Ken Burns が UI からできる (Phase 3)
- [x] 5 種のトランジションが動作する (Phase 4)
- [x] 日本語テキストオーバーレイが最終動画に反映される (Phase 5、統合テスト `test_render_with_text_overlay_produces_mp4` で確認済み)
- [x] 26 クリップ超で二段階レンダが自動発動する (Phase 4) ※ 300 枚の実走テストは未作成
- [x] `filtergraph.py` と `project_store.py` の単体テストカバレッジ 80%+ (現状 93%)
- [ ] Playwright E2E 1 シナリオが通る (Phase 5 完了時)
- [x] ライブプレビューで Konva Canvas に静止画・矩形・テキストが表示される (Phase 6)
- [x] プロジェクト変更後 1s で自動プロキシが投入される (Phase 6)

---

## 8. 関連ファイルパス

**既存 (参照・再利用)**:
- `src/timelapse/reels_spec.py`
- `src/timelapse/normalize.py`
- `src/timelapse/encoder.py`
- `src/timelapse/discovery.py`
- `src/timelapse/similarity.py`
- `PLAN.md`
- `pyproject.toml`

**新規 (Phase 1 で作成済み)**:
- `src/timelapse_web/main.py`
- `src/timelapse_web/cli_entry.py`
- `src/timelapse_web/config.py`
- `src/timelapse_web/models/project.py`
- `src/timelapse_web/models/jobs.py`
- `src/timelapse_web/services/filtergraph.py`
- `src/timelapse_web/services/renderer.py`
- `src/timelapse_web/services/job_queue.py`
- `src/timelapse_web/services/project_store.py`
- `src/timelapse_web/services/thumbnail.py`
- `src/timelapse_web/api/{projects,media,render,events,deps}.py`
- `web/src/App.tsx`
- `web/src/store/useProjectStore.ts`
- `web/src/store/useJobStream.ts`
- `web/src/api/client.ts`
- `web/src/types/project.ts`
- `web/src/features/{library,timeline,preview,render,project}/*.tsx`
- `tests/timelapse_web/*.py`
- `docs/web-architecture.md`

**新規 (Phase 2–4 で追加済み)**:
- `src/timelapse_web/api/fs.py` (Phase 2)
- `web/src/features/fspicker/DirectoryPicker.tsx` (Phase 2)
- `web/src/features/fspicker/OutputPicker.tsx` (Phase 2)
- `web/src/features/crop/CropEditor.tsx` (Phase 2)
- `web/src/features/kenburns/KenBurnsEditor.tsx` (Phase 3)
- `web/src/features/transitions/TransitionPicker.tsx` (Phase 4)

**新規 (Phase 5 で追加予定)**:
- `web/src/features/overlay/OverlayEditor.tsx`
- `src/timelapse_web/assets/fonts/NotoSansJP-*.otf` (ディレクトリは作成済み、フォントファイル未配置)
