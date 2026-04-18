"use client";
import useSWR from "swr";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import { ShotCard } from "@/components/ShotCard";

export default function TaskDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: task, mutate: mutateTask } = useSWR(
    `task-${id}`, () => api.getTask(id), { refreshInterval: 3000 }
  );
  const { data: shots = [], mutate: mutateShots } = useSWR(
    `shots-${id}`, () => api.getShots(id), { refreshInterval: 3000 }
  );

  if (!task) return <p className="p-6 text-gray-400">加载中…</p>;

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Link href="/" className="text-sm text-gray-500 hover:underline">← 返回总览</Link>
          <h1 className="text-2xl font-bold mt-1">{task.title}</h1>
        </div>
        <StatusBadge status={task.status} />
      </div>
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <h2 className="text-sm font-medium mb-2">脚本</h2>
        <pre className="text-sm text-gray-600 whitespace-pre-wrap">{task.script}</pre>
      </div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">镜头列表（{shots.length}）</h2>
        {task.status === "review" && (
          <Link href={`/tasks/${id}/review`} className="text-sm bg-yellow-500 text-white px-3 py-1 rounded hover:bg-yellow-600">
            进入审核
          </Link>
        )}
      </div>
      <div className="grid grid-cols-2 gap-4">
        {shots.map((shot) => (
          <ShotCard
            key={shot.id}
            shot={shot}
            videoBaseUrl="/api/backend"
            onUpdate={() => { mutateShots(); mutateTask(); }}
          />
        ))}
      </div>
    </main>
  );
}
