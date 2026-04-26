"""FFmpeg filter_complex とコマンド引数を組み立てる。

設計方針:
- 既存 `timelapse.reels_spec` の定数を正とする (1080x1920 / 30fps / H.264 High / +faststart)
- 出力先の解像度は OutputSpec から受け取る (プロキシ生成時は縮小可能)
- 生成したコマンド文字列はスナップショットテストで検証可能にする
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from timelapse.reels_spec import (
    AUDIO_BITRATE,
    AUDIO_CHANNELS,
    AUDIO_CODEC,
    AUDIO_SAMPLE_RATE,
    MOVFLAGS,
    VIDEO_BITRATE,
    VIDEO_BUFSIZE,
    VIDEO_CODEC,
    VIDEO_GOP_SEC,
    VIDEO_LEVEL,
    VIDEO_MAX_B_FRAMES,
    VIDEO_MAXRATE,
    VIDEO_PIX_FMT,
    VIDEO_PROFILE,
)

from ..models import Clip, CropRect, KenBurns, Project
from ..models.project import KenBurnsEasing, TextAnchor, TextOverlay, Transition, TransitionKind

_XFADE_NAMES: dict[TransitionKind, str] = {
    TransitionKind.FADE: "fade",
    TransitionKind.CROSSFADE: "dissolve",
    TransitionKind.WIPE_LEFT: "wipeleft",
    TransitionKind.WIPE_RIGHT: "wiperight",
    TransitionKind.SLIDE_UP: "slideup",
}


@dataclass(frozen=True)
class RenderTarget:
    width: int
    height: int
    fps: int
    # プロキシ用に品質を落とすためのオーバーライド
    video_bitrate: str = VIDEO_BITRATE
    video_maxrate: str = VIDEO_MAXRATE
    video_bufsize: str = VIDEO_BUFSIZE

    @classmethod
    def from_project(cls, project: Project) -> "RenderTarget":
        return cls(
            width=project.output.width,
            height=project.output.height,
            fps=project.output.fps,
        )

    @classmethod
    def proxy(cls, project: Project, scale: float = 0.5, fps: int = 15) -> "RenderTarget":
        w = int(project.output.width * scale)
        h = int(project.output.height * scale)
        # yuv420p は偶数解像度が必要
        w = w - (w % 2)
        h = h - (h % 2)
        return cls(
            width=w,
            height=h,
            fps=fps,
            video_bitrate="1500k",
            video_maxrate="2000k",
            video_bufsize="3000k",
        )


def _crop_filter(crop: CropRect | None) -> str | None:
    """正規化クロップ矩形を FFmpeg crop フィルタ式に変換する。None の場合は中央から
    縦:横 = 16:9 を守る最大サイズのクロップを返す (aspect 指定なし)。"""
    if crop is None:
        return None
    # in_w / in_h ベースで式を組む (解像度非依存)
    x_expr = f"in_w*{crop.x:.6f}"
    y_expr = f"in_h*{crop.y:.6f}"
    w_expr = f"in_w*{crop.w:.6f}"
    h_expr = f"in_h*{crop.h:.6f}"
    return f"crop={w_expr}:{h_expr}:{x_expr}:{y_expr}"


def build_zoompan_filter(
    kb: KenBurns,
    duration_s: float,
    target: RenderTarget,
) -> str:
    """Ken Burns を zoompan フィルタ式に変換する。

    入力は scale+pad 済みの target.width × target.height フレームで、矩形は
    正規化 (0..1) 座標で、出力アスペクト (9:16) と同じアスペクトを持つ前提。

    - 線形補間: t = on/(d-1)
    - ease_in_out: t' = 0.5 * (1 - cos(PI * t))
    - zoom = 1 / w_interp (w_interp == h_interp となる矩形を前提)
    - pan (x, y) は pixel 単位で iw / ih 倍する
    """
    d = max(1, round(duration_s * target.fps))
    sr, er = kb.start_rect, kb.end_rect

    # on 変数を直接使う。d==1 のときはゼロ除算を避けて定数 0 にする。
    if d <= 1:
        raw_t = "0"
    else:
        raw_t = f"(on/{d - 1})"

    if kb.easing == KenBurnsEasing.EASE_IN_OUT:
        t_expr = f"(0.5*(1-cos(PI*{raw_t})))"
    else:
        t_expr = raw_t

    # 各成分を線形 or イージング済み t で補間
    def lerp(a: float, b: float) -> str:
        if abs(a - b) < 1e-9:
            return f"{a:.6f}"
        return f"({a:.6f}+({b - a:.6f})*{t_expr})"

    w_interp = lerp(sr.w, er.w)
    x_interp = lerp(sr.x, er.x)
    y_interp = lerp(sr.y, er.y)

    z_expr = f"(1/{w_interp})"
    x_expr = f"({x_interp}*iw)"
    y_expr = f"({y_interp}*ih)"

    # s= は出力解像度、fps= は出力フレームレート
    return (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':"
        f"d={d}:s={target.width}x{target.height}:fps={target.fps}"
    )


def _scale_pad_filter(target: RenderTarget) -> str:
    """出力サイズにアスペクト比を保ったまま収め、余白は黒帯 (letterbox)。"""
    w, h = target.width, target.height
    return (
        f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1"
    )


def build_clip_chain(clip: Clip, target: RenderTarget, stream_idx: int) -> str:
    """1 クリップ分のフィルタチェーン (入力ラベル → [v<idx>])。

    順序: loop+trim+setpts → crop? → scale+pad → (zoompan?) → format → fps → settb
    JPEG を -loop 1 で繰り返しデコードするとタイムベースが 1/1000000 にリセット
    されて xfade が失敗するため、loop フィルタで単一フレームをメモリ上でループする。
    """
    n_frames = max(1, round(clip.duration_s * target.fps))
    parts: list[str] = []
    parts.append(f"[{stream_idx}:v]")
    sub: list[str] = []
    sub.append(f"loop=loop=-1:size=1:start=0")
    sub.append(f"trim=end_frame={n_frames}")
    sub.append(f"setpts=PTS-STARTPTS")
    if (cf := _crop_filter(clip.crop)) is not None:
        sub.append(cf)
    sub.append(_scale_pad_filter(target))
    if clip.ken_burns is not None:
        sub.append(build_zoompan_filter(clip.ken_burns, clip.duration_s, target))
    sub.append(f"format={VIDEO_PIX_FMT}")
    sub.append(f"fps={target.fps}")
    sub.append(f"settb=1/{target.fps}")
    parts.append(",".join(sub))
    parts.append(f"[v{stream_idx}]")
    return "".join(parts)


def escape_drawtext(s: str) -> str:
    """drawtext の text オプション値として安全なエスケープを施す。

    順序は重要: バックスラッシュを最初に処理してから他の文字を置換する。
    """
    s = s.replace("\\", "\\\\")
    s = s.replace("'", "\\'")
    s = s.replace(":", "\\:")
    s = s.replace("%{", "%%{")
    s = s.replace("\n", " ")
    return s


def _hex_to_ffmpeg_color(color_hex: str) -> str:
    """#RRGGBB → 0xRRGGBB。"""
    return "0x" + color_hex.lstrip("#")


