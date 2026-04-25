import { create } from "zustand";
import { api } from "../api/client";
import type {
  Clip,
  CropRect,
  ImageInfo,
  KenBurns,
  Project,
  RenderJob,
  TextAnchor,
  TextOverlay,
  Transition,
  TransitionKind,
} from "../types/project";

const INITIAL: Project = {
  schema_version: 1,
  id: `proj_${cryptoId()}`,
  name: "Untitled",
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  output: { width: 1080, height: 1920, fps: 30 },
  clips: [],
  transitions: [],
  overlays: [],
};

function cryptoId(): string {
  const bytes = new Uint8Array(5);
  crypto.getRandomValues(bytes);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

interface ProjectState {
  project: Project;
  selectedClipId: string | null;
  library: ImageInfo[];
  libraryDir: string;
  projectPath: string | null;
  jobs: Record<string, RenderJob>;
  lastError: string | null;

  setLibraryDir: (dir: string) => void;
  scanLibrary: (dir: string, recursive?: boolean) => Promise<void>;
  addClipsFromLibrary: (paths: string[]) => void;
  selectClip: (id: string | null) => void;
  removeClip: (id: string) => void;
  moveClip: (id: string, delta: -1 | 1) => void;
  updateClipDuration: (id: string, duration: number) => void;
  setClipCrop: (id: string, crop: CropRect | null) => void;
  setClipKenBurns: (id: string, kb: KenBurns | null) => void;
  setTransition: (afterClipId: string, kind: TransitionKind, durationS: number) => void;
  removeTransition: (afterClipId: string) => void;

  addOverlay: () => void;
  updateOverlay: (id: string, patch: Partial<Omit<TextOverlay, "id">>) => void;
  removeOverlay: (id: string) => void;

  setProjectName: (name: string) => void;
  resetProject: () => void;

  saveToPath: (path: string) => Promise<void>;
  loadFromPath: (path: string) => Promise<void>;
  pushProjectToServer: () => Promise<void>;

  submitRender: (kind: "final" | "proxy", outputPath?: string) => Promise<RenderJob>;
  applyJobEvent: (job: RenderJob) => void;
  setError: (msg: string | null) => void;
}

function reindex(clips: Clip[]): Clip[] {
  return clips.map((c, i) => ({ ...c, order_index: i }));
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  project: INITIAL,
  selectedClipId: null,
  library: [],
  libraryDir: "",
  projectPath: null,
  jobs: {},
  lastError: null,

  setLibraryDir: (dir) => set({ libraryDir: dir }),

  scanLibrary: async (dir, recursive = false) => {
    try {
      const res = await api.scanDirectory(dir, { recursive });
      set({ library: res.images, libraryDir: res.directory, lastError: null });
    } catch (e) {
      set({ lastError: (e as Error).message, library: [] });
    }
  },

  addClipsFromLibrary: (paths) => {
    const now = get().project;
    const base = now.clips.length;
    const newClips: Clip[] = paths.map((p, i) => ({
      id: `clip_${cryptoId()}`,
      source_path: p,
      order_index: base + i,
      duration_s: 0.5,
      crop: null,
      ken_burns: null,
    }));
    const next: Project = {
      ...now,
      clips: [...now.clips, ...newClips],
      updated_at: new Date().toISOString(),
    };
    set({ project: next });
  },

  selectClip: (id) => set({ selectedClipId: id }),

  removeClip: (id) => {
    const p = get().project;
    const clips = reindex(p.clips.filter((c) => c.id !== id));
    set({
      project: { ...p, clips, updated_at: new Date().toISOString() },
      selectedClipId: get().selectedClipId === id ? null : get().selectedClipId,
    });
  },

  moveClip: (id, delta) => {
    const p = get().project;
    const sorted = [...p.clips].sort((a, b) => a.order_index - b.order_index);
    const idx = sorted.findIndex((c) => c.id === id);
    const newIdx = idx + delta;
    if (idx < 0 || newIdx < 0 || newIdx >= sorted.length) return;
    const [moved] = sorted.splice(idx, 1);
    sorted.splice(newIdx, 0, moved);
    set({
      project: {
        ...p,
        clips: reindex(sorted),
        updated_at: new Date().toISOString(),
      },
    });
  },

  updateClipDuration: (id, duration) => {
    const p = get().project;
    const clips = p.clips.map((c) =>
      c.id === id ? { ...c, duration_s: duration } : c,
    );
    set({ project: { ...p, clips, updated_at: new Date().toISOString() } });
  },

  setClipCrop: (id, crop) => {
    const p = get().project;
    const clips = p.clips.map((c) => (c.id === id ? { ...c, crop } : c));
    set({ project: { ...p, clips, updated_at: new Date().toISOString() } });
  },

  setClipKenBurns: (id, kb) => {
    const p = get().project;
    const clips = p.clips.map((c) => (c.id === id ? { ...c, ken_burns: kb } : c));
    set({ project: { ...p, clips, updated_at: new Date().toISOString() } });
  },

  setTransition: (afterClipId, kind, durationS) => {
    const p = get().project;
    const existing = p.transitions.find((t) => t.after_clip_id === afterClipId);
    let transitions: Transition[];
    if (existing) {
      transitions = p.transitions.map((t) =>
        t.after_clip_id === afterClipId ? { ...t, kind, duration_s: durationS } : t,
      );
    } else {
      const id = `tr_${cryptoId()}`;
      transitions = [...p.transitions, { id, after_clip_id: afterClipId, kind, duration_s: durationS }];
    }
    set({ project: { ...p, transitions, updated_at: new Date().toISOString() } });
  },

  removeTransition: (afterClipId) => {
    const p = get().project;
    const transitions = p.transitions.filter((t) => t.after_clip_id !== afterClipId);
    set({ project: { ...p, transitions, updated_at: new Date().toISOString() } });
  },

  addOverlay: () => {
    const p = get().project;
    const newOverlay: TextOverlay = {
      id: `txt_${cryptoId()}`,
      text: "テキスト",
      font_family: "NotoSansJP",
      font_size_px: 64,
      color_hex: "#FFFFFF",
      stroke_color_hex: "#000000",
      stroke_width_px: 2,
      x: 0.5,
      y: 0.5,
      anchor: "center" as TextAnchor,
      start_s: 0.0,
      end_s: Math.max(1.0, p.clips.reduce((s, c) => s + c.duration_s, 0) * 0.5),
      fade_in_s: 0.0,
      fade_out_s: 0.0,
    };
    set({ project: { ...p, overlays: [...p.overlays, newOverlay], updated_at: new Date().toISOString() } });
  },

  updateOverlay: (id, patch) => {
    const p = get().project;
    const overlays = p.overlays.map((o) => (o.id === id ? { ...o, ...patch } : o));
    set({ project: { ...p, overlays, updated_at: new Date().toISOString() } });
  },

  removeOverlay: (id) => {
    const p = get().project;
    const overlays = p.overlays.filter((o) => o.id !== id);
    set({ project: { ...p, overlays, updated_at: new Date().toISOString() } });
  },

  setProjectName: (name) => {
    const p = get().project;
    set({ project: { ...p, name, updated_at: new Date().toISOString() } });
  },

  resetProject: () => {
    set({
      project: {
        ...INITIAL,
        id: `proj_${cryptoId()}`,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
      selectedClipId: null,
      projectPath: null,
      jobs: {},
    });
  },

  pushProjectToServer: async () => {
    const p = get().project;
    try {
      // サーバーに存在しない場合 create、存在する場合 update
      await api.createProject(p).catch(async () => {
        await api.updateProject(p);
      });
    } catch (e) {
      set({ lastError: (e as Error).message });
      throw e;
    }
  },

  saveToPath: async (path) => {
    await get().pushProjectToServer();
    const p = get().project;
    try {
      const res = await api.saveProject(p.id, path);
      set({ projectPath: res.path, lastError: null });
    } catch (e) {
      set({ lastError: (e as Error).message });
    }
  },

  loadFromPath: async (path) => {
    try {
      const res = await api.loadProject(path);
      set({
        project: res.project,
        projectPath: res.path,
        selectedClipId: null,
        jobs: {},
        lastError: null,
      });
    } catch (e) {
      set({ lastError: (e as Error).message });
    }
  },

  submitRender: async (kind, outputPath) => {
    await get().pushProjectToServer();
    const p = get().project;
    const job = await api.submitRender(p.id, kind, outputPath);
    set({ jobs: { ...get().jobs, [job.id]: job } });
    return job;
  },

  applyJobEvent: (job) => {
    set({ jobs: { ...get().jobs, [job.id]: job } });
  },

  setError: (msg) => set({ lastError: msg }),
}));
