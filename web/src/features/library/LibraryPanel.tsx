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

  const handleScan = async (dir: string | null) => {
    if (!dir) return;
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
    } else if (outcome.kind === "unavailable") {
      setPickerOpen(true);
    }
  };

  const handleAddAll = () => addClips(library.map((i) => i.path));

  return (
    <div className="panel">
      <h3>Library</h3>
      <div className="col" style={{ marginBottom: 10 }}>
        <label>画像フォルダ</label>
        <PathField
          value={libraryDir || null}
          placeholder="(未選択) フォルダを選択してください"
          onBrowse={() => void openPicker()}
          browseLabel={libraryDir ? "変更" : "フォルダを選択"}
        />
        <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <input
            type="checkbox"
            checked={recursive}
            onChange={(e) => setRecursive(e.target.checked)}
          />
          サブディレクトリも含める
        </label>
        <div className="row">
          <button onClick={() => handleScan(libraryDir)} disabled={!libraryDir || loading}>
            {loading ? "読込中..." : "スキャン"}
          </button>
          <button onClick={handleAddAll} disabled={library.length === 0}>
            全追加 ({library.length})
          </button>
        </div>
      </div>

      {library.length === 0 ? (
        <div className="empty">
          {scanned
            ? "このディレクトリに対応画像がありません。サブディレクトリも含める を試してください。"
            : "画像フォルダを選択してください"}
        </div>
      ) : (
        <div>
          {library.map((item) => (
            <div
              key={item.path}
              className="library-item"
              onClick={() => addClips([item.path])}
              title={item.path}
            >
              <img src={api.thumbnailUrl(item.path)} alt={item.filename} loading="lazy" />
              <div className="name">{item.filename}</div>
              <div style={{ fontSize: 10, color: "var(--text-dim)" }}>
                {item.width}×{item.height}
              </div>
            </div>
          ))}
        </div>
      )}

      {pickerOpen && (
        <DirectoryPicker
          title="画像フォルダを選択"
          initialPath={libraryDir || null}
          onCancel={() => setPickerOpen(false)}
          onPick={(path) => {
            setPickerOpen(false);
            setScanned(false);
            void handleScan(path);
          }}
        />
      )}
    </div>
  );
}