_ANCHOR_EXPR: dict[TextAnchor, tuple[str, str]] = {
    TextAnchor.TOP_LEFT: ("W*{x}", "H*{y}"),
    TextAnchor.TOP_CENTER: ("W*{x}-tw/2", "H*{y}"),
    TextAnchor.CENTER: ("W*{x}-tw/2", "H*{y}-th/2"),
    TextAnchor.BOTTOM_CENTER: ("W*{x}-tw/2", "H*{y}-th"),
    TextAnchor.BOTTOM_LEFT: ("W*{x}", "H*{y}-th"),
}

_SYSTEM_FONT_CANDIDATES: list[Path] = [
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc"),
    Path("/usr/local/share/fonts/NotoSansJP-Bold.otf"),
    Path("/Library/Fonts/NotoSansCJK-Bold.ttc"),
]


def find_font() -> Path:
    """Noto Sans JP フォントを返す。bundled → system の順で探索する。

    どちらにも見つからない場合は ValueError を送出する。
    """
    bundled_dir = Path(__file__).parent.parent / "assets" / "fonts"
    for name in ("NotoSansJP-Bold.otf", "NotoSansCJK-Bold.ttc", "NotoSansCJK-Regular.ttc"):
        p = bundled_dir / name
        if p.exists():
            return p

    for p in _SYSTEM_FONT_CANDIDATES:
        if p.exists():
            return p

    raise ValueError(
        "Noto Sans JP フォントが見つかりません。"
        "`apt install fonts-noto-cjk` でインストールするか、"
        "src/timelapse_web/assets/fonts/ に配置してください。"
    )


