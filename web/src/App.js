import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { LibraryPanel } from "./features/library/LibraryPanel";
import { OverlayEditor } from "./features/overlay/OverlayEditor";
import { PreviewPanel } from "./features/preview/PreviewPanel";
import { ProjectToolbar } from "./features/project/ProjectToolbar";
import { RenderPanel } from "./features/render/RenderPanel";
import { ClipInspector } from "./features/timeline/ClipInspector";
import { Timeline } from "./features/timeline/Timeline";
import { useJobStream } from "./store/useJobStream";
export function App() {
    useJobStream();
    return (_jsxs("div", { className: "app-shell", children: [_jsx(ProjectToolbar, {}), _jsxs("div", { className: "workspace", children: [_jsx(LibraryPanel, {}), _jsxs("div", { style: { display: "grid", gridTemplateRows: "1fr auto" }, children: [_jsx(PreviewPanel, {}), _jsx(Timeline, {})] }), _jsxs("div", { className: "panel", style: { borderLeft: "1px solid var(--border)", overflowY: "auto" }, children: [_jsx("h3", { children: "Clip" }), _jsx(ClipInspector, {}), _jsx("div", { style: { height: 16 } }), _jsx(OverlayEditor, {}), _jsx("div", { style: { height: 16 } }), _jsx(RenderPanel, {})] })] }), _jsx("div", { style: {
                    padding: "4px 12px",
                    fontSize: 10,
                    color: "var(--text-dim)",
                    background: "var(--panel)",
                    borderTop: "1px solid var(--border)",
                }, children: "Phase 6 \u2014 \u7DE8\u96C6\u30D7\u30EC\u30D3\u30E5\u30FC (Konva) \u5B8C\u4E86" })] }));
}
