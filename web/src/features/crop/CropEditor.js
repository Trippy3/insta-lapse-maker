import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useRef, useState } from "react";
import { Cropper } from "react-advanced-cropper";
import "react-advanced-cropper/dist/style.css";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
const ASPECT_OPTIONS = [
    { value: "1:1", label: "1:1 (正方)", ratio: 1 },
    { value: "9:16", label: "9:16 (縦長)", ratio: 9 / 16 },
];
export function CropEditor({ clip }) {
    const setCrop = useProjectStore((s) => s.setClipCrop);
    const [aspect, setAspect] = useState(clip.crop?.aspect ?? "9:16");
    const cropperRef = useRef(null);
    const [natural, setNatural] = useState(null);
    // クリップ切替時に aspect を再同期
    useEffect(() => {
        setAspect(clip.crop?.aspect ?? "9:16");
    }, [clip.id, clip.crop?.aspect]);
    const imageUrl = useMemo(() => api.thumbnailUrl(clip.source_path), [clip.source_path]);
    const ratio = ASPECT_OPTIONS.find((a) => a.value === aspect)?.ratio ?? 9 / 16;
    const defaultCoordinates = useMemo(() => {
        if (!natural || !clip.crop)
            return undefined;
        // natural は「サムネイル解像度」。crop は「原画像に対する正規化座標 (0..1)」。
        // 正規化座標 * natural で stencil の既定位置を算出する。
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
            aspect,
            x: clamp01(coords.left / imgW),
            y: clamp01(coords.top / imgH),
            w: clamp01(coords.width / imgW),
            h: clamp01(coords.height / imgH),
        };
        // 境界超過は CropRect バリデータで弾かれるため調整して保存
        adjustToBounds(next);
        if (!isSameRect(clip.crop, next)) {
            setCrop(clip.id, next);
        }
    };
    const handleReset = () => {
        setCrop(clip.id, null);
    };
    return (_jsxs("div", { className: "crop-editor", children: [_jsxs("div", { className: "row", style: { justifyContent: "space-between" }, children: [_jsx("div", { className: "row", children: ASPECT_OPTIONS.map((opt) => (_jsx("button", { className: aspect === opt.value ? "primary" : "", onClick: () => setAspect(opt.value), children: opt.label }, opt.value))) }), _jsx("button", { onClick: handleReset, disabled: !clip.crop, children: "\u30AF\u30ED\u30C3\u30D7\u89E3\u9664" })] }), _jsx("div", { className: "crop-stage", children: _jsx(Cropper, { ref: cropperRef, src: imageUrl, className: "crop-canvas", stencilProps: {
                        aspectRatio: ratio,
                        grid: true,
                    }, defaultCoordinates: defaultCoordinates, onChange: handleChange }, `${clip.id}-${aspect}`) }), clip.crop ? (_jsx("div", { style: { fontSize: 10, color: "var(--text-dim)" }, children: `${clip.crop.aspect} | x:${clip.crop.x.toFixed(3)} y:${clip.crop.y.toFixed(3)} w:${clip.crop.w.toFixed(3)} h:${clip.crop.h.toFixed(3)}` })) : (_jsx("div", { style: { fontSize: 10, color: "var(--text-dim)" }, children: "\u30AF\u30ED\u30C3\u30D7\u672A\u8A2D\u5B9A (\u9ED2\u5E2F\u306E\u307F)" }))] }));
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
    return (a.aspect === b.aspect &&
        Math.abs(a.x - b.x) < eps &&
        Math.abs(a.y - b.y) < eps &&
        Math.abs(a.w - b.w) < eps &&
        Math.abs(a.h - b.h) < eps);
}
