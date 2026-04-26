import { useMemo, useState } from "react";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
import { LivePreview } from "./LivePreview";

type PreviewMode = "live" | "video";

export function PreviewPanel() {
  const [mode, setMode] = useState<PreviewMode>("live");
  const [liveAspect, setLiveAspect] = useState<number | null>(null);
  const jobs = useProjectStore((s) => s.jobs);

  const videoJob = useMemo(() => {
    const done = Object.values(jobs).filter((j) => j.status === "done");
    const latest = (kind: string) =>
      done
        .filter((j) => j.kind === kind)
        .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0] ?? null;
    return latest("proxy") ?? latest("final");
  }, [jobs]);

  // 編集プレビューでは選択中クリップの画像比率に枠を追従させる。
  // 動画プレビューは出力比率 (9:16) 固定。
  const frameStyle =
    mode === "live" && liveAspect != null
      ? { aspectRatio: `${liveAspect}` }
      : undefined;
  const frameClass =
    mode === "live" ? "preview-frame preview-frame--live" : "preview-frame";

  return (
    <div className="center">
      <div className="preview-mode-tabs">
        <button
          className={`preview-tab${mode === "live" ? " active" : ""}`}
          onClick={() => setMode("live")}
        >
          編集プレビュー
        </button>
        <button
          className={`preview-tab${mode === "video" ? " active" : ""}`}
          onClick={() => setMode("video")}
        >
          動画プレビュー
        </button>
      </div>

      <div className={frameClass} style={frameStyle}>
        {mode === "live" ? (
          <LivePreview onAspectChange={setLiveAspect} />
        ) : videoJob ? (
          <video
            key={videoJob.id}
            src={api.downloadUrl(videoJob.id)}
            controls
            autoPlay
            loop
            muted
          />
        ) : (
          <div style={{ padding: 20, textAlign: "center" }}>
            「動画プレビューを作成」または「書き出す」後の動画がここに表示されます
          </div>
        )}
      </div>
    </div>
  );
}
