# 実装計画: 絵画制作タイムラプス CLI ツール

作成日: 2026-04-17

---

## 概要

絵画制作過程を撮影した写真群を入力として、Instagram Reels 仕様に準拠したタイムラプス動画を生成する CLI ツール。
Python + FFmpeg を中核に据え、MVP では基本的な動画生成機能を、拡張フェーズで BGM・テキストオーバーレイ・トランジションなどの表現機能を提供する。

---

## 1. 技術スタック

| カテゴリ | 採用技術 | 理由 |
|---------|---------|------|
| 言語 | **Python 3.11+** | 画像/動画処理エコシステムが最も充実。1人開発に向く |
| 動画処理 | **FFmpeg** (直呼び出し or ffmpeg-python) | 業界標準。Reels 仕様のコーデック・ビットレート制御が完全に可能 |
| 画像処理 | **Pillow** | リサイズ、クロップ、パディング、テキストオーバーレイに十分 |
| CLI | **Typer** | 型ヒント駆動で直感的。ヘルプ生成と補完が強力 |
| 設定管理 | **Pydantic v2** | 入力バリデーションと設定ファイル(YAML/TOML)のパース |
| UX | **rich** | CLI の進捗バー・カラーログで UX を向上 |
| パッケージ管理 | **uv** | 高速インストール、ロックファイル管理 |
| テスト | **pytest + pytest-mock** | デファクト。FFmpeg 呼び出しはモック化 |

---

## 2. Instagram Reels 仕様（2026年4月 推奨値）

| 項目 | 値 |
|------|---|
| フォーマット | MP4 (MOV も可) |
| 動画コーデック | **H.264** (High Profile, Level 4.0+) |
| 音声コーデック | **AAC-LC**, 48kHz, 128kbps 以上, ステレオ |
| 解像度 | **1080 x 1920** (フル HD 縦型) |
| アスペクト比 | **9:16** |
| フレームレート | **30fps** 推奨 (23-60fps 許容) |
| 動画長 | 最小 3秒 / 最大 90秒 |
| ファイルサイズ | **4GB** 上限 |
| ビットレート | 3.5〜8 Mbps (5Mbps 前後が標準) |
| 色空間 | BT.709 (sRGB) |
| GOP (キーフレーム間隔) | 2秒以下推奨 |
| 最大 B フレーム | 2 |
| クロマサブサンプリング | 4:2:0 |
| **必須フラグ** | `-movflags +faststart` |

### セーフゾーン

Reels には UI 要素（キャプション、アクションボタン、プロフィール）が上下に重なります。

- **上部**: 約 250px のマージン
- **下部**: 約 450-650px のマージン（キャプション・CTA・コメント領域）
- 主要被写体は中央 **1080 x 1220** 程度に収める

---

## 3. 機能仕様

### Phase 1 — MVP（投稿可能な動画を生成）

- 入力: 写真が格納されたディレクトリパス
- ソート: ファイル名昇順 または EXIF 撮影日時
- 1枚あたりの表示時間指定 (秒、デフォルト 0.3s)
- 出力: 1080x1920 MP4 (H.264/AAC, 30fps)
- アスペクト比の自動調整: レターボックス(pad) または クロップ(crop)
- 進捗表示 (rich progress bar)
- ドライラン (実際にエンコードせず設定のみ検証)

### Phase 2 — 表現機能

- **BGM 追加**: 音声ファイル(mp3/aac/wav)を指定、動画長に合わせて自動フェードイン/アウト
- **テキストオーバーレイ**: タイトル/キャプション画像生成(Pillow) → FFmpeg overlay
- **ホールドフレーム**: 開始・終了画像の静止時間を個別指定

### Phase 3 — ポリッシュ

- **クロスフェードトランジション** (FFmpeg xfade フィルタ)
- **手ブレ補正**: OpenCV ORB 特徴点マッチングによる位置合わせ
- **明るさ正規化**: ヒストグラムマッチングで照明変化を吸収
- **YAML/TOML 設定ファイル対応**
- **プリセット**: slow / standard / fast / reels-optimized

### Phase 4 — 運用機能（任意）

- Instagram Graph API 経由で直接アップロード
- サムネイル(カバー画像)自動生成
- 複数解像度同時出力 (Reels / Stories / Feed)

---

## 4. プロジェクト構造

```
timelapse/
├── pyproject.toml
├── README.md
├── .gitignore
├── .python-version
├── src/
│   └── timelapse/
│       ├── __init__.py
│       ├── cli.py                # Typer エントリポイント
│       ├── reels_spec.py         # Instagram Reels 仕様定数
│       ├── config.py             # Pydantic 設定モデル
│       ├── system.py             # FFmpeg 検出などシステムユーティリティ
│       ├── discovery.py          # 画像ファイル列挙・ソート
│       ├── normalize.py          # リサイズ・パディング・EXIF 回転
│       ├── encoder.py            # FFmpeg 呼び出し(動画生成)
│       ├── audio.py              # BGM 合成 (Phase 2)
│       ├── overlay.py            # テキスト/ロゴオーバーレイ (Phase 2)
│       ├── transitions.py        # クロスフェード等 (Phase 3)
│       ├── align.py              # 画像位置合わせ (Phase 3)
│       ├── exposure.py           # 明るさ正規化 (Phase 3)
│       ├── timing.py             # 表示時間・速度カーブ
│       ├── logging_setup.py      # rich ロガー設定
│       └── errors.py             # カスタム例外
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   └── sample_images/        # テスト用小サイズ画像
│   ├── test_discovery.py
│   ├── test_normalize.py
│   ├── test_encoder.py
│   ├── test_cli.py
│   └── test_config.py
├── docs/
│   └── reels-spec.md
└── examples/
    ├── basic.yaml
    └── with-bgm.yaml
```

