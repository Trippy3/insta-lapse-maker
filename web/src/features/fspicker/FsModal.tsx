import { useEffect } from "react";
import type { ReactNode } from "react";

interface FsModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
}

export function FsModal({ title, onClose, children, footer }: FsModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [onClose]);

  return (
    <div className="fs-modal-backdrop" onMouseDown={onClose}>
      <div className="fs-modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="fs-modal-head">
          <span>{title}</span>
          <button onClick={onClose} aria-label="閉じる">
            ✕
          </button>
        </div>
        <div className="fs-modal-body">{children}</div>
        {footer && <div className="fs-modal-foot">{footer}</div>}
      </div>
    </div>
  );
}
