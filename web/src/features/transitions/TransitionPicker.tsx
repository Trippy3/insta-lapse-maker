import { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
import type { Transition, TransitionKind } from "../../types/project";

interface Props {
  afterClipId: string;
  transition: Transition | undefined;
}

const KINDS: { kind: TransitionKind; label: string }[] = [
  { kind: "cut", label: "カット" },
  { kind: "fade", label: "フェード" },
  { kind: "crossfade", label: "クロス" },
  { kind: "wipe_left", label: "←ワイプ" },
  { kind: "wipe_right", label: "→ワイプ" },
  { kind: "slide_up", label: "↑スライド" },
];

const DEFAULT_DURATION = 0.5;

export function TransitionPicker({ afterClipId, transition }: Props) {
  const setTransition = useProjectStore((s) => s.setTransition);
  const removeTransition = useProjectStore((s) => s.removeTransition);
  const [open, setOpen] = useState(false);

  const currentKind: TransitionKind = transition?.kind ?? "cut";
  const currentDur = transition?.duration_s ?? 0;

  function select(kind: TransitionKind) {
    if (kind === "cut") {
      removeTransition(afterClipId);
    } else {
      setTransition(afterClipId, kind, transition?.duration_s ?? DEFAULT_DURATION);
    }
    setOpen(false);
  }

  function changeDuration(e: React.ChangeEvent<HTMLInputElement>) {
    const val = parseFloat(e.target.value);
    if (!isNaN(val) && val > 0 && currentKind !== "cut") {
      setTransition(afterClipId, currentKind, val);
    }
  }

  const label = KINDS.find((k) => k.kind === currentKind)?.label ?? currentKind;

  return (
    <div className="transition-picker">
      <button
        type="button"
        className={`tr-btn ${currentKind !== "cut" ? "tr-active" : ""}`}
        onClick={() => setOpen((v) => !v)}
        title={`トランジション: ${label}`}
      >
        {currentKind === "cut" ? "┊" : "↔"}
      </button>
      {open && (
        <div className="tr-popup">
          <div className="tr-kinds">
            {KINDS.map(({ kind, label: lbl }) => (
              <button
                key={kind}
                type="button"
                className={`tr-kind-btn ${currentKind === kind ? "active" : ""}`}
                onClick={() => select(kind)}
              >
                {lbl}
              </button>
            ))}
          </div>
          {currentKind !== "cut" && (
            <label className="tr-dur-row">
              <span>秒</span>
              <input
                type="number"
                min={0.1}
                max={3.0}
                step={0.1}
                value={currentDur}
                onChange={changeDuration}
              />
            </label>
          )}
        </div>
      )}
    </div>
  );
}
