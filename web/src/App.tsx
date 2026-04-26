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

  return (
    <div className="app-shell">
      <ProjectToolbar />
      <div className="workspace">
        <LibraryPanel />
        <div style={{ display: "grid", gridTemplateRows: "1fr auto", minHeight: 0 }}>
          <PreviewPanel />
          <Timeline />
        </div>
        <div className="panel" style={{ borderLeft: "1px solid var(--border)", overflowY: "auto" }}>
          <h3>Clip</h3>
          <ClipInspector />
          <div style={{ height: 16 }} />
          <OverlayEditor />
          <div style={{ height: 16 }} />
          <RenderPanel />
        </div>
      </div>
    </div>
  );
}
