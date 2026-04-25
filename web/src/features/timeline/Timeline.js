import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
import { TransitionPicker } from "../transitions/TransitionPicker";
export function Timeline() {
    const clips = useProjectStore((s) => [...s.project.clips].sort((a, b) => a.order_index - b.order_index));
    const transitions = useProjectStore((s) => s.project.transitions);
    const selectedId = useProjectStore((s) => s.selectedClipId);
    const selectClip = useProjectStore((s) => s.selectClip);
    const moveClip = useProjectStore((s) => s.moveClip);
    const removeClip = useProjectStore((s) => s.removeClip);
    const trByClipId = Object.fromEntries(transitions.map((t) => [t.after_clip_id, t]));
    if (clips.length === 0) {
        return (_jsx("div", { className: "timeline", children: _jsx("div", { className: "empty", children: "\u30E9\u30A4\u30D6\u30E9\u30EA\u304B\u3089\u30AF\u30EA\u30C3\u30D7\u3092\u8FFD\u52A0\u3057\u3066\u304F\u3060\u3055\u3044" }) }));
    }
    return (_jsx("div", { className: "timeline", children: _jsx("div", { className: "timeline-row", children: clips.map((c, i) => (_jsxs("div", { className: "clip-with-transition", children: [_jsxs("div", { className: `clip-card ${selectedId === c.id ? "selected" : ""}`, onClick: () => selectClip(c.id), children: [_jsx("img", { src: api.thumbnailUrl(c.source_path), alt: "", loading: "lazy" }), _jsxs("div", { className: "meta", children: [_jsxs("span", { children: [c.duration_s.toFixed(2), "s"] }), _jsxs("span", { children: [_jsx("button", { type: "button", onClick: (e) => {
                                                    e.stopPropagation();
                                                    moveClip(c.id, -1);
                                                }, title: "\u524D\u3078", style: { padding: "1px 4px", fontSize: 10 }, children: "\u25C0" }), _jsx("button", { type: "button", onClick: (e) => {
                                                    e.stopPropagation();
                                                    moveClip(c.id, 1);
                                                }, title: "\u5F8C\u308D\u3078", style: { padding: "1px 4px", fontSize: 10, marginLeft: 2 }, children: "\u25B6" }), _jsx("button", { type: "button", onClick: (e) => {
                                                    e.stopPropagation();
                                                    removeClip(c.id);
                                                }, title: "\u524A\u9664", style: { padding: "1px 4px", fontSize: 10, marginLeft: 2 }, children: "\u2715" })] })] })] }), i < clips.length - 1 && (_jsx(TransitionPicker, { afterClipId: c.id, transition: trByClipId[c.id] }))] }, c.id))) }) }));
}