def build_drawtext_filter(overlay: TextOverlay, font_path: Path) -> str:
    """TextOverlay を FFmpeg drawtext フィルタ文字列に変換する。"""
    escaped = escape_drawtext(overlay.text)
    color = _hex_to_ffmpeg_color(overlay.color_hex)

    x_tmpl, y_tmpl = _ANCHOR_EXPR[overlay.anchor]
    x_expr = x_tmpl.format(x=overlay.x, y=overlay.y)
    y_expr = y_tmpl.format(x=overlay.x, y=overlay.y)

    parts = [
        f"drawtext=fontfile={font_path}",
        f"text='{escaped}'",
        f"fontsize={overlay.font_size_px}",
        f"fontcolor={color}",
        f"x={x_expr}",
        f"y={y_expr}",
        f"enable='between(t,{overlay.start_s},{overlay.end_s})'",
    ]

    if overlay.stroke_color_hex is not None and overlay.stroke_width_px > 0:
        parts.append(f"borderw={overlay.stroke_width_px}")
        parts.append(f"bordercolor={_hex_to_ffmpeg_color(overlay.stroke_color_hex)}")

    if overlay.fade_in_s > 0 or overlay.fade_out_s > 0:
        s, e, fi, fo = overlay.start_s, overlay.end_s, overlay.fade_in_s, overlay.fade_out_s
        if fi > 0 and fo > 0:
            alpha = (
                f"if(lt(t,{s + fi}),(t-{s})/{fi},"
                f"if(gt(t,{e - fo}),({e}-t)/{fo},1))"
            )
        elif fi > 0:
            alpha = f"if(lt(t,{s + fi}),(t-{s})/{fi},1)"
        else:
            alpha = f"if(gt(t,{e - fo}),({e}-t)/{fo},1)"
        parts.append(f"alpha='{alpha}'")

    return ":".join(parts)


def _group_into_segments(
    clips: list[Clip],
    tr_by_clip_id: dict[str, Transition],
) -> list[tuple[list[Clip], Transition | None]]:
    """クリップを cut 境界でセグメントに分割する。

    各セグメントは (clip_list, out_transition) のタプル。
    out_transition は次のセグメントへの非 cut トランジション (最終は None)。
    """
    if not clips:
        return []
    segments: list[tuple[list[Clip], Transition | None]] = []
    current: list[Clip] = [clips[0]]
    for i in range(1, len(clips)):
        prev = clips[i - 1]
        tr = tr_by_clip_id.get(prev.id)
        if tr is None or tr.kind == TransitionKind.CUT:
            current.append(clips[i])
        else:
            segments.append((current, tr))
            current = [clips[i]]
    segments.append((current, None))
    return segments


def build_filter_complex(project: Project, target: RenderTarget) -> str:
    """プロジェクトから filter_complex 文字列を組み立てる。"""
    clips = project.sorted_clips()
    if not clips:
        raise ValueError("clips が空です")

    overlays = project.overlays
    has_overlays = bool(overlays)
    # drawtext チェーンがある場合は concat/xfade の出力を vout_base とし、
    # drawtext チェーンの末端が vout になる
    base_label = "vout_base" if has_overlays else "vout"

    clip_idx = {c.id: i for i, c in enumerate(clips)}
    tr_by_clip_id = {t.after_clip_id: t for t in project.transitions}
    segments = _group_into_segments(clips, tr_by_clip_id)

    filters: list[str] = [build_clip_chain(c, target, clip_idx[c.id]) for c in clips]

    # セグメントが 1 つなら従来 concat
    if len(segments) == 1:
        seg_clips = segments[0][0]
        inputs = "".join(f"[v{clip_idx[c.id]}]" for c in seg_clips)
        filters.append(f"{inputs}concat=n={len(seg_clips)}:v=1:a=0[{base_label}]")
    else:
        # セグメントごとに内部 concat を作り、ラベルを決定
        # concat の出力タイムベースは AV_TIME_BASE_Q (1/1000000) に強制
        # リセットされるため、xfade に渡す前に settb で再正規化する。
        seg_labels: list[str] = []
        for k, (seg_clips, _) in enumerate(segments):
            if len(seg_clips) == 1:
                seg_labels.append(f"v{clip_idx[seg_clips[0].id]}")
            else:
                inputs = "".join(f"[v{clip_idx[c.id]}]" for c in seg_clips)
                label = f"seg{k}"
                filters.append(
                    f"{inputs}concat=n={len(seg_clips)}:v=1:a=0,"
                    f"settb=1/{target.fps}[{label}]"
                )
                seg_labels.append(label)

        # セグメント間を xfade でペアワイズ連結
        seg_durations = [sum(c.duration_s for c in sc) for sc, _ in segments]
        seg_transitions = [tr for _, tr in segments[:-1]]  # all non-None

        prev_label = seg_labels[0]
        for k, tr in enumerate(seg_transitions):
            assert tr is not None
            xfade_name = _XFADE_NAMES[tr.kind]
            xfade_dur = tr.duration_s
            # offset_k = sum(seg_dur_i - td_i for i in 0..k)
            offset = sum(
                seg_durations[i] - seg_transitions[i].duration_s
                for i in range(k + 1)
            )
            offset = round(offset * target.fps) / target.fps
            out_label = base_label if k == len(seg_transitions) - 1 else f"xf{k}"
            filters.append(
                f"[{prev_label}][{seg_labels[k + 1]}]"
                f"xfade=transition={xfade_name}:duration={xfade_dur}:offset={offset:.6f}"
                f"[{out_label}]"
            )
            prev_label = out_label

    # drawtext チェーン
    if has_overlays:
        font_path = find_font()
        prev = base_label
        for i, overlay in enumerate(overlays):
            out = "vout" if i == len(overlays) - 1 else f"vd{i}"
            dt = build_drawtext_filter(overlay, font_path)
            filters.append(f"[{prev}]{dt}[{out}]")
            prev = out

    return ";".join(filters)


