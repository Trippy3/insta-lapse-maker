import { useEffect, useRef } from "react";
import { useProjectStore } from "./useProjectStore";

const DEBOUNCE_MS = 1000;

export function useAutoProxy() {
  const updatedAt = useProjectStore((s) => s.project.updated_at);
  const clipCount = useProjectStore((s) => s.project.clips.length);
  const submitRender = useProjectStore((s) => s.submitRender);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(false);

  useEffect(() => {
    if (!mountedRef.current) {
      mountedRef.current = true;
      return;
    }
    if (clipCount === 0) return;

    if (timerRef.current !== null) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      submitRender("proxy").catch(() => {});
      timerRef.current = null;
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current !== null) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [updatedAt]);
}
