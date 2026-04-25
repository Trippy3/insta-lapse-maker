import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { api } from "../../api/client";
import { DirectoryPicker } from "../fspicker/DirectoryPicker";
import { PathField } from "../fspicker/PathField";
import { nativePick } from "../fspicker/nativePick";
import { useProjectStore } from "../../store/useProjectStore";
export function LibraryPanel() {
    const libraryDir = useProjectStore((s) => s.libraryDir);
    const library = useProjectStore((s) => s.library);
    const scanLibrary = useProjectStore((s) => s.scanLibrary);
    const addClips = useProjectStore((s) => s.addClipsFromLibrary);
    const [recursive, setRecursive] = useState(false);
    const [loading, setLoading] = useState(false);
    const [scanned, setScanned] = useState(false);
    const [pickerOpen, setPickerOpen] = useState(false);
    const handleScan = async (dir) => {
        if (!dir)
            return;
        setLoading(true);
        await scanLibrary(dir, recursive);
        setScanned(true);
        setLoading(false);
    };
    const openPicker = async () => {
        const outcome = await nativePick({
            mode: "directory",
            initial_dir: libraryDir || null,
            title: "画像フォルダを選択",
        });
        if (outcome.kind === "picked") {
            setScanned(false);
            void handleScan(outcome.path);
        }
        else if (outcome.kind === "unavailable") {
            setPickerOpen(true);
        }
    };
    const handleAddAll = () => addClips(library.map((i) => i.path));
    return (_jsxs("div", { className: "panel", children: [_jsx("h3", { children: "Library" }), _jsxs("div", { className: "col", style: { marginBottom: 10 }, children: [_jsx("label", { children: "\u753B\u50CF\u30D5\u30A9\u30EB\u30C0" }), _jsx(PathField, { value: libraryDir || null, placeholder: "(\u672A\u9078\u629E) \u30D5\u30A9\u30EB\u30C0\u3092\u9078\u629E\u3057\u3066\u304F\u3060\u3055\u3044", onBrowse: () => void openPicker(), browseLabel: libraryDir ? "変更" : "フォルダを選択" }), _jsxs("label", { style: { display: "flex", alignItems: "center", gap: 6, fontSize: 12 }, children: [_jsx("input", { type: "checkbox", checked: recursive, onChange: (e) => setRecursive(e.target.checked) }), "\u30B5\u30D6\u30C7\u30A3\u30EC\u30AF\u30C8\u30EA\u3082\u542B\u3081\u308B"] }), _jsxs("div", { className: "row", children: [_jsx("button", { onClick: () => handleScan(libraryDir), disabled: !libraryDir || loading, children: loading ? "読込中..." : "スキャン" }), _jsxs("button", { onClick: handleAddAll, disabled: library.length === 0, children: ["\u5168\u8FFD\u52A0 (", library.length, ")"] })] })] }), library.length === 0 ? (_jsx("div", { className: "empty", children: scanned
                    ? "このディレクトリに対応画像がありません。サブディレクトリも含める を試してください。"
                    : "画像フォルダを選択してください" })) : (_jsx("div", { children: library.map((item) => (_jsxs("div", { className: "library-item", onClick: () => addClips([item.path]), title: item.path, children: [_jsx("img", { src: api.thumbnailUrl(item.path), alt: item.filename, loading: "lazy" }), _jsx("div", { className: "name", children: item.filename }), _jsxs("div", { style: { fontSize: 10, color: "var(--text-dim)" }, children: [item.width, "\u00D7", item.height] })] }, item.path))) })), pickerOpen && (_jsx(DirectoryPicker, { title: "\u753B\u50CF\u30D5\u30A9\u30EB\u30C0\u3092\u9078\u629E", initialPath: libraryDir || null, onCancel: () => setPickerOpen(false), onPick: (path) => {
                    setPickerOpen(false);
                    setScanned(false);
                    void handleScan(path);
                } }))] }));
}