@dataclass(frozen=True)
class RenderPlan:
    two_stage: bool
    reason: str = field(default="")


def plan_render(project: Project, target: RenderTarget) -> RenderPlan:
    """クリップ数・filter_complex 長・xfade 有無に応じて二段階レンダを選択する。

    xfade 使用時は単一ステージで JPEG を -loop 1 で繰り返しデコードすると
    2 回目以降のデコードでタイムベースが 1/1000000 にリセットされ xfade が
    失敗するため、常に二段階レンダを選択する。
    """
    clips = project.sorted_clips()
    if len(clips) > 25:
        return RenderPlan(two_stage=True, reason="clips > 25")

    tr_by_clip_id = {t.after_clip_id: t for t in project.transitions}
    has_xfade = any(
        tr.kind != TransitionKind.CUT
        for tr in tr_by_clip_id.values()
    )
    if has_xfade:
        return RenderPlan(two_stage=True, reason="xfade transitions")

    try:
        fc = build_filter_complex(project, target)
        if len(fc) > 30000:
            return RenderPlan(two_stage=True, reason="filter_complex > 30000 chars")
    except Exception:
        pass
    return RenderPlan(two_stage=False)


def build_ffmpeg_command(
    project: Project,
    target: RenderTarget,
    output: Path,
    ffmpeg_path: str = "ffmpeg",
) -> list[str]:
    """レンダ用 FFmpeg コマンドを生成する (実行はしない)。"""
    clips = project.sorted_clips()
    if not clips:
        raise ValueError("clips が空です")

    cmd: list[str] = [ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error", "-progress", "pipe:1"]

    # 各クリップを静止画入力として追加 (ループは filter_complex 内の loop フィルタで行う)
    for clip in clips:
        cmd += [
            "-framerate", str(target.fps),
            "-i", str(Path(clip.source_path).expanduser().resolve()),
        ]

    # 無音ダミーオーディオ (Reels 仕様で AAC トラックを必須とする)
    anull_idx = len(clips)
    cmd += [
        "-f", "lavfi",
        "-i", f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_SAMPLE_RATE}",
    ]

    filter_complex = build_filter_complex(project, target)
    cmd += ["-filter_complex", filter_complex]

    gop = int(target.fps * VIDEO_GOP_SEC)
    cmd += [
        "-map", "[vout]",
        "-map", f"{anull_idx}:a",
        "-c:v", VIDEO_CODEC,
        "-profile:v", VIDEO_PROFILE,
        "-level:v", VIDEO_LEVEL,
        "-b:v", target.video_bitrate,
        "-maxrate", target.video_maxrate,
        "-bufsize", target.video_bufsize,
        "-g", str(gop),
        "-bf", str(VIDEO_MAX_B_FRAMES),
        "-pix_fmt", VIDEO_PIX_FMT,
        "-r", str(target.fps),
        "-c:a", AUDIO_CODEC,
        "-b:a", AUDIO_BITRATE,
        "-ac", str(AUDIO_CHANNELS),
        "-ar", str(AUDIO_SAMPLE_RATE),
        "-shortest",
        "-movflags", MOVFLAGS,
        str(output),
    ]
    return cmd
