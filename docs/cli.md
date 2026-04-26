# CLI リファレンス

`timelapse` は写真ディレクトリを 1 コマンドで Reels 用 MP4 に変換するツールです。編集 UI が不要なバッチ用途に向いています。

## 基本

```bash
uv run timelapse generate ./photos
```

`./photos` 内の画像をファイル名順で並べ、カレントディレクトリに `output.mp4` を生成します。

## オプション

```
timelapse generate [OPTIONS] INPUT_DIR

引数:
  INPUT_DIR             写真が格納されたディレクトリ (必須)

オプション:
  -o, --output PATH     出力 MP4 ファイルパス          [default: output.mp4]
  -d, --duration FLOAT  1 枚あたりの表示秒数           [default: 0.3]
  --fps FLOAT           フレームレート                 [default: 30.0]
  -s, --sort            ソート順 (filename / exif)     [default: filename]
  -f, --fit             アスペクト比調整 (pad / crop)  [default: pad]
  --dry-run             エンコードせず設定だけ確認
  -v, --verbose         詳細ログを表示
```

## 使用例

```bash
# 出力先・1 枚あたりの表示時間を指定
uv run timelapse generate ./photos -o timelapse.mp4 -d 0.5

# EXIF 撮影日時順でソート
uv run timelapse generate ./photos --sort exif

# 横長写真を中央クロップして縦型に変換 (黒帯なし)
uv run timelapse generate ./photos --fit crop

# エンコードせず設定だけ確認
uv run timelapse generate ./photos --dry-run

# 速いタイムラプス (1 枚 0.1 秒)
uv run timelapse generate ./photos -d 0.1 -o fast.mp4
```

## ソート順

| オプション | 動作 |
|-----------|------|
| `filename` (デフォルト) | ファイル名の自然順 (`img9.jpg` → `img10.jpg`) |
| `exif` | EXIF 撮影日時順。日時情報がない画像はファイル名順で末尾に追加 |

## アスペクト比調整 (`--fit`)

### `pad` (デフォルト)

元のアスペクト比を保ったまま、余白を黒帯で埋めます。**絵画全体が見える**ことを優先する場合に適しています。

### `crop`

中央を基準にクロップし、黒帯なしで画面を埋めます。**フル画面で見せたい**場合に適しています。

詳細は [`docs/reels-spec.md`](reels-spec.md) を参照してください。
