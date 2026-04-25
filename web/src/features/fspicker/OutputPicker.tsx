import { useState } from "react";
import { FsBrowser } from "./FsBrowser";
import { FsModal } from "./FsModal";

interface OutputPickerProps {
  title?: string;
  initialDir?: string | null;
  initialFilename?: string;
  extension?: string; // 例: ".mp4", ".tlproj.json"
  onPick: (absolutePath: string) => void;
  onCancel: () => void;
}

/**
 * ディレクトリ選択 + ファイル名入力で絶対パスを組み立てる。
 * 拡張子が一致しない場合は自動付与する。
 */
export function OutputPicker({
  title = "保存先を選択",
  initialDir,
  initialFilename = "",
  extension,
  onPick,
  onCancel,
}: OutputPickerProps) {
  const [selectedDir, setSelectedDir] = useState<string | null>(initialDir ?? null);
  const [filename, setFilename] = useState(initialFilename);

  const canConfirm = !!selectedDir && filename.trim().length > 0;

  const handlePick = () => {
    if (!canConfirm || !selectedDir) return;
    let name = filename.trim();
    if (extension && !name.toLowerCase().endsWith(extension.toLowerCase())) {
      name = name + extension;
    }
    const joined = selectedDir.endsWith("/")
      ? selectedDir + name
      : selectedDir + "/" + name;
    onPick(joined);
  };

  return (
    <FsModal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <div className="spacer" />
          <button onClick={onCancel}>キャンセル</button>
          <button className="primary" disabled={!canConfirm} onClick={handlePick}>
            決定
          </button>
        </>
      }
    >
      <FsBrowser
        mode="directory"
        initialPath={initialDir ?? null}
        selectedPath={selectedDir}
        onSelectedPathChange={setSelectedDir}
      />
      <div className="fs-filename-row">
        <label>ファイル名</label>
        <input
          type="text"
          value={filename}
          placeholder={extension ? `例: output${extension}` : "ファイル名"}
          onChange={(e) => setFilename(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && canConfirm) handlePick();
          }}
        />
        {extension && (
          <span className="fs-hint">拡張子 {extension} は自動付与</span>
        )}
      </div>
    </FsModal>
  );
}
