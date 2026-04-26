import { useEffect, useMemo, useRef, useState } from "react";
import { Image as KonvaImage, Layer, Rect, Stage, Text as KonvaText } from "react-konva";
import useImage from "use-image";
import { api } from "../../api/client";
import type { TextOverlay } from "../../types/project";
import { useProjectStore } from "../../store/useProjectStore";

const OUTPUT_ASPECT = 9 / 16; // 出力動画の幅/高さ比 (= 9:16)
const FALLBACK_W = 270;
const FALLBACK_H = 480;

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

function anchorOffset(
  anchor: string,
  approxW: number,
  approxH: number,
): { dx: number; dy: number } {
  switch (anchor) {
    case "top_left":    return { dx: 0,           dy: 0 };
    case "top_center":  return { dx: approxW / 2, dy: 0 };
    case "center":      return { dx: approxW / 2, dy: approxH / 2 };
    case "bottom_center": return { dx: approxW / 2, dy: approxH };
    case "bottom_left": return { dx: 0,           dy: approxH };
    default:            return { dx: 0,           dy: 0 };
  }
}

function OverlayText({
  overlay,
  area,
}: {
  overlay: TextOverlay;
  area: Box;
}) {
  const fontSize = Math.max(8, Math.round((overlay.font_size_px * area.h) / 1920));
  const approxCharW = fontSize * 0.65;
  const approxTextW = overlay.text.length * approxCharW;
  const approxTextH = fontSize * 1.3;
  const { dx, dy } = anchorOffset(overlay.anchor, approxTextW, approxTextH);

  return (
    <KonvaText
      text={overlay.text}
      x={area.x + overlay.x * area.w - dx}
      y={area.y + overlay.y * area.h - dy}
      fontSize={fontSize}
      fill={overlay.color_hex}
      stroke={overlay.stroke_color_hex ?? undefined}
      strokeWidth={
        overlay.stroke_width_px
          ? (overlay.stroke_width_px * area.h) / 1920
          : 0
      }
    />
  );
}

interface LivePreviewProps {
  onAspectChange?: (aspect: number | null) => void;
}

