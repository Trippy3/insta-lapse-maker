import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import type { FsBrowseResponse, FsEntry, FsEntryType } from "../../types/project";

export type FsPickMode = "directory" | "image-file" | "any-file";

interface FsBrowserProps {
  initialPath?: string | null;
  mode: FsPickMode;
  selectedPath: string | null;
  onSelectedPathChange: (path: string | null) => void;
  /** 画像以外で表示したい拡張子 (例: ".tlproj.json,.json") */
  matchExt?: string;
}

export function FsBrowser({
  initialPath,
  mode,
  selectedPath,
  onSelectedPathChange,
  matchExt,
}: FsBrowserProps) {
  const [currentPath, setCurrentPath] = useState<string | null>(initialPath ?? null);
  const [data, setData] = useState<FsBrowseResponse | null>(null);
  const [roots, setRoots] = useState<string[]>([]);
  const [showHidden, setShowHidden] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPath = useCallback(
    async (path: string, opts: { hidden?: boolean } = {}) => {
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
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setLoading(false);
      }
    },
    [showHidden, matchExt],
  );

  useEffect(() => {
    let cancelled = false;
    const bootstrap = async () => {
      try {
        let startPath = initialPath ?? null;
        if (!startPath) {
          const home = await api.fsHome();
          startPath = home.home;
          if (!cancelled) setRoots(home.roots);
        }
        if (!cancelled && startPath) {
          await loadPath(startPath);
        }
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
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

  const isSelectable = (entry: FsEntry): boolean => {
    if (mode === "directory") return entry.type === "dir";
    if (mode === "image-file") return entry.type === "image";
    return entry.type === "image" || entry.type === "file";
  };

  const handleEntryDoubleClick = (entry: FsEntry) => {
    if (entry.type === "dir") {
      void loadPath(entry.path);
      return;
    }
    if (isSelectable(entry)) onSelectedPathChange(entry.path);
  };

  const handleEntryClick = (entry: FsEntry) => {
    if (mode === "directory") {
      if (entry.type === "dir") onSelectedPathChange(entry.path);
      return;
    }
    if (isSelectable(entry)) onSelectedPathChange(entry.path);
  };

  const goParent = () => {
    if (data?.parent) void loadPath(data.parent);
  };

  const goHome = async () => {
    try {
      const home = await api.fsHome();
      setRoots(home.roots);
      await loadPath(home.home);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const canSelectCurrent = mode === "directory" && !!currentPath;
  const filtered = (data?.entries ?? []).filter((e) => {
    if (e.type === "dir") return true;
    if (mode === "directory") return false;
    if (mode === "image-file") return e.type === "image";
    return e.type === "image" || e.type === "file";
  });

  return (
    <div className="fs-browser">
      <div className="fs-toolbar">
        <button onClick={goParent} disabled={!data?.parent} title="親ディレクトリへ">
          ↑ 上へ
        </button>
        <button onClick={goHome} title="ホームへ戻る">
          🏠 ホーム
        </button>
        <button
          onClick={() => currentPath && loadPath(currentPath)}
          disabled={!currentPath || loading}
          title="再読込"
        >
          ↻
        </button>
        <label className="fs-toggle">
          <input
            type="checkbox"
            checked={showHidden}
            onChange={(e) => {
              setShowHidden(e.target.checked);
              if (currentPath) void loadPath(currentPath, { hidden: e.target.checked });
            }}
          />
          隠しファイル
        </label>
      </div>

      <div className="fs-breadcrumbs" title={currentPath ?? ""}>
        {crumbs.map((c, i) => (
          <span key={c.path} className="fs-crumb">
            {i > 0 && <span className="fs-sep">/</span>}
            <button className="fs-crumb-btn" onClick={() => loadPath(c.path)}>
              {c.label}
            </button>
          </span>
        ))}
      </div>

      {mode === "directory" && (
        <div className="fs-select-current">
          <button
            className={canSelectCurrent && selectedPath === currentPath ? "primary" : ""}
            onClick={() => canSelectCurrent && onSelectedPathChange(currentPath)}
            disabled={!canSelectCurrent}
          >
            ✓ このフォルダを選択
          </button>
          {selectedPath && (
            <span className="fs-selected" title={selectedPath}>
              選択中: {selectedPath}
            </span>
          )}
        </div>
      )}

      {error && <div className="fs-error">{error}</div>}

      <div className="fs-list" aria-busy={loading}>
        {loading && !data ? (
          <div className="empty">読込中...</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            {mode === "directory"
              ? "サブフォルダはありません"
              : "フォルダも画像もありません"}
          </div>
        ) : (
          filtered.map((entry) => (
            <div
              key={entry.path}
              className={
                "fs-entry" + (selectedPath === entry.path ? " selected" : "")
              }
              onClick={() => handleEntryClick(entry)}
              onDoubleClick={() => handleEntryDoubleClick(entry)}
              title={entry.path}
            >
              <span className="fs-icon">{iconOf(entry.type, entry.has_images)}</span>
              <span className="fs-name">{entry.name}</span>
              {entry.type === "dir" && entry.has_images && (
                <span className="fs-badge">画像あり</span>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function iconOf(type: FsEntryType, hasImages: boolean): string {
  if (type === "dir") return hasImages ? "📂" : "📁";
  if (type === "image") return "🖼";
  if (type === "file") return "📄";
  return "·";
}

function buildCrumbs(
  currentPath: string | null,
  roots: string[],
): { label: string; path: string }[] {
  if (!currentPath) return [];
  // currentPath を含む root を探す
  const parentRoot = roots.find((r) => currentPath === r || currentPath.startsWith(r + "/"));
  if (!parentRoot) return [{ label: currentPath, path: currentPath }];

  const crumbs: { label: string; path: string }[] = [
    { label: displayRootName(parentRoot), path: parentRoot },
  ];
  if (currentPath === parentRoot) return crumbs;

  const rel = currentPath.slice(parentRoot.length).replace(/^\/+/, "");
  const parts = rel.split("/").filter(Boolean);
  let acc = parentRoot;
  for (const part of parts) {
    acc = acc.endsWith("/") ? acc + part : acc + "/" + part;
    crumbs.push({ label: part, path: acc });
  }
  return crumbs;
}

function displayRootName(root: string): string {
  const trimmed = root.replace(/\/+$/, "");
  const base = trimmed.split("/").pop();
  return base ? base : "/";
}
