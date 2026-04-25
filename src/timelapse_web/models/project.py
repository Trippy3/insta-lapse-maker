"""プロジェクトデータモデル (*.tlproj.json のスキーマ)。"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from timelapse.reels_spec import (
    REELS_FPS,
    REELS_HEIGHT,
    REELS_MAX_DURATION_SEC,
    REELS_MIN_DURATION_SEC,
    REELS_WIDTH,
)

SCHEMA_VERSION = 1


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Rect01(BaseModel):
    """正規化座標の矩形 (0..1)。"""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(gt=0.0, le=1.0)
    h: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_bounds(self) -> "Rect01":
        if self.x + self.w > 1.0 + 1e-6:
            raise ValueError("x + w が 1.0 を超えています")
        if self.y + self.h > 1.0 + 1e-6:
            raise ValueError("y + h が 1.0 を超えています")
        return self


class CropRect(BaseModel):
    """ソース画像へのクロップ指示。"""

    model_config = ConfigDict(extra="ignore")

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    w: float = Field(gt=0.0, le=1.0)
    h: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_bounds(self) -> "CropRect":
        if self.x + self.w > 1.0 + 1e-6:
            raise ValueError("crop x+w が 1.0 を超えています")
        if self.y + self.h > 1.0 + 1e-6:
            raise ValueError("crop y+h が 1.0 を超えています")
        return self


class KenBurnsEasing(str, Enum):
    LINEAR = "linear"
    EASE_IN_OUT = "ease_in_out"


class KenBurns(BaseModel):
    start_rect: Rect01
    end_rect: Rect01
    easing: KenBurnsEasing = KenBurnsEasing.LINEAR

    @model_validator(mode="after")
    def _check_aspect(self) -> "KenBurns":
        # 出力 (9:16) キャンバス上で矩形ピクセルも 9:16 になるためには、
        # 正規化座標 (0..1) で w == h である必要がある
        # (w*W)/(h*H) = (w/h)*(W/H), W/H=9/16 なので 9/16 にするには w/h=1。
        tolerance = 0.02
        for label, r in (("start_rect", self.start_rect), ("end_rect", self.end_rect)):
            ratio = r.w / r.h
            if abs(ratio - 1.0) > tolerance:
                raise ValueError(
                    f"Ken Burns の {label} は出力アスペクト (9:16) に揃える必要があります "
                    f"(正規化座標で w == h。現在 w/h={ratio:.4f})"
                )
        return self


class Clip(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("clip"))
    source_path: str
    order_index: int = Field(ge=0)
    duration_s: float = Field(gt=0.0, le=60.0, default=0.5)
    crop: CropRect | None = None
    ken_burns: KenBurns | None = None


class TransitionKind(str, Enum):
    CUT = "cut"
    FADE = "fade"
    CROSSFADE = "crossfade"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    SLIDE_UP = "slide_up"


class Transition(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("tr"))
    after_clip_id: str
    kind: TransitionKind = TransitionKind.CUT
    duration_s: float = Field(ge=0.0, le=3.0, default=0.0)


class TextAnchor(str, Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    CENTER = "center"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_LEFT = "bottom_left"


class TextOverlay(BaseModel):
    id: str = Field(default_factory=lambda: _new_id("txt"))
    text: str = Field(min_length=1, max_length=500)
    font_family: str = "NotoSansJP"
    font_size_px: int = Field(ge=8, le=400, default=64)
    color_hex: str = "#FFFFFF"
    stroke_color_hex: str | None = "#000000"
    stroke_width_px: int = Field(ge=0, le=20, default=2)
    x: float = Field(ge=0.0, le=1.0, default=0.5)
    y: float = Field(ge=0.0, le=1.0, default=0.5)
    anchor: TextAnchor = TextAnchor.CENTER
    start_s: float = Field(ge=0.0, default=0.0)
    end_s: float = Field(gt=0.0, default=3.0)
    fade_in_s: float = Field(ge=0.0, le=5.0, default=0.0)
    fade_out_s: float = Field(ge=0.0, le=5.0, default=0.0)

    @field_validator("color_hex", "stroke_color_hex")
    @classmethod
    def _check_hex(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith("#") or len(v) not in (7, 4):
            raise ValueError("色は #RRGGBB 形式で指定してください")
        return v.upper()

    @model_validator(mode="after")
    def _check_times(self) -> "TextOverlay":
        if self.end_s <= self.start_s:
            raise ValueError("end_s は start_s より大きい必要があります")
        return self


class OutputSpec(BaseModel):
    width: int = REELS_WIDTH
    height: int = REELS_HEIGHT
    fps: int = REELS_FPS


class Project(BaseModel):
    schema_version: int = SCHEMA_VERSION
    id: str = Field(default_factory=lambda: _new_id("proj"))
    name: str = "Untitled"
    created_at: str = Field(default_factory=_utcnow)
    updated_at: str = Field(default_factory=_utcnow)
    output: OutputSpec = Field(default_factory=OutputSpec)
    clips: list[Clip] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    overlays: list[TextOverlay] = Field(default_factory=list)

    def sorted_clips(self) -> list[Clip]:
        return sorted(self.clips, key=lambda c: c.order_index)

    def total_visible_duration_s(self) -> float:
        """xfade による重なり時間を差し引いた総尺。"""
        clips = self.sorted_clips()
        if not clips:
            return 0.0
        total = sum(c.duration_s for c in clips)
        tr_by_clip = {t.after_clip_id: t for t in self.transitions}
        overlap = 0.0
        for c in clips[:-1]:
            tr = tr_by_clip.get(c.id)
            if tr and tr.kind != TransitionKind.CUT:
                overlap += tr.duration_s
        return max(0.0, total - overlap)

    @model_validator(mode="after")
    def _check_duration(self) -> "Project":
        if not self.clips:
            return self
        total = self.total_visible_duration_s()
        if total > REELS_MAX_DURATION_SEC:
            raise ValueError(
                f"総尺 {total:.2f}s が Reels 上限 {REELS_MAX_DURATION_SEC}s を超えています"
            )
        if 0 < total < REELS_MIN_DURATION_SEC:
            # 完成時のみ厳密化するため、編集中は warn を出さず通す
            pass
        # overlay の end_s が総尺内
        for o in self.overlays:
            if o.end_s > total + 1e-3:
                raise ValueError(
                    f"オーバーレイ {o.id} の end_s {o.end_s} が総尺 {total:.2f}s を超えています"
                )
        return self
