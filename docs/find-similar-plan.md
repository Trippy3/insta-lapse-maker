# 実装計画: `timelapse find-similar` サブコマンド

作成日: 2026-04-18

---

## 概要

指定した基準画像に視覚的に類似した画像を、検索フォルダから抽出して一覧出力するCLIサブコマンドを追加する。タイムラプス動画生成の前処理として、混在した撮影データから同一絵画の連続撮影を自動選別することが目的。

---

## 1. アルゴリズム選定

### 候補手法の比較

| 手法 | 長所 | 短所 | 適合度 |
|------|------|------|--------|
| ピクセル差分 (MSE/SSIM) | Pillowのみ、実装簡単 | 明度・角度変化に脆弱 | 低 |
| aHash | 超高速 | 精度低、偽陽性多い | 中 |
| dHash | 高速、aHashより頑健 | 僅かな色変化に弱い | 中〜高 |
| **pHash (Perceptual Hash)** | DCT利用で頑健。回転・リサイズ・軽微な編集に強い | aHash/dHashよりわずかにコスト高 | **高（デフォルト）** |
| カラーヒストグラム | 全体の色調類似を判断 | 構図無視、色が似た別画像も拾う | 高（補助） |
| ORB/AKAZE 特徴量 | 非常に頑健 | OpenCV依存、計算コスト高 | 中（過剰） |

### 採用方針

- **デフォルト戦略**: pHash（DCT低周波成分を使うため、絵画制作途中画像のように「構図は同じ・色が徐々に変わる」性質に最適）
- **補助モード**: ヒストグラム相関（`--strategy combined` でpHashとAND条件）
- **ライブラリ**: `imagehash>=4.3`（純Python+Pillow+NumPy、軽量）
- **しきい値**: pHaシュハミング距離 デフォルト `10`（64ビット中 ~84%類似）

---

## 2. CLIインターフェース

```
timelapse find-similar REFERENCE SEARCH_DIR [OPTIONS]

Arguments:
  REFERENCE    基準画像ファイルパス (必須)
  SEARCH_DIR   検索対象ディレクトリ (必須)

Options:
  -t, --threshold INT     ハミング距離しきい値 (default: 10, 0=完全一致)
  -S, --strategy TEXT     phash|dhash|ahash|histogram|combined (default: phash)
  -F, --format TEXT       plain|json|scored (default: plain)
      --sort TEXT         similarity|filename (default: similarity)
  -r, --recursive         サブディレクトリも再帰検索
      --max-workers INT   並列ワーカー数 (default: CPU数)
      --cache             ハッシュキャッシュを有効化 (~/.cache/timelapse/hashes.json)
      --cache-dir PATH    キャッシュ保存先ディレクトリ (default: ~/.cache/timelapse)
```

### 出力例

**plain** (default, stdout):
```
./photos/IMG_001.jpg
./photos/IMG_002.jpg
./photos/IMG_005.jpg
```

**json** (`--format json`):
```json
[
  {"path": "./photos/IMG_001.jpg", "score": 0.97, "distance": 2},
  {"path": "./photos/IMG_002.jpg", "score": 0.92, "distance": 5}
]
```

**scored** (`--format scored`):
```
0.97  2  ./photos/IMG_001.jpg
0.92  5  ./photos/IMG_002.jpg
```

> 結果は **stdout**、進捗バーは **stderr** に分離（パイプ連携可能）

---

## 3. ファイル構成

### 新規作成

| ファイル | 役割 |
|---------|------|
| `src/timelapse/similarity.py` | ハッシュ計算・類似度判定・ハッシュキャッシュ |
| `src/timelapse/similarity_output.py` | 出力フォーマッタ (plain/json/scored) |
| `tests/test_similarity.py` | similarity.py の単体テスト |
| `tests/test_similarity_output.py` | 出力フォーマッタのテスト |
| `tests/test_cli_find_similar.py` | CLIサブコマンド統合テスト |

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `src/timelapse/cli.py` | `find-similar` サブコマンド追加 |
| `src/timelapse/discovery.py` | `recursive: bool = False` パラメータ追加（後方互換） |
| `src/timelapse/errors.py` | `ReferenceImageNotFoundError`, `InvalidImageError` 追加 |
| `pyproject.toml` | `imagehash>=4.3` 依存追加 |
| `README.md` | `find-similar` 使用例追記 |

---

## 4. 実装フェーズ

### Phase 1: コアロジック（TDD）

| ステップ | ファイル | 内容 |
|---------|---------|------|
| 1 | `errors.py` | `ReferenceImageNotFoundError`, `InvalidImageError` 追加 |
| 2 | `similarity.py` | `SimilarityStrategy` Enum 定義 |
| 3 | `similarity.py` | `compute_hash()` — EXIF回転補正後にimagehashへ委譲 |
| 4 | `similarity.py` | `compute_histogram_correlation()` — NumPy正規化相関係数 |
| 5 | `similarity.py` | `SimilarityResult` frozen dataclass (path, score, distance) |
| 6 | `similarity.py` | `find_similar_images()` — ThreadPoolExecutorで並列ハッシュ化+しきい値フィルタ |
| 7 | `similarity.py` | `HashCache` クラス — mtime/sizeベース無効化、JSONシリアライズ |

