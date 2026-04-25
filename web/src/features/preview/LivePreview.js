import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo } from "react";
import { Image as KonvaImage, Layer, Rect, Stage, Text as KonvaText } from "react-konva";
import useImage from "use-image";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
const CANVAS_W = 270;
const CANVAS_H = 480;
function anchorOffset(anchor, approxW, approxH) {
    switch (anchor) {
        case "top_left": return { dx: 0, dy: 0 };
        case "top_center": return { dx: approxW / 2, dy: 0 };
        case "center": return { dx: approxW / 2, dy: approxH / 2 };
        case "bottom_center": return { dx: approxW / 2, dy: approxH };
        case "bottom_left": return { dx: 0, dy: approxH };
        default: return { dx: 0, dy: 0 };
    }
}
function OverlayText({ overlay }) {
    const fontSize = Math.max(8, Math.round((overlay.font_size_px * CANVAS_H) / 1920));
    const approxCharW = fontSize * 0.65;
    const approxTextW = overlay.text.length * approxCharW;
    const approxTextH = fontSize * 1.3;
    const { dx, dy } = anchorOffset(overlay.anchor, approxTextW, approxTextH);
    return (_jsx(KonvaText, { text: overlay.text, x: overlay.x * CANVAS_W - dx, y: overlay.y * CANVAS_H - dy, fontSize: fontSize, fill: overlay.color_hex, stroke: overlay.stroke_color_hex ?? undefined, strokeWidth: overlay.stroke_width_px
            ? (overlay.stroke_width_px * CANVAS_H) / 1920
            : 0 }));
}
function ClipLayer({ sourcePath }) {
    const [img] = useImage(api.thumbnailUrl(sourcePath), "anonymous");
    if (!img)
        return null;
    const scaleX = CANVAS_W / img.naturalWidth;
    const scaleY = CANVAS_H / img.naturalHeight;
    const scale = Math.max(scaleX, scaleY);
    const drawW = img.naturalWidth * scale;
    const drawH = img.naturalHeight * scale;
    const offX = (CANVAS_W - drawW) / 2;
    const offY = (CANVAS_H - drawH) / 2;
    return (_jsx(KonvaImage, { image: img, x: offX, y: offY, width: drawW, height: drawH }));
}
export function LivePreview() {
    const clips = useProjectStore((s) => s.project.clips);
    const overlays = useProjectStore((s) => s.project.overlays);
    const selectedClipId = useProjectStore((s) => s.selectedClipId);
    const clip = useMemo(() => {
        const sorted = [...clips].sort((a, b) => a.order_index - b.order_index);
        return sorted.find((c) => c.id === selectedClipId) ?? sorted[0] ?? null;
    }, [clips, selectedClipId]);
    return (_jsxs("div", { className: "live-preview-wrap", children: [_jsx(Stage, { width: CANVAS_W, height: CANVAS_H, children: _jsxs(Layer, { children: [_jsx(Rect, { x: 0, y: 0, width: CANVAS_W, height: CANVAS_H, fill: "#111" }), clip && _jsx(ClipLayer, { sourcePath: clip.source_path }), clip?.crop && (_jsx(Rect, { x: clip.crop.x * CANVAS_W, y: clip.crop.y * CANVAS_H, width: clip.crop.w * CANVAS_W, height: clip.crop.h * CANVAS_H, stroke: "#3b82f6", strokeWidth: 2, dash: [6, 3], fill: "rgba(0,0,0,0)" })), clip?.ken_burns && (_jsx(Rect, { x: clip.ken_burns.start_rect.x * CANVAS_W, y: clip.ken_burns.start_rect.y * CANVAS_H, width: clip.ken_burns.start_rect.w * CANVAS_W, height: clip.ken_burns.start_rect.h * CANVAS_H, stroke: "#22c55e", strokeWidth: 2, dash: [4, 4], fill: "rgba(34,197,94,0.08)" })), clip?.ken_burns && (_jsx(Rect, { x: clip.ken_burns.end_rect.x * CANVAS_W, y: clip.ken_burns.end_rect.y * CANVAS_H, width: clip.ken_burns.end_rect.w * CANVAS_W, height: clip.ken_burns.end_rect.h * CANVAS_H, stroke: "#ef4444", strokeWidth: 2, dash: [4, 4], fill: "rgba(239,68,68,0.08)" })), overlays.map((overlay) => (_jsx(OverlayText, { overlay: overlay }, overlay.id)))] }) }), !clip && (_jsx("div", { className: "live-preview-empty", children: "\u30AF\u30EA\u30C3\u30D7\u3092\u8FFD\u52A0\u3057\u3066\u304F\u3060\u3055\u3044" })), clip?.ken_burns && (_jsxs("div", { className: "live-preview-legend", children: [_jsx("span", { style: { color: "#22c55e" }, children: "\u25A0" }), " \u958B\u59CB", _jsx("span", { style: { color: "#ef4444", marginLeft: 8 }, children: "\u25A0" }), " \u7D42\u4E86"] }))] }));
}
