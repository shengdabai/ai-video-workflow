import type { VideoTask, ShotTask, Asset } from "./types";

const BASE = "/api/backend/orchestrator";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

interface ShotPayload {
  shot_index: number;
  prompt: string;
  duration: number;
  aspect_ratio: string;
}

export const api = {
  listTasks: () => req<VideoTask[]>("/tasks"),
  getTask: (id: string) => req<VideoTask>(`/tasks/${id}`),
  createTask: (body: { title: string; script: string }) =>
    req<VideoTask>("/tasks", { method: "POST", body: JSON.stringify(body) }),
  getShots: (taskId: string) => req<ShotTask[]>(`/tasks/${taskId}/shots`),
  createShots: (taskId: string, shots: ShotPayload[]) =>
    req<ShotTask[]>(`/tasks/${taskId}/shots`, {
      method: "POST",
      body: JSON.stringify({ shots }),
    }),
  approveVideo: (taskId: string) =>
    req(`/tasks/${taskId}/review/approve`, { method: "POST" }),
  approveShot: (shotId: string) =>
    req(`/shots/${shotId}/approve`, { method: "POST" }),
  rejectShot: (shotId: string, newPrompt?: string) =>
    req(`/shots/${shotId}/reject`, {
      method: "POST",
      body: JSON.stringify({ new_prompt: newPrompt }),
    }),
};

export type { VideoTask, ShotTask, Asset };
