import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { CropEditor } from "../crop/CropEditor";
import { KenBurnsEditor } from "../kenburns/KenBurnsEditor";
import { useProjectStore } from "../../store/useProjectStore";
export function ClipInspector() {
    const selectedId = useProjectStore((s) => s.selectedClipId);
    const clip = useProjectStore((s) => s.project.clips.find((c) => c.id === selectedId));
    const updateDuration = useProjectStore((s) => s.updateClipDuration);
    const [cropOpen, setCropOpen] = useState(true);
    const [kbOpen, setKbOpen] = useState(false);
    if (!clip) {
        return _jsx("div", { className: "empty", children: "\u30AF\u30EA\u30C3\u30D7\u3092\u9078\u629E\u3057\u3066\u304F\u3060\u3055\u3044" });
    }
    return (_jsxs("div", { className: "col", children: [_jsxs("div", { className: "clip-controls", children: [_jsx("label", { children: "\u30D5\u30A1\u30A4\u30EB" }), _jsx("span", { style: { fontSize: 11, color: "var(--text-dim)", wordBreak: "break-all" }, title: clip.source_path, children: clip.source_path.split("/").pop() }), _jsx("label", { children: "\u5C3A (\u79D2)" }), _jsx("input", { type: "number", min: 0.1, max: 10, step: 0.1, value: clip.duration_s, onChange: (e) => {
                            const v = Number.parseFloat(e.target.value);
                            if (Number.isFinite(v) && v > 0)
                                updateDuration(clip.id, v);
                        } })] }), _jsxs("div", { style: { marginTop: 8 }, children: [_jsxs("button", { style: { width: "100%" }, onClick: () => setCropOpen((o) => !o), children: [cropOpen ? "▼" : "▶", " \u30C8\u30EA\u30DF\u30F3\u30B0 ", clip.crop ? "(設定済み)" : "(未設定)"] }), cropOpen && _jsx(CropEditor, { clip: clip })] }), _jsxs("div", { style: { marginTop: 8 }, children: [_jsxs("button", { style: { width: "100%" }, onClick: () => setKbOpen((o) => !o), children: [kbOpen ? "▼" : "▶", " Ken Burns ", clip.ken_burns ? `(${clip.ken_burns.easing})` : "(未設定)"] }), kbOpen && _jsx(KenBurnsEditor, { clip: clip })] })] }));
}
