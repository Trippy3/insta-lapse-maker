# timelapse — AI エージェント向けガイド

## What

- **用途**: 絵画制作過程の写真群から Instagram Reels 用タイムラプス動画 (1080×1920 / 30fps / H.264) を生成する
- **技術スタック**:
  - Backend: Python 3.11+、FastAPI、Pydantic v2、FFmpeg 直呼び出し
  - Frontend: React 19 + Vite + Zustand、react-konva (Ken Burns / クロップエディタ)
  - パッケージ管理: uv (Python)、pnpm (JS)
- **主要モジュール**:
  - `src/timelapse/` — CLI (バッチ生成、画像探索・エンコード・正規化・類似画像検出)
  - `src/timelapse_agent/` — AI エージェント向け CLI (Skills 連携、`inspect` / `scaffold` / `render` / `crop-grid`)
    - `grid_overlay.py` — クロップ視認支援 (Pillow でグリッド付きサムネイル生成)
  - `src/timelapse_web/` — Web API サーバ (FastAPI)
    - `services/filtergraph.py` — FFmpeg filter_complex 生成の中核 (CLI / Web / Agent 共通)
    - `services/renderer.py` — FFmpeg 実行と進捗配信、二段階レンダ自動切替
    - `services/project_store.py` — `*.tlproj.json` の原子的永続化
    - `models/project.py` — プロジェクトデータモデル (Pydantic v2)
  - `web/src/` — React フロントエンド
    - `features/` — 機能別コンポーネント (timeline / crop / kenburns / transitions / overlay / preview / library / render / fspicker / project)
    - `store/useProjectStore.ts` — Zustand グローバルストア
  - `skills/timelapse-maker/` — Claude Code 向け Skill 定義 (映像ディレクター役のプロンプト)

## Why

- CLI / Web UI / AI エージェントは同じ `filtergraph.py` / `reels_spec.py` を共有し、出力品質を完全に一致させる
- xfade トランジションは「セグメント単位 concat → セグメント間 xfade」設計で filter_complex の肥大を抑制する
- クリップ数 > 25 または filter_complex 文字列長 > 30000 で二段階レンダ (`run_two_stage_render`) に自動切替
- プロジェクトファイル (`*.tlproj.json`) は CLI / Agent / Web UI の 3 者で完全互換 (Agent が生成 → Web UI で再編集 → 再レンダ、が成立する)

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

# AI エージェント CLI の動作確認
uv run python -m timelapse_agent inspect <ディレクトリ>
uv run python -m timelapse_agent scaffold <ディレクトリ> --output /tmp/test.tlproj.json
uv run python -m timelapse_agent render /tmp/test.tlproj.json --dry-run
uv run python -m timelapse_agent crop-grid <ディレクトリ> --output-dir /tmp/grid/
```

- 実装の詳細要件は `docs/web-plan.md` を参照
- モデルの制約 (`Rect01`, `CropRect`, `KenBurns`, `Transition`, `TextOverlay`) は `src/timelapse_web/models/project.py` が正本
- xfade offset 計算の設計根拠は `src/timelapse_web/services/filtergraph.py` 内のコメントを参照
- WebUI 互換のため `*.tlproj.json` 拡張子が必須 (`web/src/features/project/ProjectToolbar.tsx` の `PROJECT_EXT`)。`save_project()` 自体は強制しないので呼び出し側で明示する責任がある

## 実装状況

| Phase | 内容 | 状態 |
|-------|------|------|
| 1 | 基本動画生成 (concat + scale/pad) | 完了 |
| 2 | トリミング UI + FS ピッカー | 完了 |
| 3 | Ken Burns / zoompan | 完了 |
| 4 | 5 種トランジション + 二段階レンダ | 完了 |
| 5 | テキストオーバーレイ (drawtext) | 完了 |
| 6 | ライブプレビュー | 保留 |
| — | AI エージェント Skills 連携 (`timelapse_agent` + `skills/timelapse-maker/`) | 完了 |

## タスク別ドキュメント

- `docs/web-plan.md` — 全フェーズの要件・設計・受け入れ基準
- `docs/web-architecture.md` — Web バックエンド設計
- `docs/cli.md` — CLI のオプション一覧・使用例
- `docs/reels-spec.md` — Reels 出力仕様・セーフゾーン・対応フォーマット
- `skills/timelapse-maker/SKILL.md` — AI エージェントの判断ロジックと実行手順
- `tests/timelapse_web/test_filtergraph.py` — filter_complex 生成ロジックのテスト例
- `tests/timelapse_web/test_render_integration.py` — FFmpeg 統合テスト例
- `tests/timelapse_agent/` — AI エージェント CLI のテスト
