"""画像リストから雛形 Project を生成するヘルパ。"""

from __future__ import annotations

from pathlib import Path

from timelapse_web.models.project import (
    Clip,
    Project,
    Transition,
    TransitionKind,
)


def scaffold_project(
    image_paths: list[Path],
    default_duration_s: float = 0.5,
    default_transition: TransitionKind = TransitionKind.CUT,
    transition_duration_s: float = 0.0,
    name: str = "Untitled",
) -> Project:
    """
    画像パスリストから雛形 Project を生成する。

    ID 採番・order_index の整列・Transition の after_clip_id 紐付けを確実に処理する。
    カメラワーク（Ken Burns）やクロップは含まない。AI が後から JSON を編集して追加する。
    """
    clips: list[Clip] = []
    for i, path in enumerate(image_paths):
        clips.append(
            Clip(
                source_path=str(path.expanduser().resolve()),
                order_index=i,
                duration_s=default_duration_s,
            )
        )

    transitions: list[Transition] = []
    use_transition = (
        default_transition != TransitionKind.CUT
        and transition_duration_s > 0.0
    )
    if use_transition:
        for clip in clips[:-1]:
            transitions.append(
                Transition(
                    after_clip_id=clip.id,
                    kind=default_transition,
                    duration_s=transition_duration_s,
                )
            )

    return Project(name=name, clips=clips, transitions=transitions)
