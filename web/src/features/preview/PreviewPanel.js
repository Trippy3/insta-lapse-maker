import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useMemo, useState } from "react";
import { api } from "../../api/client";
import { useProjectStore } from "../../store/useProjectStore";
import { LivePreview } from "./LivePreview";
export function PreviewPanel() {
    const [mode, setMode] = useState("live");
    const [liveAspect, setLiveAspect] = useState(null);
    const jobs = useProjectStore((s) => s.jobs);
    const videoJob = useMemo(() => {
        const done = Object.values(jobs).filter((j) => j.status === "done");
        const latest = (kind) => done
            .filter((j) => j.kind === kind)
            .sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0] ?? null;
        return latest("proxy") ?? latest("final");
    }, [jobs]);
    // 編集プレビューでは選択中クリップの画像比率に枠を追従させる。
    // 動画プレビューは出力比率 (9:16) 固定。
    const frameStyle = mode === "live" && liveAspect != null
        ? { aspectRatio: `${liveAspect}` }
        : undefined;
    const frameClass = mode === "live" ? "preview-frame preview-frame--live" : "preview-frame";
    return (_jsxs("div", { className: "center", children: [_jsxs("div", { className: "preview-mode-tabs", children: [_jsx("button", { className: `preview-tab${mode === "live" ? " active" : ""}`, onClick: () => setMode("live"), children: "\u7DE8\u96C6\u30D7\u30EC\u30D3\u30E5\u30FC" }), _jsx("button", { className: `preview-tab${mode === "video" ? " active" : ""}`, onClick: () => setMode("video"), children: "\u52D5\u753B\u30D7\u30EC\u30D3\u30E5\u30FC" })] }), _jsx("div", { className: frameClass, style: frameStyle, children: mode === "live" ? (_jsx(LivePreview, { onAspectChange: setLiveAspect })) : videoJob ? (_jsx("video", { src: api.downloadUrl(videoJob.id), controls: true, autoPlay: true, loop: true, muted: true }, videoJob.id)) : (_jsx("div", { style: { padding: 20, textAlign: "center" }, children: "\u300C\u52D5\u753B\u30D7\u30EC\u30D3\u30E5\u30FC\u3092\u4F5C\u6210\u300D\u307E\u305F\u306F\u300C\u66F8\u304D\u51FA\u3059\u300D\u5F8C\u306E\u52D5\u753B\u304C\u3053\u3053\u306B\u8868\u793A\u3055\u308C\u307E\u3059" })) })] }));
}
