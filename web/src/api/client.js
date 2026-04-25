const API = "";
export class ApiError extends Error {
    status;
    constructor(status, message) {
        super(message);
        this.status = status;
        this.name = "ApiError";
    }
}
async function request(url, init) {
    const res = await fetch(API + url, {
        ...init,
        headers: {
            "Content-Type": "application/json",
            ...(init?.headers || {}),
        },
    });
    if (!res.ok) {
        // FastAPI の {detail: "..."} があればそれを優先
        let message = `${res.status} ${res.statusText}`;
        try {
            const payload = await res.clone().json();
            if (payload && typeof payload === "object" && "detail" in payload) {
                message = String(payload.detail);
            }
        }
        catch {
            const text = await res.text().catch(() => "");
            if (text)
                message = text;
        }
        throw new ApiError(res.status, message);
    }
    return (await res.json());
}
export const api = {
    health: () => request("/api/health"),
    createProject: (project) => request("/api/projects", {
        method: "POST",
        body: JSON.stringify(project),
    }),
    updateProject: (project) => request(`/api/projects/${project.id}`, {
        method: "PUT",
        body: JSON.stringify(project),
    }),
    saveProject: (projectId, path) => request(`/api/projects/${projectId}/save`, { method: "POST", body: JSON.stringify({ path }) }),
    loadProject: (path) => request("/api/projects/load", {
        method: "POST",
        body: JSON.stringify({ path }),
    }),
    scanDirectory: (directory, options = {}) => {
        const sort = options.sort ?? "filename";
        const recursive = options.recursive ?? false;
        const qs = new URLSearchParams({
            directory,
            sort,
            recursive: recursive ? "true" : "false",
        });
        return request(`/api/media/scan?${qs.toString()}`);
    },
    thumbnailUrl: (path) => `/api/media/thumbnail?path=${encodeURIComponent(path)}`,
    submitRender: (projectId, kind, outputPath) => request("/api/render", {
        method: "POST",
        body: JSON.stringify({
            project_id: projectId,
            kind,
            output_path: outputPath ?? null,
        }),
    }),
    getJob: (jobId) => request(`/api/render/${jobId}`),
    downloadUrl: (jobId) => `/api/render/${jobId}/file`,
    fsHome: () => request("/api/fs/home"),
    fsBrowse: (path, options = {}) => {
        const qs = new URLSearchParams({
            path,
            show_hidden: options.showHidden ? "true" : "false",
        });
        if (options.matchExt)
            qs.set("match_ext", options.matchExt);
        return request(`/api/fs/browse?${qs.toString()}`);
    },
    fsNativeAvailable: () => request("/api/fs/native-available"),
    fsNativePick: (body) => request("/api/fs/native-pick", {
        method: "POST",
        body: JSON.stringify(body),
    }),
};
