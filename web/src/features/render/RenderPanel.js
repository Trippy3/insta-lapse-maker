import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { OutputPicker } from "../fspicker/OutputPicker";
import { PathField } from "../fspicker/PathField";
import { nativePick } from "../fspicker/nativePick";
import { useProjectStore } from "../../store/useProjectStore";
import { dirname, sanitizeFilename } from "../../utils/path";
const KIND_LABEL = {
    proxy: "動画プレビュー",
    final: "書き出し",
};
const STATUS_LABEL = {
    queued: "待機中",
    running: "処理中",
    done: "完了",
    failed: "失敗",
};
const STATUS_CLASS = {
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
    const [outputPath, setOutputPath] = useState(null);
    const [busy, setBusy] = useState(false);
    const [pickerOpen, setPickerOpen] = useState(false);
    const ordered = Object.values(jobs).sort((a, b) => b.created_at.localeCompare(a.created_at));
    const handleRender = async (kind) => {
        if (clips.length === 0)
            return;
        setBusy(true);
        try {
            await submitRender(kind, kind === "final" && outputPath ? outputPath : undefined);
        }
        finally {
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
        }
        else if (outcome.kind === "unavailable") {
            setPickerOpen(true);
        }
    };
    return (_jsxs("div", { className: "panel", children: [_jsx("h3", { children: "\u66F8\u304D\u51FA\u3057" }), _jsxs("div", { className: "col", style: { marginBottom: 10 }, children: [_jsx("label", { children: "\u4FDD\u5B58\u5148 (\u672A\u9078\u629E\u306E\u5834\u5408\u306F\u30AD\u30E3\u30C3\u30B7\u30E5\u3078\u81EA\u52D5\u4FDD\u5B58)" }), _jsx(PathField, { value: outputPath, placeholder: "(\u672A\u9078\u629E) \u81EA\u52D5\u3067\u30AD\u30E3\u30C3\u30B7\u30E5\u306B\u4FDD\u5B58", onBrowse: () => void openPicker(), onClear: () => setOutputPath(null), browseLabel: outputPath ? "変更" : "保存先を選択" }), _jsxs("div", { className: "row", children: [_jsx("button", { className: "primary", disabled: busy || clips.length === 0, onClick: () => handleRender("final"), children: "\u66F8\u304D\u51FA\u3059 (\u9AD8\u753B\u8CEA)" }), _jsx("button", { disabled: busy || clips.length === 0, onClick: () => handleRender("proxy"), children: "\u52D5\u753B\u30D7\u30EC\u30D3\u30E5\u30FC\u3092\u4F5C\u6210" })] })] }), _jsx("h3", { children: "\u51E6\u7406\u5C65\u6B74" }), ordered.length === 0 ? (_jsx("div", { className: "empty", children: "\u307E\u3060\u51E6\u7406\u306F\u3042\u308A\u307E\u305B\u3093" })) : (ordered.map((job) => (_jsxs("div", { className: "job-row", children: [_jsxs("div", { className: "row", style: { justifyContent: "space-between" }, children: [_jsxs("span", { children: [KIND_LABEL[job.kind] ?? job.kind, _jsx("span", { className: STATUS_CLASS[job.status] || "status-badge", style: { marginLeft: 6 }, children: STATUS_LABEL[job.status] ?? job.status })] }), _jsxs("span", { style: { color: "var(--text-dim)" }, children: [Math.round(job.progress * 100), "%"] })] }), _jsx("div", { className: "progress-bar", children: _jsx("div", { style: { width: `${Math.round(job.progress * 100)}%` } }) }), job.status === "done" && job.output_path && (_jsxs("div", { style: { marginTop: 4, wordBreak: "break-all" }, children: [_jsx("a", { href: `/api/render/${job.id}/file`, download: true, style: { color: "var(--accent)" }, children: "\u30C0\u30A6\u30F3\u30ED\u30FC\u30C9" }), _jsx("div", { style: { fontSize: 10, color: "var(--text-dim)" }, children: job.output_path })] })), job.status === "failed" && (_jsx("div", { style: { color: "var(--danger)", fontSize: 11, marginTop: 4 }, children: job.error }))] }, job.id)))), pickerOpen && (_jsx(OutputPicker, { title: "\u52D5\u753B\u306E\u4FDD\u5B58\u5148\u3092\u9078\u629E", initialDir: lastSelectedDir, initialFilename: suggestedFilename, extension: ".mp4", onCancel: () => setPickerOpen(false), onPick: (path) => {
                    setPickerOpen(false);
                    setOutputPath(path);
                } }))] }));
}
