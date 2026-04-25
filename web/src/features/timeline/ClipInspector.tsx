import { useState } from "react";
import { CropEditor } from "../crop/CropEditor";
import { KenBurnsEditor } from "../kenburns/KenBurnsEditor";
import { useProjectStore } from "../../store/useProjectStore";

export function ClipInspector() {
  const selectedId = useProjectStore((s) => s.selectedClipId);
  const clip = useProjectStore((s) =>
    s.project.clips.find((c) => c.id === selectedId),
  );
  const updateDuration = useProjectStore((s) => s.updateClipDuration);
  const [cropOpen, setCropOpen] = useState(true);
  const [kbOpen, setKbOpen] = useState(false);

  if (!clip) {
    return <div className="empty">クリップを選択してください</div>;
  }

  return (
    <div className="col">
      <div className="clip-controls">
        <label>ファイル</label>
        <span
          style={{ fontSize: 11, color: "var(--text-dim)", wordBreak: "break-all" }}
          title={clip.source_path}
        >
          {clip.source_path.split("/").pop()}
        </span>

        <label>尺 (秒)</label>
        <input
          type="number"
          min={0.1}
          max={10}
          step={0.1}
          value={clip.duration_s}
          onChange={(e) => {
            const v = Number.parseFloat(e.target.value);
            if (Number.isFinite(v) && v > 0) updateDuration(clip.id, v);
          }}
        />
      </div>

      <div style={{ marginTop: 8 }}>
        <button
          style={{ width: "100%" }}
          onClick={() => setCropOpen((o) => !o)}
        >
          {cropOpen ? "▼" : "▶"} トリミング {clip.crop ? "(設定済み)" : "(未設定)"}
        </button>
        {cropOpen && <CropEditor clip={clip} />}
      </div>

      <div style={{ marginTop: 8 }}>
        <button
          style={{ width: "100%" }}
          onClick={() => setKbOpen((o) => !o)}
        >
          {kbOpen ? "▼" : "▶"} Ken Burns {clip.ken_burns ? `(${clip.ken_burns.easing})` : "(未設定)"}
        </button>
        {kbOpen && <KenBurnsEditor clip={clip} />}
      </div>
    </div>
  );
}
