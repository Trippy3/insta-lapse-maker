# timelapse — AI エージェント向けガイド

## What

- **用途**: 絵画制作過程の写真群から Instagram Reels 用タイムラプス動画 (1080×1920 / 30fps / H.264) を生成する
- **技術スタック**:
  - Backend: Python 3.11+、FastAPI、Pydantic v2、FFmpeg 直呼び出し
  - Frontend: React 19 + Vite + Zustand、react-konva (Ken Burns エディタ)
  - パッケージ管理: uv (Python)、pnpm (JS)
- **主要モジュール**:
  - `src/timelapse/` — CLI ツール本体 (画像探索・エンコード・正規化)
  - `src/timelapse_web/` — Web API サーバ (FastAPI)
    - `services/filtergraph.py` — FFmpeg filter_complex 生成の中核
    - `services/renderer.py` — FFmpeg 実行と進捗配信
    - `models/project.py` — プロジェクトデータモデル (Pydantic)
  - `web/src/` — React フロントエンド
    - `features/` — 機能別コンポーネント (kenburns / transitions / fspicker など)
    - `store/useProjectStore.ts` — Zustand グローバルストア

## Why

- CLI と Web UI は同じ `filtergraph.py` / `reels_spec.py` を共有し、出力品質を一致させる
- xfade トランジションは「セグメント単位 concat → セグメント間 xfade」設計で filter_complex の肥大を抑制する
- クリップ数 > 25 または filter_complex 文字列長 > 30000 で二段階レンダ (`run_two_stage_render`) に自動切替

## How

```bash
# テスト (全件)
uv run pytest tests/

# テスト (FFmpeg 不要の単体テストのみ)
uv run pytest tests/ -m "not integration"

# フロントエンド型チェック
cd web && pnpm typecheck

# フロントエンドビルド
cd web && pnpm build
```

- 実装の詳細要件は `docs/web-plan.md` を参照
- モデルの制約 (`Rect01`, `KenBurns`, `Transition`) は `src/timelapse_web/models/project.py` が正本
- xfade offset 計算の設計根拠は `src/timelapse_web/services/filtergraph.py` 内のコメントを参照

## 実装状況

| Phase | 内容 | 状態 |
|-------|------|------|
| 1 | 基本動画生成 (concat + scale/pad) | 完了 |
| 2 | トリミング UI + FS ピッカー | 完了 |
| 3 | Ken Burns / zoompan | 完了 |
| 4 | 5 種トランジション + 二段階レンダ | 完了 |
| 5 | テキストオーバーレイ (drawtext) | 未着手 |
| 6 | ライブプレビュー | 保留 |

## タスク別ドキュメント

- `docs/web-plan.md` — 全フェーズの要件・設計・受け入れ基準
- `tests/timelapse_web/test_filtergraph.py` — filter_complex 生成ロジックのテスト例
- `tests/timelapse_web/test_render_integration.py` — FFmpeg 統合テスト例
