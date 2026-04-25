import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { useProjectStore } from "../../store/useProjectStore";
const KINDS = [
    { kind: "cut", label: "カット" },
    { kind: "fade", label: "フェード" },
    { kind: "crossfade", label: "クロス" },
    { kind: "wipe_left", label: "←ワイプ" },
    { kind: "wipe_right", label: "→ワイプ" },
    { kind: "slide_up", label: "↑スライド" },
];
const DEFAULT_DURATION = 0.5;
export function TransitionPicker({ afterClipId, transition }) {
    const setTransition = useProjectStore((s) => s.setTransition);
    const removeTransition = useProjectStore((s) => s.removeTransition);
    const [open, setOpen] = useState(false);
    const currentKind = transition?.kind ?? "cut";
    const currentDur = transition?.duration_s ?? 0;
    function select(kind) {
        if (kind === "cut") {
            removeTransition(afterClipId);
        }
        else {
            setTransition(afterClipId, kind, transition?.duration_s ?? DEFAULT_DURATION);
        }
        setOpen(false);
    }
    function changeDuration(e) {
        const val = parseFloat(e.target.value);
        if (!isNaN(val) && val > 0 && currentKind !== "cut") {
            setTransition(afterClipId, currentKind, val);
        }
    }
    const label = KINDS.find((k) => k.kind === currentKind)?.label ?? currentKind;
    return (_jsxs("div", { className: "transition-picker", children: [_jsx("button", { type: "button", className: `tr-btn ${currentKind !== "cut" ? "tr-active" : ""}`, onClick: () => setOpen((v) => !v), title: `トランジション: ${label}`, children: currentKind === "cut" ? "┊" : "↔" }), open && (_jsxs("div", { className: "tr-popup", children: [_jsx("div", { className: "tr-kinds", children: KINDS.map(({ kind, label: lbl }) => (_jsx("button", { type: "button", className: `tr-kind-btn ${currentKind === kind ? "active" : ""}`, onClick: () => select(kind), children: lbl }, kind))) }), currentKind !== "cut" && (_jsxs("label", { className: "tr-dur-row", children: [_jsx("span", { children: "\u79D2" }), _jsx("input", { type: "number", min: 0.1, max: 3.0, step: 0.1, value: currentDur, onChange: changeDuration })] }))] }))] }));
}
