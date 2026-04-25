import { useProjectStore } from "../../store/useProjectStore";
import type { TextAnchor, TextOverlay } from "../../types/project";

const ANCHOR_LABELS: Record<TextAnchor, string> = {
  top_left: "左上",
  top_center: "上中",
  center: "中央",
  bottom_center: "下中",
  bottom_left: "左下",
};

function OverlayRow({ overlay }: { overlay: TextOverlay }) {
  const updateOverlay = useProjectStore((s) => s.updateOverlay);
  const removeOverlay = useProjectStore((s) => s.removeOverlay);

  const set = <K extends keyof Omit<TextOverlay, "id">>(key: K, value: TextOverlay[K]) =>
    updateOverlay(overlay.id, { [key]: value } as Partial<Omit<TextOverlay, "id">>);

  return (
    <div className="overlay-row">
      <div className="overlay-row-header">
        <input
          className="overlay-text-input"
          value={overlay.text}
          onChange={(e) => set("text", e.target.value)}
          placeholder="テキスト"
        />
        <button className="icon-btn" onClick={() => removeOverlay(overlay.id)} title="削除">
          ✕
        </button>
      </div>

      <div className="overlay-grid">
        <label>サイズ</label>
        <input
          type="number"
          min={8}
          max={400}
          value={overlay.font_size_px}
          onChange={(e) => set("font_size_px", Number(e.target.value))}
        />

        <label>色</label>
        <input
          type="color"
          value={overlay.color_hex}
          onChange={(e) => set("color_hex", e.target.value.toUpperCase())}
        />

        <label>縁取り</label>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <input
            type="color"
            value={overlay.stroke_color_hex ?? "#000000"}
            onChange={(e) => set("stroke_color_hex", e.target.value.toUpperCase())}
          />
          <input
            type="number"
            min={0}
            max={20}
            value={overlay.stroke_width_px}
            onChange={(e) => set("stroke_width_px", Number(e.target.value))}
            style={{ width: 48 }}
          />
          px
        </div>

        <label>位置</label>
        <select
          value={overlay.anchor}
          onChange={(e) => set("anchor", e.target.value as TextAnchor)}
        >
          {(Object.keys(ANCHOR_LABELS) as TextAnchor[]).map((a) => (
            <option key={a} value={a}>{ANCHOR_LABELS[a]}</option>
          ))}
        </select>

        <label>X</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={overlay.x}
          onChange={(e) => set("x", Number(e.target.value))}
        />

        <label>Y</label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={overlay.y}
          onChange={(e) => set("y", Number(e.target.value))}
        />

        <label>開始(s)</label>
        <input
          type="number"
          min={0}
          step={0.1}
          value={overlay.start_s}
          onChange={(e) => set("start_s", Number(e.target.value))}
        />

        <label>終了(s)</label>
        <input
          type="number"
          min={0.1}
          step={0.1}
          value={overlay.end_s}
          onChange={(e) => set("end_s", Number(e.target.value))}
        />

        <label>FI(s)</label>
        <input
          type="number"
          min={0}
          max={5}
          step={0.1}
          value={overlay.fade_in_s}
          onChange={(e) => set("fade_in_s", Number(e.target.value))}
          title="フェードイン秒数"
        />

        <label>FO(s)</label>
        <input
          type="number"
          min={0}
          max={5}
          step={0.1}
          value={overlay.fade_out_s}
          onChange={(e) => set("fade_out_s", Number(e.target.value))}
          title="フェードアウト秒数"
        />
      </div>
    </div>
  );
}

export function OverlayEditor() {
  const overlays = useProjectStore((s) => s.project.overlays);
  const addOverlay = useProjectStore((s) => s.addOverlay);

  return (
    <div className="overlay-editor">
      <div className="overlay-editor-header">
        <span style={{ fontWeight: 600, fontSize: 13 }}>テキスト</span>
        <button className="btn-sm" onClick={addOverlay}>+ 追加</button>
      </div>
      {overlays.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--text-dim)", margin: "8px 0" }}>
          オーバーレイなし
        </p>
      )}
      {overlays.map((ov) => (
        <OverlayRow key={ov.id} overlay={ov} />
      ))}
    </div>
  );
}