### Phase 2: CLI統合

| ステップ | ファイル | 内容 |
|---------|---------|------|
| 8 | `discovery.py` | `recursive` オプション追加（rglob対応） |
| 9 | `similarity_output.py` | `OutputFormat` Enum + `format_results()` 関数 |
| 10 | `cli.py` | `find-similar` サブコマンド実装（rich Progressでstderrに進捗） |

### Phase 3: テスト & ドキュメント

| ステップ | ファイル | 内容 |
|---------|---------|------|
| 11 | `tests/conftest.py` | Pillowで動的生成するテスト画像フィクスチャ追加 |
| 12 | `tests/test_similarity.py` | 各戦略・しきい値境界値・異常系・並列処理テスト |
| 13 | `tests/test_similarity_output.py` | 3形式のスナップショットテスト |
| 14 | `tests/test_cli_find_similar.py` | CliRunnerによる統合テスト |
| 15 | `README.md` | `find-similar` 使用例・オプション表追記 |

---

## 5. ハッシュキャッシュ設計

```
~/.cache/timelapse/hashes.json
{
  "/abs/path/to/img.jpg": {
    "mtime": 1713400000.0,
    "size": 204800,
    "phash": "f8e0c0a0f0e0d0c0",
    "dhash": "..."
  }
}
```

- キャッシュヒット条件: `mtime` + `size` が一致
- ロード: `find-similar` 実行時に一括読み込み
- 保存: 新規ハッシュ計算後にアトミック書き込み（`tempfile` → `rename`）
- オプション: `--cache` で有効化、`--cache-dir PATH` でディレクトリ変更可

---

## 6. データフロー

```
REFERENCE画像
    ↓ compute_hash()
reference_hash
    ↓
SEARCH_DIR → discover_images() → [candidate_paths]
    ↓ ThreadPoolExecutor(compute_hash)
[(path, hash), ...]
    ↓ ハミング距離 / ヒストグラム相関
[SimilarityResult, ...]  ← しきい値でフィルタ
    ↓ ソート（similarity / filename）
    ↓ format_results()
stdout (plain / json / scored)
```

---

## 7. リスク & 対策

| リスク | 影響 | 対策 |
|--------|------|------|
| pHash偽陽性（同色調の別絵） | 中 | `--strategy combined` でヒストグラムとAND条件 |
| 500枚処理の遅延 | 中 | ThreadPoolExecutorで並列ハッシュ化 |
| EXIF回転未考慮でハッシュ変化 | 中 | `ImageOps.exif_transpose()` をハッシュ化前に適用 |
| HEIC画像のハッシュ化失敗 | 中 | `pillow-heif.register_heif_opener()` をモジュールロード時に呼ぶ |
| 壊れた画像でクラッシュ | 中 | `InvalidImageError` でキャッチ → 警告ログ + スキップ |
| 既存 `generate` の挙動破壊 | 中 | `recursive=False` デフォルトで後方互換 |
| キャッシュ整合性破綻 | 中 | mtime+sizeで無効化判定、アトミック書き込みで破損防止 |

---

## 8. テスト戦略

- **Unit Tests**: 各戦略のハッシュ計算、しきい値境界値、並列処理の順序保持、異常系（壊れた画像・存在しないパス）
- **Integration Tests**: `CliRunner` で各オプション組合せを実行、stdout/stderrの分離検証、exit code検証
- **Fixtures**: `conftest.py` でPillowを使い動的生成（基準画像、類似画像=色微変化、無関係画像=別構図）
- **カバレッジ目標**: 80%+

---

## 9. 工数見積もり

| Phase | 内容 | 見積 |
|-------|------|------|
| Phase 1 | コアロジック（similarity.py） | 3〜4h |
| Phase 2 | CLI統合 | 2〜3h |
| Phase 3 | テスト & ドキュメント | 3〜4h |
| (ハッシュキャッシュはPhase 1に含む) | | |
| **合計** | | **8〜11h** |

---

## 10. 成功基準

- [ ] `timelapse find-similar ref.jpg ./photos/` でパス一覧がstdoutに出力される
- [ ] `--format json` が valid JSONを返し、`jq` で処理可能
- [ ] 500枚ディレクトリで処理時間30秒以内（ハッシュ化並列化込み）
- [ ] pHash / dHash / aHash / histogram / combined の5戦略が切替可能
- [ ] HEIC を含む混在フォーマットで動作
- [ ] `--cache` でハッシュを永続化し、再実行が高速化される
- [ ] 既存 `generate` サブコマンドのテスト・挙動が壊れない
- [ ] テストカバレッジ 80%+
- [ ] README にユースケース例記載
