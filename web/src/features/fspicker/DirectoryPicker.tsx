import { useState } from "react";
import { FsBrowser } from "./FsBrowser";
import { FsModal } from "./FsModal";

interface DirectoryPickerProps {
  title?: string;
  initialPath?: string | null;
  onPick: (path: string) => void;
  onCancel: () => void;
  confirmLabel?: string;
}

export function DirectoryPicker({
  title = "フォルダを選択",
  initialPath,
  onPick,
  onCancel,
  confirmLabel = "決定",
}: DirectoryPickerProps) {
  const [selected, setSelected] = useState<string | null>(initialPath ?? null);

  return (
    <FsModal
      title={title}
      onClose={onCancel}
      footer={
        <>
          <div className="spacer" />
          <button onClick={onCancel}>キャンセル</button>
          <button
            className="primary"
            disabled={!selected}
            onClick={() => selected && onPick(selected)}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <FsBrowser
        mode="directory"
        initialPath={initialPath ?? null}
        selectedPath={selected}
        onSelectedPathChange={setSelected}
      />
    </FsModal>
  );
}
