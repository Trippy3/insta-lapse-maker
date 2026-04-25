import { useEffect } from "react";
import { useProjectStore } from "./useProjectStore";
export function useJobStream() {
    const applyJobEvent = useProjectStore((s) => s.applyJobEvent);
    useEffect(() => {
        const es = new EventSource("/api/events/jobs");
        es.addEventListener("job", (ev) => {
            try {
                const job = JSON.parse(ev.data);
                applyJobEvent(job);
            }
            catch (err) {
                console.warn("failed to parse job event", err);
            }
        });
        es.onerror = (err) => {
            console.debug("SSE error", err);
        };
        return () => es.close();
    }, [applyJobEvent]);
}