export function LivePreview({ onAspectChange }: LivePreviewProps) {
  const clips = useProjectStore((s) => s.project.clips);
  const overlays = useProjectStore((s) => s.project.overlays);
  const selectedClipId = useProjectStore((s) => s.selectedClipId);

  const clip = useMemo(() => {
    const sorted = [...clips].sort((a, b) => a.order_index - b.order_index);
    return sorted.find((c) => c.id === selectedClipId) ?? sorted[0] ?? null;
  }, [clips, selectedClipId]);

  const [img] = useImage(
    clip ? api.thumbnailUrl(clip.source_path) : "",
    "anonymous",
  );

  const imageAspect = useMemo(() => {
    if (!img || img.naturalWidth <= 0 || img.naturalHeight <= 0) return null;
    return img.naturalWidth / img.naturalHeight;
  }, [img]);

  // 画像のアスペクト比を親 (PreviewPanel) に伝え、.preview-frame の枠が
  // 画像比率に追従するヒントとして使う。Stage 内では別途レターボックス
  // するため、親 CSS が効かなくても画像は歪まない。
  useEffect(() => {
    onAspectChange?.(imageAspect);
  }, [imageAspect, onAspectChange]);

  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState<{ w: number; h: number }>({
    w: FALLBACK_W,
    h: FALLBACK_H,
  });

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
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

  // Stage 内で画像をアスペクト保存して中央に配置 (object-fit:contain 相当)。
  // 親要素の比率が画像と一致しなくても、画像は決して歪まない。
  const imageBox: Box | null = useMemo(() => {
    if (!imageAspect || canvasW <= 0 || canvasH <= 0) return null;
    const stageAspect = canvasW / canvasH;
    if (imageAspect >= stageAspect) {
      // 画像が横長: 幅をフィットさせて上下にレターボックス
      const w = canvasW;
      const h = canvasW / imageAspect;
      return { x: 0, y: (canvasH - h) / 2, w, h };
    }
    // 画像が縦長: 高さをフィットさせて左右にレターボックス
    const h = canvasH;
    const w = canvasH * imageAspect;
    return { x: (canvasW - w) / 2, y: 0, w, h };
  }, [imageAspect, canvasW, canvasH]);

  // 出力動画 (9:16) のセーフエリアを scale+pad の挙動と同じく中央に配置する。
  // crop 設定時はサーバ側 scale_pad は crop 後の画像で動作するため、
  // ここでは未設定時 (= 元画像) のセーフエリアを描画する近似実装とする。
  const safeArea: Box | null = useMemo(() => {
    if (!imageBox) return null;
    const ib = imageBox;
    if (ib.w / ib.h >= OUTPUT_ASPECT) {
      const safeW = ib.h * OUTPUT_ASPECT;
      return { x: ib.x + (ib.w - safeW) / 2, y: ib.y, w: safeW, h: ib.h };
    }
    const safeH = ib.w / OUTPUT_ASPECT;
    return { x: ib.x, y: ib.y + (ib.h - safeH) / 2, w: ib.w, h: safeH };
  }, [imageBox]);

  return (
    <div
      ref={wrapRef}
      className="live-preview-wrap"
      style={{ width: "100%", height: "100%" }}
    >
      <Stage width={canvasW} height={canvasH}>
        <Layer>
          <Rect x={0} y={0} width={canvasW} height={canvasH} fill="#111" />
          {img && imageBox && (
            <KonvaImage
              image={img}
              x={imageBox.x}
              y={imageBox.y}
              width={imageBox.w}
              height={imageBox.h}
            />
          )}

          {/* トリミング矩形は元画像の正規化座標 → imageBox にマップ */}
          {imageBox && clip?.crop && (
            <Rect
              x={imageBox.x + clip.crop.x * imageBox.w}
              y={imageBox.y + clip.crop.y * imageBox.h}
              width={clip.crop.w * imageBox.w}
              height={clip.crop.h * imageBox.h}
              stroke="#3b82f6"
              strokeWidth={2}
              dash={[6, 3]}
              fill="rgba(0,0,0,0)"
            />
          )}

          {/* 9:16 セーフエリア (出力範囲) を薄く表示 */}
          {safeArea && (
            <Rect
              x={safeArea.x}
              y={safeArea.y}
              width={safeArea.w}
              height={safeArea.h}
              stroke="#888"
              strokeWidth={1}
              dash={[2, 4]}
              fill="rgba(0,0,0,0)"
              listening={false}
            />
          )}

          {/* Ken Burns 矩形は scale+pad 済み 9:16 フレーム上の正規化座標 */}
          {safeArea && clip?.ken_burns && (
            <Rect
              x={safeArea.x + clip.ken_burns.start_rect.x * safeArea.w}
              y={safeArea.y + clip.ken_burns.start_rect.y * safeArea.h}
              width={clip.ken_burns.start_rect.w * safeArea.w}
              height={clip.ken_burns.start_rect.h * safeArea.h}
              stroke="#22c55e"
              strokeWidth={2}
              dash={[4, 4]}
              fill="rgba(34,197,94,0.08)"
            />
          )}
          {safeArea && clip?.ken_burns && (
            <Rect
              x={safeArea.x + clip.ken_burns.end_rect.x * safeArea.w}
              y={safeArea.y + clip.ken_burns.end_rect.y * safeArea.h}
              width={clip.ken_burns.end_rect.w * safeArea.w}
              height={clip.ken_burns.end_rect.h * safeArea.h}
              stroke="#ef4444"
              strokeWidth={2}
              dash={[4, 4]}
              fill="rgba(239,68,68,0.08)"
            />
          )}

          {/* テキストオーバーレイは出力フレーム (9:16) 上の正規化座標 */}
          {safeArea && overlays.map((overlay) => (
            <OverlayText key={overlay.id} overlay={overlay} area={safeArea} />
          ))}
        </Layer>
      </Stage>

      {!clip && (
        <div className="live-preview-empty">
          クリップを追加してください
        </div>
      )}

      {clip?.ken_burns && (
        <div className="live-preview-legend">
          <span style={{ color: "#22c55e" }}>■</span> 開始
          <span style={{ color: "#ef4444", marginLeft: 8 }}>■</span> 終了
        </div>
      )}
    </div>
  );
}