---

## 5. 実装フェーズ詳細

### Phase 1: MVP (基礎動画生成)

| ステップ | ファイル | 内容 |
|---------|---------|------|
| 1 | `pyproject.toml` | `uv init` でプロジェクト作成、依存関係宣言 |
| 2 | `system.py` | FFmpeg 存在確認・バージョン検出 |
| 3 | `discovery.py` | ディレクトリ走査、JPEG/PNG/HEIC 収集、ファイル名/EXIF ソート |
| 4 | `normalize.py` | 全画像を 1080x1920 に変換 (pad/crop)、EXIF 回転適用 |
| 5 | `encoder.py` | FFmpeg concat demuxer で H.264 MP4 生成 |
| 6 | `cli.py` | Typer で `timelapse generate <input_dir> -o output.mp4` 実装 |
| 7 | `reels_spec.py` | 仕様定数を集約 |
| 8 | `tests/` | 単体テスト + 統合テスト (ffprobe で出力検証) |

### Phase 2: BGM とテキストオーバーレイ

| ステップ | ファイル | 内容 |
|---------|---------|------|
| 9 | `audio.py` | BGM トリミング、afade フェードイン/アウト |
| 10 | `overlay.py` | Pillow でタイトル画像生成、FFmpeg overlay 合成 |
| 11 | `timing.py` | ホールドフレーム (先頭/末尾の静止時間個別指定) |

### Phase 3: トランジションとポリッシュ

| ステップ | ファイル | 内容 |
|---------|---------|------|
| 12 | `transitions.py` | FFmpeg xfade フィルタ |
| 13 | `align.py` | OpenCV ORB 特徴点抽出、ホモグラフィ位置合わせ |
| 14 | `exposure.py` | ヒストグラムマッチングによる明るさ正規化 |
| 15 | `config.py` | Pydantic モデルで YAML/TOML 読み込み |

---

## 6. リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Instagram Reels 仕様の変更 | High | `reels_spec.py` に集約、`ffprobe` で出力を自動検証 |
| FFmpeg が未インストール/古いバージョン | High | 起動時検出、v6.0+ 要求、README にインストールガイド |
| エンコード品質でリールに拒否される | High | Meta 公式と同等パラメータ採用、ffprobe で自動アサート |
| 大量画像(500枚以上)で処理時間肥大 | Medium | rich 進捗表示、逐次処理 + 一時ファイル経由 |
| HEIC/RAW フォーマット非対応 | Medium | `pillow-heif` オプション依存、未サポートは警告スキップ |
| 日本語フォントの欠落 | Medium | NotoSansJP 同梱 or システムフォント検出 |
| xfade フィルタグラフの肥大化 | Medium | 枚数閾値超で自動無効化、ドキュメントに制限明記 |
| EXIF 未登録画像のソート不定 | Low | ファイル名フォールバック、曖昧時は警告 |

---

## 7. テスト戦略

- **単体テスト**: `discovery` / `normalize` / `config` / `timing` ロジックを 80%+ カバー
- **統合テスト**: 小サンプル画像 3-5 枚で実際に FFmpeg を起動、`ffprobe` で出力動画のメタデータ(解像度/fps/コーデック)を検証
- **E2E テスト**: CLI を subprocess で起動、期待される出力ファイル生成を確認
- **仕様準拠チェック**: 出力動画を `ffprobe -show_format -show_streams` で検査し Reels 仕様を自動アサート

---

## 8. 工数見積もり

| フェーズ | 工数目安 | 複雑度 | 主要リスク |
|---------|---------|--------|-----------|
| Phase 1 (MVP) | 2-3 日 | Medium | FFmpeg パラメータチューニング |
| Phase 2 (BGM/Overlay) | 2 日 | Medium | 音量正規化、フォント処理 |
| Phase 3 (Transition/Align) | 3-4 日 | High | OpenCV 連携、xfade グラフ生成 |
| Phase 4 (API 連携) | 3-5 日 | High | Meta 認証、レビュー手続き |

**Phase 1 のみで Instagram Reels 投稿可能な動画が得られる設計です。**

---

## 9. 成功基準

- [ ] 任意の画像ディレクトリから 30fps/1080x1920/H.264 MP4 を生成できる
- [ ] 生成動画が Instagram Reels にアップロードでき、品質劣化が目立たない
- [ ] ファイル名/EXIF 両ソート方式が動作
- [ ] BGM 付き動画を生成でき、フェードイン/アウトが適用される (Phase 2)
- [ ] テストカバレッジ 80%+
- [ ] `timelapse --help` で全オプションが明確に表示される
- [ ] README に最小サンプルと詳細オプションが記載されている
