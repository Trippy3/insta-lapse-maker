import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo, useRef, useState } from "react";
import { Cropper } from "react-advanced-cropper";
import "react-advanced-cropper/dist/style.css";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
export function CropEditor({ clip }) {
    const setCrop = useProjectStore((s) => s.setClipCrop);
    const cropperRef = useRef(null);
    const [natural, setNatural] = useState(null);
    const imageUrl = useMemo(() => api.thumbnailUrl(clip.source_path), [clip.source_path]);
    const defaultCoordinates = useMemo(() => {
        if (!natural || !clip.crop)
            return undefined;
        return {
            left: clip.crop.x * natural.w,
            top: clip.crop.y * natural.h,
            width: clip.crop.w * natural.w,
            height: clip.crop.h * natural.h,
        };
    }, [natural, clip.crop]);
    const handleChange = (cropper) => {
        const state = cropper.getState();
        const coords = cropper.getCoordinates();
        if (!state || !coords || !state.imageSize)
            return;
        const imgW = state.imageSize.width;
        const imgH = state.imageSize.height;
        if (imgW <= 0 || imgH <= 0)
            return;
        if (!natural)
            setNatural({ w: imgW, h: imgH });
        const next = {
            x: clamp01(coords.left / imgW),
            y: clamp01(coords.top / imgH),
            w: clamp01(coords.width / imgW),
            h: clamp01(coords.height / imgH),
        };
        adjustToBounds(next);
        if (!isSameRect(clip.crop, next)) {
            setCrop(clip.id, next);
        }
    };
    const handleReset = () => {
        setCrop(clip.id, null);
    };
    return (_jsxs("div", { className: "crop-editor", children: [_jsx("div", { className: "row", style: { justifyContent: "flex-end" }, children: _jsx("button", { onClick: handleReset, disabled: !clip.crop, children: "\u30AF\u30ED\u30C3\u30D7\u89E3\u9664" }) }), _jsx("div", { className: "crop-stage", children: _jsx(Cropper, { ref: cropperRef, src: imageUrl, className: "crop-canvas", stencilProps: { grid: true }, defaultCoordinates: defaultCoordinates, onChange: handleChange }, clip.id) }), clip.crop ? (_jsx("div", { style: { fontSize: 10, color: "var(--text-dim)" }, children: `x:${clip.crop.x.toFixed(3)} y:${clip.crop.y.toFixed(3)} w:${clip.crop.w.toFixed(3)} h:${clip.crop.h.toFixed(3)}` })) : (_jsx("div", { style: { fontSize: 10, color: "var(--text-dim)" }, children: "\u30AF\u30ED\u30C3\u30D7\u672A\u8A2D\u5B9A (\u9ED2\u5E2F\u306E\u307F)" }))] }));
}
function clamp01(v) {
    if (!Number.isFinite(v))
        return 0;
    if (v < 0)
        return 0;
    if (v > 1)
        return 1;
    return v;
}
function adjustToBounds(r) {
    if (r.x + r.w > 1)
        r.w = Math.max(1e-4, 1 - r.x);
    if (r.y + r.h > 1)
        r.h = Math.max(1e-4, 1 - r.y);
    if (r.w <= 0)
        r.w = 1e-4;
    if (r.h <= 0)
        r.h = 1e-4;
}
function isSameRect(a, b) {
    if (!a)
        return false;
    const eps = 1e-4;
    return (Math.abs(a.x - b.x) < eps &&
        Math.abs(a.y - b.y) < eps &&
        Math.abs(a.w - b.w) < eps &&
        Math.abs(a.h - b.h) < eps);
}
