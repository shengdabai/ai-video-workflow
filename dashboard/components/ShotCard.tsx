"use client";
import { useState } from "react";
import { ShotTask } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { api } from "@/lib/api";

interface ShotCardProps {
  shot: ShotTask;
  videoBaseUrl: string;
  onUpdate: () => void;
}

export function ShotCard({ shot, onUpdate }: ShotCardProps) {
  const [editPrompt, setEditPrompt] = useState(shot.prompt);
  const [showReject, setShowReject] = useState(false);

  async function handleApprove() {
    await api.approveShot(shot.id);
    onUpdate();
  }

  async function handleReject() {
    await api.rejectShot(shot.id, editPrompt !== shot.prompt ? editPrompt : undefined);
    setShowReject(false);
    onUpdate();
  }

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">镜头 {shot.shot_index + 1}</span>
        <StatusBadge status={shot.status} />
      </div>
      <p className="text-sm text-gray-600">{shot.prompt}</p>
      {shot.status === "review_pending" && (
        <div className="flex gap-2">
          <button onClick={handleApprove} className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">
            通过
          </button>
          <button onClick={() => setShowReject(!showReject)} className="text-xs bg-red-500 text-white px-3 py-1 rounded hover:bg-red-600">
            退回
          </button>
        </div>
      )}
      {showReject && (
        <div className="space-y-2">
          <textarea
            value={editPrompt}
            onChange={(e) => setEditPrompt(e.target.value)}
            className="w-full border rounded px-2 py-1 text-xs"
            rows={3}
          />
          <button onClick={handleReject} className="text-xs bg-orange-500 text-white px-3 py-1 rounded">
            确认退回并重跑
          </button>
        </div>
      )}
    </div>
  );
}
