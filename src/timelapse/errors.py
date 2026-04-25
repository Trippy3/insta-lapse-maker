"""カスタム例外。"""


class TimelapseError(Exception):
    """基底例外。"""


class FFmpegNotFoundError(TimelapseError):
    """FFmpeg が見つからない場合。"""


class FFmpegVersionError(TimelapseError):
    """FFmpeg バージョンが古い場合。"""


class NoImagesFoundError(TimelapseError):
    """対象画像が見つからない場合。"""


class EncodingError(TimelapseError):
    """動画エンコード失敗。"""


class ReferenceImageNotFoundError(TimelapseError):
    """基準画像が見つからない場合。"""


class InvalidImageError(TimelapseError):
    """画像を開けない・デコードできない場合。"""
