import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
export function FsBrowser({ initialPath, mode, selectedPath, onSelectedPathChange, matchExt, }) {
    const [currentPath, setCurrentPath] = useState(initialPath ?? null);
    const [data, setData] = useState(null);
    const [roots, setRoots] = useState([]);
    const [showHidden, setShowHidden] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const loadPath = useCallback(async (path, opts = {}) => {
        setLoading(true);
        setError(null);
        try {
            const res = await api.fsBrowse(path, {
                showHidden: opts.hidden ?? showHidden,
                matchExt,
            });
            setData(res);
            setCurrentPath(res.path);
            setRoots(res.roots);
        }
        catch (e) {
            setError(e.message);
        }
        finally {
            setLoading(false);
        }
    }, [showHidden, matchExt]);
    useEffect(() => {
        let cancelled = false;
        const bootstrap = async () => {
            try {
                let startPath = initialPath ?? null;
                if (!startPath) {
                    const home = await api.fsHome();
                    startPath = home.home;
                    if (!cancelled)
                        setRoots(home.roots);
                }
                if (!cancelled && startPath) {
                    await loadPath(startPath);
                }
            }
            catch (e) {
                if (!cancelled)
                    setError(e.message);
            }
        };
        bootstrap();
        return () => {
            cancelled = true;
        };
        // initialPath は初回のみ参照する
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);
    const crumbs = useMemo(() => buildCrumbs(currentPath, roots), [currentPath, roots]);
    const isSelectable = (entry) => {
        if (mode === "directory")
            return entry.type === "dir";
        if (mode === "image-file")
            return entry.type === "image";
        return entry.type === "image" || entry.type === "file";
    };
    const handleEntryDoubleClick = (entry) => {
        if (entry.type === "dir") {
            void loadPath(entry.path);
            return;
        }
        if (isSelectable(entry))
            onSelectedPathChange(entry.path);
    };
    const handleEntryClick = (entry) => {
        if (mode === "directory") {
            if (entry.type === "dir")
                onSelectedPathChange(entry.path);
            return;
        }
        if (isSelectable(entry))
            onSelectedPathChange(entry.path);
    };
    const goParent = () => {
        if (data?.parent)
            void loadPath(data.parent);
    };
    const goHome = async () => {
        try {
            const home = await api.fsHome();
            setRoots(home.roots);
            await loadPath(home.home);
        }
        catch (e) {
            setError(e.message);
        }
    };
    const canSelectCurrent = mode === "directory" && !!currentPath;
    const filtered = (data?.entries ?? []).filter((e) => {
        if (e.type === "dir")
            return true;
        if (mode === "directory")
            return false;
        if (mode === "image-file")
            return e.type === "image";
        return e.type === "image" || e.type === "file";
    });
    return (_jsxs("div", { className: "fs-browser", children: [_jsxs("div", { className: "fs-toolbar", children: [_jsx("button", { onClick: goParent, disabled: !data?.parent, title: "\u89AA\u30C7\u30A3\u30EC\u30AF\u30C8\u30EA\u3078", children: "\u2191 \u4E0A\u3078" }), _jsx("button", { onClick: goHome, title: "\u30DB\u30FC\u30E0\u3078\u623B\u308B", children: "\uD83C\uDFE0 \u30DB\u30FC\u30E0" }), _jsx("button", { onClick: () => currentPath && loadPath(currentPath), disabled: !currentPath || loading, title: "\u518D\u8AAD\u8FBC", children: "\u21BB" }), _jsxs("label", { className: "fs-toggle", children: [_jsx("input", { type: "checkbox", checked: showHidden, onChange: (e) => {
                                    setShowHidden(e.target.checked);
                                    if (currentPath)
                                        void loadPath(currentPath, { hidden: e.target.checked });
                                } }), "\u96A0\u3057\u30D5\u30A1\u30A4\u30EB"] })] }), _jsx("div", { className: "fs-breadcrumbs", title: currentPath ?? "", children: crumbs.map((c, i) => (_jsxs("span", { className: "fs-crumb", children: [i > 0 && _jsx("span", { className: "fs-sep", children: "/" }), _jsx("button", { className: "fs-crumb-btn", onClick: () => loadPath(c.path), children: c.label })] }, c.path))) }), mode === "directory" && (_jsxs("div", { className: "fs-select-current", children: [_jsx("button", { className: canSelectCurrent && selectedPath === currentPath ? "primary" : "", onClick: () => canSelectCurrent && onSelectedPathChange(currentPath), disabled: !canSelectCurrent, children: "\u2713 \u3053\u306E\u30D5\u30A9\u30EB\u30C0\u3092\u9078\u629E" }), selectedPath && (_jsxs("span", { className: "fs-selected", title: selectedPath, children: ["\u9078\u629E\u4E2D: ", selectedPath] }))] })), error && _jsx("div", { className: "fs-error", children: error }), _jsx("div", { className: "fs-list", "aria-busy": loading, children: loading && !data ? (_jsx("div", { className: "empty", children: "\u8AAD\u8FBC\u4E2D..." })) : filtered.length === 0 ? (_jsx("div", { className: "empty", children: mode === "directory"
                        ? "サブフォルダはありません"
                        : "フォルダも画像もありません" })) : (filtered.map((entry) => (_jsxs("div", { className: "fs-entry" + (selectedPath === entry.path ? " selected" : ""), onClick: () => handleEntryClick(entry), onDoubleClick: () => handleEntryDoubleClick(entry), title: entry.path, children: [_jsx("span", { className: "fs-icon", children: iconOf(entry.type, entry.has_images) }), _jsx("span", { className: "fs-name", children: entry.name }), entry.type === "dir" && entry.has_images && (_jsx("span", { className: "fs-badge", children: "\u753B\u50CF\u3042\u308A" }))] }, entry.path)))) })] }));
}
function iconOf(type, hasImages) {
    if (type === "dir")
        return hasImages ? "📂" : "📁";
    if (type === "image")
        return "🖼";
    if (type === "file")
        return "📄";
    return "·";
}
function buildCrumbs(currentPath, roots) {
    if (!currentPath)
        return [];
    // currentPath を含む root を探す
    const parentRoot = roots.find((r) => currentPath === r || currentPath.startsWith(r + "/"));
    if (!parentRoot)
        return [{ label: currentPath, path: currentPath }];
    const crumbs = [
        { label: displayRootName(parentRoot), path: parentRoot },
    ];
    if (currentPath === parentRoot)
        return crumbs;
    const rel = currentPath.slice(parentRoot.length).replace(/^\/+/, "");
    const parts = rel.split("/").filter(Boolean);
    let acc = parentRoot;
    for (const part of parts) {
        acc = acc.endsWith("/") ? acc + part : acc + "/" + part;
        crumbs.push({ label: part, path: acc });
    }
    return crumbs;
}
function displayRootName(root) {
    const trimmed = root.replace(/\/+$/, "");
    const base = trimmed.split("/").pop();
    return base ? base : "/";
}
