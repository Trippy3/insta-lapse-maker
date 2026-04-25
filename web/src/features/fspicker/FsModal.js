import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect } from "react";
export function FsModal({ title, onClose, children, footer }) {
    useEffect(() => {
        const handler = (e) => {
            if (e.key === "Escape")
                onClose();
        };
        window.addEventListener("keydown", handler);
        return () => window.removeEventListener("keydown", handler);
    }, [onClose]);
    return (_jsx("div", { className: "fs-modal-backdrop", onMouseDown: onClose, children: _jsxs("div", { className: "fs-modal", onMouseDown: (e) => e.stopPropagation(), children: [_jsxs("div", { className: "fs-modal-head", children: [_jsx("span", { children: title }), _jsx("button", { onClick: onClose, "aria-label": "\u9589\u3058\u308B", children: "\u2715" })] }), _jsx("div", { className: "fs-modal-body", children: children }), footer && _jsx("div", { className: "fs-modal-foot", children: footer })] }) }));
}
