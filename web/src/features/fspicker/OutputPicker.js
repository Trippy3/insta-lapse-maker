import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import { useState } from "react";
import { FsBrowser } from "./FsBrowser";
import { FsModal } from "./FsModal";
/**
 * ディレクトリ選択 + ファイル名入力で絶対パスを組み立てる。
 * 拡張子が一致しない場合は自動付与する。
 */
export function OutputPicker({ title = "保存先を選択", initialDir, initialFilename = "", extension, onPick, onCancel, }) {
    const [selectedDir, setSelectedDir] = useState(initialDir ?? null);
    const [filename, setFilename] = useState(initialFilename);
    const canConfirm = !!selectedDir && filename.trim().length > 0;
    const handlePick = () => {
        if (!canConfirm || !selectedDir)
            return;
        let name = filename.trim();
        if (extension && !name.toLowerCase().endsWith(extension.toLowerCase())) {
            name = name + extension;
        }
        const joined = selectedDir.endsWith("/")
            ? selectedDir + name
            : selectedDir + "/" + name;
        onPick(joined);
    };
    return (_jsxs(FsModal, { title: title, onClose: onCancel, footer: _jsxs(_Fragment, { children: [_jsx("div", { className: "spacer" }), _jsx("button", { onClick: onCancel, children: "\u30AD\u30E3\u30F3\u30BB\u30EB" }), _jsx("button", { className: "primary", disabled: !canConfirm, onClick: handlePick, children: "\u6C7A\u5B9A" })] }), children: [_jsx(FsBrowser, { mode: "directory", initialPath: initialDir ?? null, selectedPath: selectedDir, onSelectedPathChange: setSelectedDir }), _jsxs("div", { className: "fs-filename-row", children: [_jsx("label", { children: "\u30D5\u30A1\u30A4\u30EB\u540D" }), _jsx("input", { type: "text", value: filename, placeholder: extension ? `例: output${extension}` : "ファイル名", onChange: (e) => setFilename(e.target.value), onKeyDown: (e) => {
                            if (e.key === "Enter" && canConfirm)
                                handlePick();
                        } }), extension && (_jsxs("span", { className: "fs-hint", children: ["\u62E1\u5F35\u5B50 ", extension, " \u306F\u81EA\u52D5\u4ED8\u4E0E"] }))] })] }));
}
