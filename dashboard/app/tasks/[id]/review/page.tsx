"use client";
import useSWR from "swr";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ShotCard } from "@/components/ShotCard";
import { StatusBadge } from "@/components/StatusBadge";

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: task } = useSWR(`task-${id}`, () => api.getTask(id));
  const { data: shots = [], mutate } = useSWR(`shots-${id}`, () => api.getShots(id), {
    refreshInterval: 2000,
  });

  const pendingCount = shots.filter((s) => s.status === "review_pending").length;
  const approvedCount = shots.filter((s) => s.status === "approved").length;

  async function handleApproveAll() {
    await api.approveVideo(id);
    router.push(`/tasks/${id}/publish`);
  }

  if (!task) return <p className="p-6 text-gray-400">加载中…</p>;

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <a href={`/tasks/${id}`} className="text-sm text-gray-500 hover:underline">← 返回任务详情</a>
          <h1 className="text-2xl font-bold mt-1">审核：{task.title}</h1>
        </div>
        <StatusBadge status={task.status} />
      </div>
      <div className="bg-blue-50 rounded-lg p-4 mb-6 flex items-center justify-between">
        <span className="text-sm text-blue-700">
          待审核 {pendingCount} 个 · 已通过 {approvedCount} 个 · 共 {shots.length} 个镜头
        </span>
        <button
          onClick={handleApproveAll}
          disabled={pendingCount > 0}
          className="text-sm bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:opacity-40"
        >
          {pendingCount > 0 ? `还有 ${pendingCount} 个待审核` : "全部通过 → 发布"}
        </button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        {shots.map((shot) => (
          <ShotCard
            key={shot.id}
            shot={shot}
            videoBaseUrl="/api/backend"
            onUpdate={mutate}
          />
        ))}
      </div>
    </main>
  );
}
