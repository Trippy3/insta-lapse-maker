import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
import { TransitionPicker } from "../transitions/TransitionPicker";

export function Timeline() {
  const clips = useProjectStore((s) =>
    [...s.project.clips].sort((a, b) => a.order_index - b.order_index),
  );
  const transitions = useProjectStore((s) => s.project.transitions);
  const selectedId = useProjectStore((s) => s.selectedClipId);
  const selectClip = useProjectStore((s) => s.selectClip);
  const moveClip = useProjectStore((s) => s.moveClip);
  const removeClip = useProjectStore((s) => s.removeClip);

  const trByClipId = Object.fromEntries(transitions.map((t) => [t.after_clip_id, t]));

  if (clips.length === 0) {
    return (
      <div className="timeline">
        <div className="empty">ライブラリからクリップを追加してください</div>
      </div>
    );
  }

  return (
    <div className="timeline">
      <div className="timeline-row">
        {clips.map((c, i) => (
          <div key={c.id} className="clip-with-transition">
            <div
              className={`clip-card ${selectedId === c.id ? "selected" : ""}`}
              onClick={() => selectClip(c.id)}
            >
              <img src={api.thumbnailUrl(c.source_path)} alt="" loading="lazy" />
              <div className="meta">
                <span>{c.duration_s.toFixed(2)}s</span>
                <span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      moveClip(c.id, -1);
                    }}
                    title="前へ"
                    style={{ padding: "1px 4px", fontSize: 10 }}
                  >
                    ◀
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      moveClip(c.id, 1);
                    }}
                    title="後ろへ"
                    style={{ padding: "1px 4px", fontSize: 10, marginLeft: 2 }}
                  >
                    ▶
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeClip(c.id);
                    }}
                    title="削除"
                    style={{ padding: "1px 4px", fontSize: 10, marginLeft: 2 }}
                  >
                    ✕
                  </button>
                </span>
              </div>
            </div>
            {i < clips.length - 1 && (
              <TransitionPicker
                afterClipId={c.id}
                transition={trByClipId[c.id]}
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
