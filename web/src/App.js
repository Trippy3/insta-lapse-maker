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
    return (_jsxs("div", { className: "app-shell", children: [_jsx(ProjectToolbar, {}), _jsxs("div", { className: "workspace", children: [_jsx(LibraryPanel, {}), _jsxs("div", { style: { display: "grid", gridTemplateRows: "1fr auto", minHeight: 0 }, children: [_jsx(PreviewPanel, {}), _jsx(Timeline, {})] }), _jsxs("div", { className: "panel", style: { borderLeft: "1px solid var(--border)", overflowY: "auto" }, children: [_jsx("h3", { children: "Clip" }), _jsx(ClipInspector, {}), _jsx("div", { style: { height: 16 } }), _jsx(OverlayEditor, {}), _jsx("div", { style: { height: 16 } }), _jsx(RenderPanel, {})] })] })] }));
}
