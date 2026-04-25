# timelapse-web アーキテクチャ (Phase 1)

CLI ツール (`src/timelapse/`) を無改変のまま再利用し、ブラウザ上から編集・レンダできる Web アプリを `src/timelapse_web/` + `web/` に同梱している。Phase 1 は CLI 相当の機能 (画像並び替え + 9:16 レターボックス出力) を UI から操作できるところまで。

## ディレクトリ

```
src/timelapse_web/      FastAPI アプリ
├── main.py             create_app() と StaticFiles マウント
├── cli_entry.py        `timelapse-web` コマンド
├── config.py           AppConfig (キャッシュ/バインド先)
├── models/             Pydantic: Project, Clip, KenBurns, Transition, TextOverlay, RenderJob
├── services/
│   ├── project_store.py    *.tlproj.json の原子的 save/load
│   ├── thumbnail.py        サムネイル生成 (HEIC→JPEG)
│   ├── filtergraph.py      filter_complex 組み立て (Phase 1 は scale+pad+concat)
│   ├── renderer.py         FFmpeg 実行 + 進捗パース (-progress pipe:1)
│   └── job_queue.py        単一ワーカーキュー + SSE ブロードキャスト
└── api/
    ├── projects.py     CRUD + save/load
    ├── media.py        ディレクトリ走査・サムネイル配信
    ├── render.py       ジョブ投入・状態取得・ファイルダウンロード
    └── events.py       SSE (/api/events/jobs)

web/                    Vite + React + TS
├── src/
│   ├── api/client.ts           fetch ラッパ
│   ├── store/useProjectStore.ts  Zustand (プロジェクト + ライブラリ + ジョブ)
│   ├── store/useJobStream.ts     SSE 購読
│   ├── features/
│   │   ├── library/LibraryPanel.tsx
│   │   ├── timeline/Timeline.tsx
│   │   ├── timeline/ClipInspector.tsx
│   │   ├── preview/PreviewPanel.tsx
│   │   ├── render/RenderPanel.tsx
│   │   └── project/ProjectToolbar.tsx
│   ├── types/project.ts        Pydantic と対応する TS 型
│   ├── App.tsx / main.tsx / styles.css
```

## レンダ経路

1. フロントがプロジェクトを `POST /api/projects` で送信し、`POST /api/render` でジョブを投入
2. `JobQueue` が 1 ワーカー (`ThreadPoolExecutor(max_workers=1)`) で順次処理
3. `renderer.run_render` が `filtergraph.build_ffmpeg_command` で組み立てたコマンドを起動
4. FFmpeg の `-progress pipe:1` 出力を行単位でパースし 0..1 の進捗をコールバック
5. コールバックがジョブ状態を更新し、`asyncio.Queue` ベースのリスナーへ
   `loop.call_soon_threadsafe` 経由でブロードキャスト
6. `/api/events/jobs` の SSE ハンドラが各リスナーからイベントを取り出して配信

## Phase 1 の filter_complex

```
[0:v] crop?=, scale=1080:1920:force_original_aspect_ratio=decrease, pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black, setsar=1, format=yuv420p, fps=30 [v0];
[1:v] ... [v1];
...
[v0][v1]... concat=n=N:v=1:a=0 [vout]
```

各クリップは `-loop 1 -t <秒> -i <jpg>` の静止画ループ入力で渡し、末尾に `anullsrc` の無音ステレオトラックを付与して Reels 仕様の AAC ストリームを担保する。

## Phase 2 以降の拡張ポイント

- **Phase 2 (トリミング UI)**: `CropRect` はすでにモデル/filtergraph に組み込み済み。フロントに `react-advanced-cropper` を乗せて矩形を書き戻すだけで動く。
- **Phase 3 (Ken Burns)**: `KenBurns.start_rect → end_rect` を `zoompan` 式に変換する関数を `filtergraph` に追加。クリップ数が多い場合は二段階レンダを有効化する判定を入れる。
- **Phase 4 (トランジション)**: `Transition.kind` に応じて `xfade=transition=...:offset=<累積>` を組み立てる。累積 offset の丸めはフレーム単位 (`round(t*fps)/fps`) で必ずユニットテスト。
- **Phase 5 (テキスト)**: `drawtext` 用の厳格なエスケープ関数を作り、`enable='between(t,start,end)'` と `alpha` 式でフェードイン/アウトを組み立てる。Noto Sans JP を `src/timelapse_web/assets/fonts/` に同梱する。

## テスト

- `tests/timelapse_web/test_project_model.py` — 総尺バリデーションと境界
- `tests/timelapse_web/test_project_store.py` — ラウンドトリップと原子的書き込み
- `tests/timelapse_web/test_filtergraph.py` — コマンド文字列の構造検証
- `tests/timelapse_web/test_api_projects.py` — CRUD + save/load + render バリデーション (`TestClient`)
- `tests/timelapse_web/test_render_integration.py` — 実 FFmpeg で MP4 が生成され ffprobe 検証が通る (`@pytest.mark.integration`)

CLI の既存 92 テストは無変更で通る (`uv run pytest`)。
