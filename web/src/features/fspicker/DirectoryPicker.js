import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import { FsBrowser } from "./FsBrowser";
import { FsModal } from "./FsModal";
export function DirectoryPicker({ title = "フォルダを選択", initialPath, onPick, onCancel, confirmLabel = "決定", }) {
    const [selected, setSelected] = useState(initialPath ?? null);
    return (_jsx(FsModal, { title: title, onClose: onCancel, footer: _jsxs(_Fragment, { children: [_jsx("div", { className: "spacer" }), _jsx("button", { onClick: onCancel, children: "\u30AD\u30E3\u30F3\u30BB\u30EB" }), _jsx("button", { className: "primary", disabled: !selected, onClick: () => selected && onPick(selected), children: confirmLabel })] }), children: _jsx(FsBrowser, { mode: "directory", initialPath: initialPath ?? null, selectedPath: selected, onSelectedPathChange: setSelected }) }));
}
