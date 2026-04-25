import { useEffect, useMemo, useRef, useState } from "react";
import type Konva from "konva";
import { Image as KonvaImage, Layer, Rect, Stage, Transformer } from "react-konva";
import useImage from "use-image";

import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
import type { Clip, KenBurns, KenBurnsEasing, Rect01 } from "../../types/project";

// 編集ステージの描画サイズ (9:16)。CSS 側では横 100% に拡縮する。
const STAGE_W = 240;
const STAGE_H = (STAGE_W * 16) / 9; // 426.67

const DEFAULT_START: Rect01 = { x: 0.0, y: 0.0, w: 1.0, h: 1.0 };
const DEFAULT_END: Rect01 = { x: 0.15, y: 0.15, w: 0.7, h: 0.7 };

type SelectedKind = "start" | "end" | null;

interface KenBurnsEditorProps {
  clip: Clip;
}

export function KenBurnsEditor({ clip }: KenBurnsEditorProps) {
  const setKenBurns = useProjectStore((s) => s.setClipKenBurns);
  const [selected, setSelected] = useState<SelectedKind>("end");
  const [image] = useImage(api.thumbnailUrl(clip.source_path), "anonymous");

  const kb = clip.ken_burns;

  const startRect = kb?.start_rect ?? DEFAULT_START;
  const endRect = kb?.end_rect ?? DEFAULT_END;
  const easing: KenBurnsEasing = kb?.easing ?? "linear";

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

  const update = (patch: Partial<KenBurns>) => {
    const next: KenBurns = {
      start_rect: startRect,
      end_rect: endRect,
      easing,
      ...patch,
    };
    setKenBurns(clip.id, next);
  };

  // 画像を stage 内に contain フィットで表示するための算出
  const imagePlacement = useMemo(() => {
    if (!image) return null;
    const iw = image.naturalWidth;
    const ih = image.naturalHeight;
    if (iw <= 0 || ih <= 0) return null;
    const scale = Math.min(STAGE_W / iw, STAGE_H / ih);
    const w = iw * scale;
    const h = ih * scale;
    return { x: (STAGE_W - w) / 2, y: (STAGE_H - h) / 2, w, h };
  }, [image]);

  return (
    <div className="kb-editor">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row">
          {!kb ? (
            <button className="primary" onClick={enable}>
              Ken Burns を有効化
            </button>
          ) : (
            <>
              <label style={{ fontSize: 11, color: "var(--text-dim)" }}>
                イージング
              </label>
              <select
                value={easing}
                onChange={(e) =>
                  update({ easing: e.target.value as KenBurnsEasing })
                }
              >
                <option value="linear">linear</option>
                <option value="ease_in_out">ease_in_out</option>
              </select>
            </>
          )}
        </div>
        {kb && (
          <button onClick={disable}>Ken Burns 解除</button>
        )}
      </div>

      {kb && (
        <>
          <div className="kb-legend">
            <span className="kb-dot kb-dot-start" /> 開始
            <span className="kb-dot kb-dot-end" /> 終了
            <span style={{ marginLeft: "auto", color: "var(--text-dim)" }}>
              矩形クリックで選択 → 本体ドラッグで移動 / 四隅で拡縮
            </span>
          </div>
          <div className="kb-stage-wrap">
            <Stage
              width={STAGE_W}
              height={STAGE_H}
              onMouseDown={(e) => {
                // 背景クリックで選択解除
                if (e.target === e.target.getStage()) setSelected(null);
              }}
            >
              <Layer>
                {imagePlacement && image && (
                  <KonvaImage
                    image={image}
                    x={imagePlacement.x}
                    y={imagePlacement.y}
                    width={imagePlacement.w}
                    height={imagePlacement.h}
                    listening={false}
                  />
                )}
                <DraggableRect
                  rect={startRect}
                  color="#ff6a6a"
                  selected={selected === "start"}
                  onSelect={() => setSelected("start")}
                  onChange={(r) => update({ start_rect: r })}
                />
                <DraggableRect
                  rect={endRect}
                  color="#4f8cff"
                  selected={selected === "end"}
                  onSelect={() => setSelected("end")}
                  onChange={(r) => update({ end_rect: r })}
                />
              </Layer>
            </Stage>
          </div>
          <div className="kb-info">
            <div>
              開始: x={startRect.x.toFixed(2)} y={startRect.y.toFixed(2)} size={startRect.w.toFixed(2)}
            </div>
            <div>
              終了: x={endRect.x.toFixed(2)} y={endRect.y.toFixed(2)} size={endRect.w.toFixed(2)}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

interface DraggableRectProps {
  rect: Rect01;
  color: string;
  selected: boolean;
  onSelect: () => void;
  onChange: (rect: Rect01) => void;
}

function DraggableRect({
  rect,
  color,
  selected,
  onSelect,
  onChange,
}: DraggableRectProps) {
  const rectRef = useRef<Konva.Rect>(null);
  const trRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    if (selected && trRef.current && rectRef.current) {
      trRef.current.nodes([rectRef.current]);
      trRef.current.getLayer()?.batchDraw();
    } else if (trRef.current) {
      trRef.current.nodes([]);
    }
  }, [selected]);

  // 画面上のピクセル矩形: stage は 9:16 なので w*STAGE_W:h*STAGE_H = 9:16 (w==h なら)
  const px = rect.x * STAGE_W;
  const py = rect.y * STAGE_H;
  const pw = rect.w * STAGE_W;
  const ph = rect.h * STAGE_H;

  return (
    <>
      <Rect
        ref={rectRef}
        x={px}
        y={py}
        width={pw}
        height={ph}
        stroke={color}
        strokeWidth={selected ? 3 : 2}
        fill={color}
        opacity={selected ? 0.22 : 0.12}
        draggable={selected}
        onMouseDown={onSelect}
        onTap={onSelect}
        onDragEnd={(e) => {
          const node = e.target;
          const nx = clamp01(node.x() / STAGE_W);
          const ny = clamp01(node.y() / STAGE_H);
          // ドラッグで矩形サイズは変わらない
          const adj = clampRectToBounds({ x: nx, y: ny, w: rect.w, h: rect.h });
          onChange(adj);
        }}
        onTransformEnd={() => {
          const node = rectRef.current;
          if (!node) return;
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
        }}
      />
      {selected && (
        <Transformer
          ref={trRef}
          keepRatio
          rotateEnabled={false}
          enabledAnchors={[
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
          ]}
          boundBoxFunc={(_oldBox, newBox) => {
            // 最小サイズ
            if (newBox.width < 20 || newBox.height < 35) return _oldBox;
            return newBox;
          }}
        />
      )}
    </>
  );
}

function clamp01(v: number): number {
  if (!Number.isFinite(v)) return 0;
  return Math.max(0, Math.min(1, v));
}

function clampRectToBounds(r: Rect01): Rect01 {
  // w, h は [0.1, 1.0] 内、x+w / y+h は 1 以下に収める
  const w = Math.min(1, Math.max(0.1, r.w));
  const h = Math.min(1, Math.max(0.1, r.h));
  const x = Math.min(1 - w, Math.max(0, r.x));
  const y = Math.min(1 - h, Math.max(0, r.y));
  return { x, y, w, h };
}
