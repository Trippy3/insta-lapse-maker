import { useState } from "react";
import { FsBrowser } from "../fspicker/FsBrowser";
import { FsModal } from "../fspicker/FsModal";
import { OutputPicker } from "../fspicker/OutputPicker";
import { nativePick } from "../fspicker/nativePick";
import { useProjectStore } from "../../store/useProjectStore";
import { dirname, sanitizeFilename } from "../../utils/path";

const PROJECT_EXT = ".tlproj.json";

export function ProjectToolbar() {
  const name = useProjectStore((s) => s.project.name);
  const setName = useProjectStore((s) => s.setProjectName);
  const resetProject = useProjectStore((s) => s.resetProject);
  const saveToPath = useProjectStore((s) => s.saveToPath);
  const loadFromPath = useProjectStore((s) => s.loadFromPath);
  const projectPath = useProjectStore((s) => s.projectPath);
  const lastError = useProjectStore((s) => s.lastError);
  const clipCount = useProjectStore((s) => s.project.clips.length);

  const [saveOpen, setSaveOpen] = useState(false);
  const [loadOpen, setLoadOpen] = useState(false);
  const [loadSelected, setLoadSelected] = useState<string | null>(null);

  const handlePickSave = async (path: string) => {
    setSaveOpen(false);
    await saveToPath(path);
  };

  const handlePickLoad = async () => {
    if (!loadSelected) return;
    setLoadOpen(false);
    await loadFromPath(loadSelected);
    setLoadSelected(null);
  };

  const suggestedFilename = `${sanitizeFilename(name) || "project"}${PROJECT_EXT}`;
  const saveInitialDir = projectPath ? dirname(projectPath) : null;

  const openSavePicker = async () => {
    const outcome = await nativePick({
      mode: "save-file",
      title: "プロジェクトの保存先を選択",
      initial_dir: saveInitialDir,
      initial_file:
        projectPath?.split("/").pop() ?? suggestedFilename,
      default_extension: PROJECT_EXT,
      filetype_name: "Timelapse Project",
      filetype_pattern: `*${PROJECT_EXT}`,
    });
    if (outcome.kind === "picked") {
      await saveToPath(outcome.path);
    } else if (outcome.kind === "unavailable") {
      setSaveOpen(true);
    }
  };

  const openLoadPicker = async () => {
    const outcome = await nativePick({
      mode: "open-file",
      title: "プロジェクトを開く",
      initial_dir: saveInitialDir,
      filetype_name: "Timelapse Project",
      filetype_pattern: `*${PROJECT_EXT}`,
    });
    if (outcome.kind === "picked") {
      if (!outcome.path.toLowerCase().endsWith(PROJECT_EXT)) {
        window.alert("プロジェクトファイル (*.tlproj.json) を選択してください");
        return;
      }
      await loadFromPath(outcome.path);
    } else if (outcome.kind === "unavailable") {
      setLoadOpen(true);
    }
  };

  return (
    <>
      <div className="toolbar">
        <span className="title">timelapse editor</span>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: 220 }}
        />
        <span style={{ color: "var(--text-dim)", fontSize: 11 }}>
          {clipCount} clips
        </span>
        {projectPath && (
          <span style={{ color: "var(--text-dim)", fontSize: 11 }} title={projectPath}>
            {projectPath.split("/").pop()}
          </span>
        )}
        <div className="spacer" />
        {lastError && (
          <span style={{ color: "var(--danger)", fontSize: 11 }} title={lastError}>
            {lastError.slice(0, 60)}
          </span>
        )}
        <button onClick={resetProject}>新規</button>
        <button onClick={() => void openLoadPicker()}>開く</button>
        <button onClick={() => void openSavePicker()}>保存</button>
      </div>

      {saveOpen && (
        <OutputPicker
          title="プロジェクトの保存先を選択"
          initialDir={saveInitialDir}
          initialFilename={projectPath ? projectPath.split("/").pop() ?? suggestedFilename : suggestedFilename}
          extension={PROJECT_EXT}
          onCancel={() => setSaveOpen(false)}
          onPick={handlePickSave}
        />
      )}

      {loadOpen && (
        <FsModal
          title="プロジェクトを開く"
          onClose={() => {
            setLoadOpen(false);
            setLoadSelected(null);
          }}
          footer={
            <>
              <div className="spacer" />
              <button
                onClick={() => {
                  setLoadOpen(false);
                  setLoadSelected(null);
                }}
              >
                キャンセル
              </button>
              <button
                className="primary"
                disabled={!isProjectFile(loadSelected)}
                onClick={handlePickLoad}
              >
                開く
              </button>
            </>
          }
        >
          <FsBrowser
            mode="any-file"
            matchExt={PROJECT_EXT}
            initialPath={saveInitialDir}
            selectedPath={loadSelected}
            onSelectedPathChange={setLoadSelected}
          />
          <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 6 }}>
            ※ `.tlproj.json` ファイルのみが対象です
          </div>
          {loadSelected && !isProjectFile(loadSelected) && (
            <div className="fs-error" style={{ marginTop: 6 }}>
              プロジェクトファイル (*.tlproj.json) を選択してください
            </div>
          )}
        </FsModal>
      )}
    </>
  );
}


function isProjectFile(path: string | null): boolean {
  return !!path && path.toLowerCase().endsWith(PROJECT_EXT);
}
