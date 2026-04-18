export type VideoTaskStatus =
  | "pending" | "processing" | "review"
  | "approved" | "published" | "failed";

export type ShotStatus =
  | "pending" | "generating" | "failed"
  | "review_pending" | "approved" | "rejected";

export interface VideoTask {
  id: string;
  title: string;
  script: string;
  style_pack_id: string | null;
  character_pack_id: string | null;
  status: VideoTaskStatus;
  created_at: string;
  updated_at: string;
}

export interface ShotTask {
  id: string;
  video_task_id: string;
  shot_index: number;
  prompt: string;
  duration: number;
  aspect_ratio: string;
  status: ShotStatus;
  retry_count: number;
  provider: string;
  provider_job_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: string;
  task_id: string | null;
  shot_id: string | null;
  type: string;
  file_path: string;
  file_size: number;
  meta: string;
  created_at: string;
}
