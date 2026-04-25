import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
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
    const [loadSelected, setLoadSelected] = useState(null);
    const handlePickSave = async (path) => {
        setSaveOpen(false);
        await saveToPath(path);
    };
    const handlePickLoad = async () => {
        if (!loadSelected)
            return;
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
            initial_file: projectPath?.split("/").pop() ?? suggestedFilename,
            default_extension: PROJECT_EXT,
            filetype_name: "Timelapse Project",
            filetype_pattern: `*${PROJECT_EXT}`,
        });
        if (outcome.kind === "picked") {
            await saveToPath(outcome.path);
        }
        else if (outcome.kind === "unavailable") {
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
        }
        else if (outcome.kind === "unavailable") {
            setLoadOpen(true);
        }
    };
    return (_jsxs(_Fragment, { children: [_jsxs("div", { className: "toolbar", children: [_jsx("span", { className: "title", children: "timelapse editor" }), _jsx("input", { type: "text", value: name, onChange: (e) => setName(e.target.value), style: { width: 220 } }), _jsxs("span", { style: { color: "var(--text-dim)", fontSize: 11 }, children: [clipCount, " clips"] }), projectPath && (_jsx("span", { style: { color: "var(--text-dim)", fontSize: 11 }, title: projectPath, children: projectPath.split("/").pop() })), _jsx("div", { className: "spacer" }), lastError && (_jsx("span", { style: { color: "var(--danger)", fontSize: 11 }, title: lastError, children: lastError.slice(0, 60) })), _jsx("button", { onClick: resetProject, children: "\u65B0\u898F" }), _jsx("button", { onClick: () => void openLoadPicker(), children: "\u958B\u304F" }), _jsx("button", { onClick: () => void openSavePicker(), children: "\u4FDD\u5B58" })] }), saveOpen && (_jsx(OutputPicker, { title: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u306E\u4FDD\u5B58\u5148\u3092\u9078\u629E", initialDir: saveInitialDir, initialFilename: projectPath ? projectPath.split("/").pop() ?? suggestedFilename : suggestedFilename, extension: PROJECT_EXT, onCancel: () => setSaveOpen(false), onPick: handlePickSave })), loadOpen && (_jsxs(FsModal, { title: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u3092\u958B\u304F", onClose: () => {
                    setLoadOpen(false);
                    setLoadSelected(null);
                }, footer: _jsxs(_Fragment, { children: [_jsx("div", { className: "spacer" }), _jsx("button", { onClick: () => {
                                setLoadOpen(false);
                                setLoadSelected(null);
                            }, children: "\u30AD\u30E3\u30F3\u30BB\u30EB" }), _jsx("button", { className: "primary", disabled: !isProjectFile(loadSelected), onClick: handlePickLoad, children: "\u958B\u304F" })] }), children: [_jsx(FsBrowser, { mode: "any-file", matchExt: PROJECT_EXT, initialPath: saveInitialDir, selectedPath: loadSelected, onSelectedPathChange: setLoadSelected }), _jsx("div", { style: { fontSize: 11, color: "var(--text-dim)", marginTop: 6 }, children: "\u203B `.tlproj.json` \u30D5\u30A1\u30A4\u30EB\u306E\u307F\u304C\u5BFE\u8C61\u3067\u3059" }), loadSelected && !isProjectFile(loadSelected) && (_jsx("div", { className: "fs-error", style: { marginTop: 6 }, children: "\u30D7\u30ED\u30B8\u30A7\u30AF\u30C8\u30D5\u30A1\u30A4\u30EB (*.tlproj.json) \u3092\u9078\u629E\u3057\u3066\u304F\u3060\u3055\u3044" }))] }))] }));
}
function isProjectFile(path) {
    return !!path && path.toLowerCase().endsWith(PROJECT_EXT);
}
