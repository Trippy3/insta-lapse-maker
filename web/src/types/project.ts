// バックエンド src/timelapse_web/models/project.py と jobs.py に対応する TS 型。
// 手動同期。Phase 1 が固まったら OpenAPI 自動生成に置き換えを検討する。

export type CropAspect = "1:1" | "9:16";

export interface Rect01 {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface CropRect {
  aspect: CropAspect;
  x: number;
  y: number;
  w: number;
  h: number;
}

export type KenBurnsEasing = "linear" | "ease_in_out";

export interface KenBurns {
  start_rect: Rect01;
  end_rect: Rect01;
  easing: KenBurnsEasing;
}

export interface Clip {
  id: string;
  source_path: string;
  order_index: number;
  duration_s: number;
  crop: CropRect | null;
  ken_burns: KenBurns | null;
}

export type TransitionKind =
  | "cut"
  | "fade"
  | "crossfade"
  | "wipe_left"
  | "wipe_right"
  | "slide_up";

export interface Transition {
  id: string;
  after_clip_id: string;
  kind: TransitionKind;
  duration_s: number;
}

export type TextAnchor =
  | "top_left"
  | "top_center"
  | "center"
  | "bottom_center"
  | "bottom_left";

export interface TextOverlay {
  id: string;
  text: string;
  font_family: string;
  font_size_px: number;
  color_hex: string;
  stroke_color_hex: string | null;
  stroke_width_px: number;
  x: number;
  y: number;
  anchor: TextAnchor;
  start_s: number;
  end_s: number;
  fade_in_s: number;
  fade_out_s: number;
}

export interface OutputSpec {
  width: number;
  height: number;
  fps: number;
}

export interface Project {
  schema_version: number;
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  output: OutputSpec;
  clips: Clip[];
  transitions: Transition[];
  overlays: TextOverlay[];
}

export type JobKind = "proxy" | "final";
export type JobStatus = "queued" | "running" | "done" | "failed";

export interface RenderJob {
  id: string;
  project_id: string;
  kind: JobKind;
  status: JobStatus;
  progress: number;
  output_path: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImageInfo {
  path: string;
  width: number;
  height: number;
  filename: string;
}

export type FsEntryType = "dir" | "image" | "file" | "other";

export interface FsEntry {
  name: string;
  path: string;
  type: FsEntryType;
  has_images: boolean;
}

export interface FsHomeResponse {
  home: string;
  roots: string[];
}

export interface FsBrowseResponse {
  path: string;
  parent: string | null;
  entries: FsEntry[];
  roots: string[];
}

export type NativePickMode = "directory" | "save-file" | "open-file";

export interface NativePickBody {
  mode: NativePickMode;
  initial_dir?: string | null;
  initial_file?: string | null;
  title?: string | null;
  default_extension?: string | null;
  filetype_name?: string | null;
  filetype_pattern?: string | null;
}

export interface NativePickResponse {
  path: string | null;
  cancelled: boolean;
}
