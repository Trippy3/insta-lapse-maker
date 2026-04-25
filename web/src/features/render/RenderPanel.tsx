import { useState } from "react";
import { OutputPicker } from "../fspicker/OutputPicker";
import { PathField } from "../fspicker/PathField";
import { nativePick } from "../fspicker/nativePick";
import { useProjectStore } from "../../store/useProjectStore";
import { dirname, sanitizeFilename } from "../../utils/path";

const KIND_LABEL: Record<string, string> = {
  proxy: "動画プレビュー",
  final: "書き出し",
};

const STATUS_LABEL: Record<string, string> = {
  queued: "待機中",
  running: "処理中",
  done: "完了",
  failed: "失敗",
};

const STATUS_CLASS: Record<string, string> = {
  queued: "status-badge status-queued",
  running: "status-badge status-running",
  done: "status-badge status-done",
  failed: "status-badge status-failed",
};

export function RenderPanel() {
  const jobs = useProjectStore((s) => s.jobs);
  const submitRender = useProjectStore((s) => s.submitRender);
  const clips = useProjectStore((s) => s.project.clips);
  const projectName = useProjectStore((s) => s.project.name);
  const [outputPath, setOutputPath] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);

  const ordered = Object.values(jobs).sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  );

  const handleRender = async (kind: "final" | "proxy") => {
    if (clips.length === 0) return;
    setBusy(true);
    try {
      await submitRender(kind, kind === "final" && outputPath ? outputPath : undefined);
    } finally {
      setBusy(false);
    }
  };

  const suggestedFilename = `${sanitizeFilename(projectName) || "output"}.mp4`;
  const lastSelectedDir = outputPath ? dirname(outputPath) : null;

  const openPicker = async () => {
    const outcome = await nativePick({
      mode: "save-file",
      title: "動画の保存先を選択",
      initial_dir: lastSelectedDir,
      initial_file: suggestedFilename,
      default_extension: ".mp4",
      filetype_name: "MP4 Video",
      filetype_pattern: "*.mp4",
    });
    if (outcome.kind === "picked") {
      setOutputPath(outcome.path);
    } else if (outcome.kind === "unavailable") {
      setPickerOpen(true);
    }
  };

  return (
    <div className="panel">
      <h3>書き出し</h3>

      <div className="col" style={{ marginBottom: 10 }}>
        <label>保存先 (未選択の場合はキャッシュへ自動保存)</label>
        <PathField
          value={outputPath}
          placeholder="(未選択) 自動でキャッシュに保存"
          onBrowse={() => void openPicker()}
          onClear={() => setOutputPath(null)}
          browseLabel={outputPath ? "変更" : "保存先を選択"}
        />
        <div className="row">
          <button
            className="primary"
            disabled={busy || clips.length === 0}
            onClick={() => handleRender("final")}
          >
            書き出す (高画質)
          </button>
          <button
            disabled={busy || clips.length === 0}
            onClick={() => handleRender("proxy")}
          >
            動画プレビューを作成
          </button>
        </div>
      </div>

      <h3>処理履歴</h3>
      {ordered.length === 0 ? (
        <div className="empty">まだ処理はありません</div>
      ) : (
        ordered.map((job) => (
          <div key={job.id} className="job-row">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <span>
                {KIND_LABEL[job.kind] ?? job.kind}
                <span
                  className={STATUS_CLASS[job.status] || "status-badge"}
                  style={{ marginLeft: 6 }}
                >
                  {STATUS_LABEL[job.status] ?? job.status}
                </span>
              </span>
              <span style={{ color: "var(--text-dim)" }}>
                {Math.round(job.progress * 100)}%
              </span>
            </div>
            <div className="progress-bar">
              <div style={{ width: `${Math.round(job.progress * 100)}%` }} />
            </div>
            {job.status === "done" && job.output_path && (
              <div style={{ marginTop: 4, wordBreak: "break-all" }}>
                <a
                  href={`/api/render/${job.id}/file`}
                  download
                  style={{ color: "var(--accent)" }}
                >
                  ダウンロード
                </a>
                <div style={{ fontSize: 10, color: "var(--text-dim)" }}>
                  {job.output_path}
                </div>
              </div>
            )}
            {job.status === "failed" && (
              <div style={{ color: "var(--danger)", fontSize: 11, marginTop: 4 }}>
                {job.error}
              </div>
            )}
          </div>
        ))
      )}

      {pickerOpen && (
        <OutputPicker
          title="動画の保存先を選択"
          initialDir={lastSelectedDir}
          initialFilename={suggestedFilename}
          extension=".mp4"
          onCancel={() => setPickerOpen(false)}
          onPick={(path) => {
            setPickerOpen(false);
            setOutputPath(path);
          }}
        />
      )}
    </div>
  );
}

