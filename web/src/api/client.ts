import type {
  FsBrowseResponse,
  FsHomeResponse,
  ImageInfo,
  JobKind,
  NativePickBody,
  NativePickResponse,
  Project,
  RenderJob,
} from "../types/project";

const API = "";

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
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
        message = String((payload as { detail: unknown }).detail);
      }
    } catch {
      const text = await res.text().catch(() => "");
      if (text) message = text;
    }
    throw new ApiError(res.status, message);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ ok: boolean; cache_root: string }>("/api/health"),

  createProject: (project: Project) =>
    request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(project),
    }),

  updateProject: (project: Project) =>
    request<Project>(`/api/projects/${project.id}`, {
      method: "PUT",
      body: JSON.stringify(project),
    }),

  saveProject: (projectId: string, path: string) =>
    request<{ project: Project; path: string }>(
      `/api/projects/${projectId}/save`,
      { method: "POST", body: JSON.stringify({ path }) },
    ),

  loadProject: (path: string) =>
    request<{ project: Project; path: string }>("/api/projects/load", {
      method: "POST",
      body: JSON.stringify({ path }),
    }),

  scanDirectory: (
    directory: string,
    options: { sort?: "filename" | "exif"; recursive?: boolean } = {},
  ) => {
    const sort = options.sort ?? "filename";
    const recursive = options.recursive ?? false;
    const qs = new URLSearchParams({
      directory,
      sort,
      recursive: recursive ? "true" : "false",
    });
    return request<{ directory: string; images: ImageInfo[] }>(
      `/api/media/scan?${qs.toString()}`,
    );
  },

  thumbnailUrl: (path: string) =>
    `/api/media/thumbnail?path=${encodeURIComponent(path)}`,

  submitRender: (projectId: string, kind: JobKind, outputPath?: string) =>
    request<RenderJob>("/api/render", {
      method: "POST",
      body: JSON.stringify({
        project_id: projectId,
        kind,
        output_path: outputPath ?? null,
      }),
    }),

  getJob: (jobId: string) => request<RenderJob>(`/api/render/${jobId}`),

  downloadUrl: (jobId: string) => `/api/render/${jobId}/file`,

  fsHome: () => request<FsHomeResponse>("/api/fs/home"),

  fsBrowse: (
    path: string,
    options: { showHidden?: boolean; matchExt?: string } = {},
  ) => {
    const qs = new URLSearchParams({
      path,
      show_hidden: options.showHidden ? "true" : "false",
    });
    if (options.matchExt) qs.set("match_ext", options.matchExt);
    return request<FsBrowseResponse>(`/api/fs/browse?${qs.toString()}`);
  },

  fsNativeAvailable: () =>
    request<{ available: boolean }>("/api/fs/native-available"),

  fsNativePick: (body: NativePickBody) =>
    request<NativePickResponse>("/api/fs/native-pick", {
      method: "POST",
      body: JSON.stringify(body),
    }),
};
