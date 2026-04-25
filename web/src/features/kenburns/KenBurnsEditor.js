import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useEffect, useMemo, useRef, useState } from "react";
import { Image as KonvaImage, Layer, Rect, Stage, Transformer } from "react-konva";
import useImage from "use-image";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
// 編集ステージの描画サイズ (9:16)。CSS 側では横 100% に拡縮する。
const STAGE_W = 240;
const STAGE_H = (STAGE_W * 16) / 9; // 426.67
const DEFAULT_START = { x: 0.0, y: 0.0, w: 1.0, h: 1.0 };
const DEFAULT_END = { x: 0.15, y: 0.15, w: 0.7, h: 0.7 };
export function KenBurnsEditor({ clip }) {
    const setKenBurns = useProjectStore((s) => s.setClipKenBurns);
    const [selected, setSelected] = useState("end");
    const [image] = useImage(api.thumbnailUrl(clip.source_path), "anonymous");
    const kb = clip.ken_burns;
    const startRect = kb?.start_rect ?? DEFAULT_START;
    const endRect = kb?.end_rect ?? DEFAULT_END;
    const easing = kb?.easing ?? "linear";
    const enable = () => {
        if (!clip.ken_burns) {
            setKenBurns(clip.id, {
                start_rect: DEFAULT_START,
                end_rect: DEFAULT_END,
                easing: "linear",
            });
        }
    };
    const disable = () => setKenBurns(clip.id, null);
    const update = (patch) => {
        const next = {
            start_rect: startRect,
            end_rect: endRect,
            easing,
            ...patch,
        };
        setKenBurns(clip.id, next);
    };
    // 画像を stage 内に contain フィットで表示するための算出
    const imagePlacement = useMemo(() => {
        if (!image)
            return null;
        const iw = image.naturalWidth;
        const ih = image.naturalHeight;
        if (iw <= 0 || ih <= 0)
            return null;
        const scale = Math.min(STAGE_W / iw, STAGE_H / ih);
        const w = iw * scale;
        const h = ih * scale;
        return { x: (STAGE_W - w) / 2, y: (STAGE_H - h) / 2, w, h };
    }, [image]);
    return (_jsxs("div", { className: "kb-editor", children: [_jsxs("div", { className: "row", style: { justifyContent: "space-between" }, children: [_jsx("div", { className: "row", children: !kb ? (_jsx("button", { className: "primary", onClick: enable, children: "\u30AB\u30E1\u30E9\u30EF\u30FC\u30AF\u3092\u6709\u52B9\u5316" })) : (_jsxs(_Fragment, { children: [_jsx("label", { style: { fontSize: 11, color: "var(--text-dim)" }, children: "\u30A4\u30FC\u30B8\u30F3\u30B0" }), _jsxs("select", { value: easing, onChange: (e) => update({ easing: e.target.value }), children: [_jsx("option", { value: "linear", children: "linear" }), _jsx("option", { value: "ease_in_out", children: "ease_in_out" })] })] })) }), kb && (_jsx("button", { onClick: disable, children: "\u30AB\u30E1\u30E9\u30EF\u30FC\u30AF\u89E3\u9664" }))] }), kb && (_jsxs(_Fragment, { children: [_jsxs("div", { className: "kb-legend", children: [_jsx("span", { className: "kb-dot kb-dot-start" }), " \u958B\u59CB", _jsx("span", { className: "kb-dot kb-dot-end" }), " \u7D42\u4E86", _jsx("span", { style: { marginLeft: "auto", color: "var(--text-dim)" }, children: "\u77E9\u5F62\u30AF\u30EA\u30C3\u30AF\u3067\u9078\u629E \u2192 \u672C\u4F53\u30C9\u30E9\u30C3\u30B0\u3067\u79FB\u52D5 / \u56DB\u9685\u3067\u62E1\u7E2E" })] }), _jsx("div", { className: "kb-stage-wrap", children: _jsx(Stage, { width: STAGE_W, height: STAGE_H, onMouseDown: (e) => {
                                // 背景クリックで選択解除
                                if (e.target === e.target.getStage())
                                    setSelected(null);
                            }, children: _jsxs(Layer, { children: [imagePlacement && image && (_jsx(KonvaImage, { image: image, x: imagePlacement.x, y: imagePlacement.y, width: imagePlacement.w, height: imagePlacement.h, listening: false })), _jsx(DraggableRect, { rect: startRect, color: "#ff6a6a", selected: selected === "start", onSelect: () => setSelected("start"), onChange: (r) => update({ start_rect: r }) }), _jsx(DraggableRect, { rect: endRect, color: "#4f8cff", selected: selected === "end", onSelect: () => setSelected("end"), onChange: (r) => update({ end_rect: r }) })] }) }) }), _jsxs("div", { className: "kb-info", children: [_jsxs("div", { children: ["\u958B\u59CB: x=", startRect.x.toFixed(2), " y=", startRect.y.toFixed(2), " size=", startRect.w.toFixed(2)] }), _jsxs("div", { children: ["\u7D42\u4E86: x=", endRect.x.toFixed(2), " y=", endRect.y.toFixed(2), " size=", endRect.w.toFixed(2)] })] })] }))] }));
}
function DraggableRect({ rect, color, selected, onSelect, onChange, }) {
    const rectRef = useRef(null);
    const trRef = useRef(null);
    useEffect(() => {
        if (selected && trRef.current && rectRef.current) {
            trRef.current.nodes([rectRef.current]);
            trRef.current.getLayer()?.batchDraw();
        }
        else if (trRef.current) {
            trRef.current.nodes([]);
        }
    }, [selected]);
    // 画面上のピクセル矩形: stage は 9:16 なので w*STAGE_W:h*STAGE_H = 9:16 (w==h なら)
    const px = rect.x * STAGE_W;
    const py = rect.y * STAGE_H;
    const pw = rect.w * STAGE_W;
    const ph = rect.h * STAGE_H;
    return (_jsxs(_Fragment, { children: [_jsx(Rect, { ref: rectRef, x: px, y: py, width: pw, height: ph, stroke: color, strokeWidth: selected ? 3 : 2, fill: color, opacity: selected ? 0.22 : 0.12, draggable: selected, onMouseDown: onSelect, onTap: onSelect, onDragEnd: (e) => {
                    const node = e.target;
                    const nx = clamp01(node.x() / STAGE_W);
                    const ny = clamp01(node.y() / STAGE_H);
                    // ドラッグで矩形サイズは変わらない
                    const adj = clampRectToBounds({ x: nx, y: ny, w: rect.w, h: rect.h });
                    onChange(adj);
                }, onTransformEnd: () => {
                    const node = rectRef.current;
                    if (!node)
                        return;
                    const scaleX = node.scaleX();
                    const scaleY = node.scaleY();
                    node.scaleX(1);
                    node.scaleY(1);
                    const newPw = Math.max(1, node.width() * scaleX);
                    const newPh = Math.max(1, node.height() * scaleY);
                    // 正規化座標で w == h にするため、見かけの w (pixel) を 9/16 * 見かけの h に揃える
                    // (= stage aspect と一致)
                    const aspectedPw = (newPh * 9) / 16;
                    const finalPw = (newPw + aspectedPw) / 2; // 微妙にずれた時の中間値
                    const finalPh = (finalPw * 16) / 9;
                    const nextW = clamp01(finalPw / STAGE_W);
                    const nextH = clamp01(finalPh / STAGE_H);
                    const nextX = clamp01(node.x() / STAGE_W);
                    const nextY = clamp01(node.y() / STAGE_H);
                    // 小さすぎると FFmpeg zoom が無限大になるので下限
                    const minSize = 0.1;
                    const adj = clampRectToBounds({
                        x: nextX,
                        y: nextY,
                        w: Math.max(minSize, nextW),
                        h: Math.max(minSize, nextH),
                    });
                    onChange(adj);
                } }), selected && (_jsx(Transformer, { ref: trRef, keepRatio: true, rotateEnabled: false, enabledAnchors: [
                    "top-left",
                    "top-right",
                    "bottom-left",
                    "bottom-right",
                ], boundBoxFunc: (_oldBox, newBox) => {
                    // 最小サイズ
                    if (newBox.width < 20 || newBox.height < 35)
                        return _oldBox;
                    return newBox;
                } }))] }));
}
function clamp01(v) {
    if (!Number.isFinite(v))
        return 0;
    return Math.max(0, Math.min(1, v));
}
function clampRectToBounds(r) {
    // w, h は [0.1, 1.0] 内、x+w / y+h は 1 以下に収める
    const w = Math.min(1, Math.max(0.1, r.w));
    const h = Math.min(1, Math.max(0.1, r.h));
    const x = Math.min(1 - w, Math.max(0, r.x));
    const y = Math.min(1 - h, Math.max(0, r.y));
    return { x, y, w, h };
}
