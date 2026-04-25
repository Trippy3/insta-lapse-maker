import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useProjectStore } from "../../store/useProjectStore";
const ANCHOR_LABELS = {
    top_left: "左上",
    top_center: "上中",
    center: "中央",
    bottom_center: "下中",
    bottom_left: "左下",
};
function OverlayRow({ overlay }) {
    const updateOverlay = useProjectStore((s) => s.updateOverlay);
    const removeOverlay = useProjectStore((s) => s.removeOverlay);
    const set = (key, value) => updateOverlay(overlay.id, { [key]: value });
    return (_jsxs("div", { className: "overlay-row", children: [_jsxs("div", { className: "overlay-row-header", children: [_jsx("input", { className: "overlay-text-input", value: overlay.text, onChange: (e) => set("text", e.target.value), placeholder: "\u30C6\u30AD\u30B9\u30C8" }), _jsx("button", { className: "icon-btn", onClick: () => removeOverlay(overlay.id), title: "\u524A\u9664", children: "\u2715" })] }), _jsxs("div", { className: "overlay-grid", children: [_jsx("label", { children: "\u30B5\u30A4\u30BA" }), _jsx("input", { type: "number", min: 8, max: 400, value: overlay.font_size_px, onChange: (e) => set("font_size_px", Number(e.target.value)) }), _jsx("label", { children: "\u8272" }), _jsx("input", { type: "color", value: overlay.color_hex, onChange: (e) => set("color_hex", e.target.value.toUpperCase()) }), _jsx("label", { children: "\u7E01\u53D6\u308A" }), _jsxs("div", { style: { display: "flex", gap: 4, alignItems: "center" }, children: [_jsx("input", { type: "color", value: overlay.stroke_color_hex ?? "#000000", onChange: (e) => set("stroke_color_hex", e.target.value.toUpperCase()) }), _jsx("input", { type: "number", min: 0, max: 20, value: overlay.stroke_width_px, onChange: (e) => set("stroke_width_px", Number(e.target.value)), style: { width: 48 } }), "px"] }), _jsx("label", { children: "\u4F4D\u7F6E" }), _jsx("select", { value: overlay.anchor, onChange: (e) => set("anchor", e.target.value), children: Object.keys(ANCHOR_LABELS).map((a) => (_jsx("option", { value: a, children: ANCHOR_LABELS[a] }, a))) }), _jsx("label", { children: "X" }), _jsx("input", { type: "range", min: 0, max: 1, step: 0.01, value: overlay.x, onChange: (e) => set("x", Number(e.target.value)) }), _jsx("label", { children: "Y" }), _jsx("input", { type: "range", min: 0, max: 1, step: 0.01, value: overlay.y, onChange: (e) => set("y", Number(e.target.value)) }), _jsx("label", { children: "\u958B\u59CB(s)" }), _jsx("input", { type: "number", min: 0, step: 0.1, value: overlay.start_s, onChange: (e) => set("start_s", Number(e.target.value)) }), _jsx("label", { children: "\u7D42\u4E86(s)" }), _jsx("input", { type: "number", min: 0.1, step: 0.1, value: overlay.end_s, onChange: (e) => set("end_s", Number(e.target.value)) }), _jsx("label", { children: "FI(s)" }), _jsx("input", { type: "number", min: 0, max: 5, step: 0.1, value: overlay.fade_in_s, onChange: (e) => set("fade_in_s", Number(e.target.value)), title: "\u30D5\u30A7\u30FC\u30C9\u30A4\u30F3\u79D2\u6570" }), _jsx("label", { children: "FO(s)" }), _jsx("input", { type: "number", min: 0, max: 5, step: 0.1, value: overlay.fade_out_s, onChange: (e) => set("fade_out_s", Number(e.target.value)), title: "\u30D5\u30A7\u30FC\u30C9\u30A2\u30A6\u30C8\u79D2\u6570" })] })] }));
}
export function OverlayEditor() {
    const overlays = useProjectStore((s) => s.project.overlays);
    const addOverlay = useProjectStore((s) => s.addOverlay);
    return (_jsxs("div", { className: "overlay-editor", children: [_jsxs("div", { className: "overlay-editor-header", children: [_jsx("span", { style: { fontWeight: 600, fontSize: 13 }, children: "\u30C6\u30AD\u30B9\u30C8" }), _jsx("button", { className: "btn-sm", onClick: addOverlay, children: "+ \u8FFD\u52A0" })] }), overlays.length === 0 && (_jsx("p", { style: { fontSize: 12, color: "var(--text-dim)", margin: "8px 0" }, children: "\u30AA\u30FC\u30D0\u30FC\u30EC\u30A4\u306A\u3057" })), overlays.map((ov) => (_jsx(OverlayRow, { overlay: ov }, ov.id)))] }));
}
