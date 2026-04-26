import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useRef, useState } from "react";
import { Image as KonvaImage, Layer, Rect, Stage, Text as KonvaText } from "react-konva";
import useImage from "use-image";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
const OUTPUT_ASPECT = 9 / 16; // 出力動画の幅/高さ比 (= 9:16)
const FALLBACK_W = 270;
const FALLBACK_H = 480;
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
function OverlayText({ overlay, area, }) {
    const fontSize = Math.max(8, Math.round((overlay.font_size_px * area.h) / 1920));
    const approxCharW = fontSize * 0.65;
    const approxTextW = overlay.text.length * approxCharW;
    const approxTextH = fontSize * 1.3;
    const { dx, dy } = anchorOffset(overlay.anchor, approxTextW, approxTextH);
    return (_jsx(KonvaText, { text: overlay.text, x: area.x + overlay.x * area.w - dx, y: area.y + overlay.y * area.h - dy, fontSize: fontSize, fill: overlay.color_hex, stroke: overlay.stroke_color_hex ?? undefined, strokeWidth: overlay.stroke_width_px
            ? (overlay.stroke_width_px * area.h) / 1920
            : 0 }));
}
export function LivePreview({ onAspectChange }) {
    const clips = useProjectStore((s) => s.project.clips);
    const overlays = useProjectStore((s) => s.project.overlays);
    const selectedClipId = useProjectStore((s) => s.selectedClipId);
    const clip = useMemo(() => {
        const sorted = [...clips].sort((a, b) => a.order_index - b.order_index);
        return sorted.find((c) => c.id === selectedClipId) ?? sorted[0] ?? null;
    }, [clips, selectedClipId]);
    const [img] = useImage(clip ? api.thumbnailUrl(clip.source_path) : "", "anonymous");
    // 画像のアスペクト比を親 (PreviewPanel) に伝え、.preview-frame の枠が
    // 画像比率に合わせて伸縮するようにする。
    const imageAspect = useMemo(() => {
        if (!img || img.naturalWidth <= 0 || img.naturalHeight <= 0)
            return null;
        return img.naturalWidth / img.naturalHeight;
    }, [img]);
    useEffect(() => {
        onAspectChange?.(imageAspect);
    }, [imageAspect, onAspectChange]);
    // 親要素 (.preview-frame 内) の実サイズを観察し、Stage を埋める。
    const wrapRef = useRef(null);
    const [size, setSize] = useState({
        w: FALLBACK_W,
        h: FALLBACK_H,
    });
    useEffect(() => {
        const el = wrapRef.current;
        if (!el)
            return;
        const update = () => {
            const r = el.getBoundingClientRect();
            const w = Math.max(1, Math.floor(r.width));
            const h = Math.max(1, Math.floor(r.height));
            setSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
        };
        update();
        const ro = new ResizeObserver(update);
        ro.observe(el);
        return () => ro.disconnect();
    }, []);
    const canvasW = size.w;
    const canvasH = size.h;
    // 出力動画 (9:16) のセーフエリアを scale+pad の挙動と同じく中央に配置する。
    // crop 設定時はサーバ側 scale_pad は crop 後の画像で動作するため、
    // ここでは未設定時 (= 元画像) のセーフエリアを描画する近似実装とする。
    const safeArea = useMemo(() => {
        if (!imageAspect || canvasW <= 0 || canvasH <= 0)
            return null;
        if (imageAspect >= OUTPUT_ASPECT) {
            const safeW = canvasH * OUTPUT_ASPECT;
            return { x: (canvasW - safeW) / 2, y: 0, w: safeW, h: canvasH };
        }
        const safeH = canvasW / OUTPUT_ASPECT;
        return { x: 0, y: (canvasH - safeH) / 2, w: canvasW, h: safeH };
    }, [imageAspect, canvasW, canvasH]);
    return (_jsxs("div", { ref: wrapRef, className: "live-preview-wrap", style: { width: "100%", height: "100%" }, children: [_jsx(Stage, { width: canvasW, height: canvasH, children: _jsxs(Layer, { children: [_jsx(Rect, { x: 0, y: 0, width: canvasW, height: canvasH, fill: "#111" }), img && (_jsx(KonvaImage, { image: img, x: 0, y: 0, width: canvasW, height: canvasH })), clip?.crop && (_jsx(Rect, { x: clip.crop.x * canvasW, y: clip.crop.y * canvasH, width: clip.crop.w * canvasW, height: clip.crop.h * canvasH, stroke: "#3b82f6", strokeWidth: 2, dash: [6, 3], fill: "rgba(0,0,0,0)" })), safeArea && (_jsx(Rect, { x: safeArea.x, y: safeArea.y, width: safeArea.w, height: safeArea.h, stroke: "#888", strokeWidth: 1, dash: [2, 4], fill: "rgba(0,0,0,0)", listening: false })), safeArea && clip?.ken_burns && (_jsx(Rect, { x: safeArea.x + clip.ken_burns.start_rect.x * safeArea.w, y: safeArea.y + clip.ken_burns.start_rect.y * safeArea.h, width: clip.ken_burns.start_rect.w * safeArea.w, height: clip.ken_burns.start_rect.h * safeArea.h, stroke: "#22c55e", strokeWidth: 2, dash: [4, 4], fill: "rgba(34,197,94,0.08)" })), safeArea && clip?.ken_burns && (_jsx(Rect, { x: safeArea.x + clip.ken_burns.end_rect.x * safeArea.w, y: safeArea.y + clip.ken_burns.end_rect.y * safeArea.h, width: clip.ken_burns.end_rect.w * safeArea.w, height: clip.ken_burns.end_rect.h * safeArea.h, stroke: "#ef4444", strokeWidth: 2, dash: [4, 4], fill: "rgba(239,68,68,0.08)" })), safeArea && overlays.map((overlay) => (_jsx(OverlayText, { overlay: overlay, area: safeArea }, overlay.id)))] }) }), !clip && (_jsx("div", { className: "live-preview-empty", children: "\u30AF\u30EA\u30C3\u30D7\u3092\u8FFD\u52A0\u3057\u3066\u304F\u3060\u3055\u3044" })), clip?.ken_burns && (_jsxs("div", { className: "live-preview-legend", children: [_jsx("span", { style: { color: "#22c55e" }, children: "\u25A0" }), " \u958B\u59CB", _jsx("span", { style: { color: "#ef4444", marginLeft: 8 }, children: "\u25A0" }), " \u7D42\u4E86"] }))] }));
}
