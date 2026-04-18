"use client";
import useSWR from "swr";
import Link from "next/link";
import { api } from "@/lib/api";
import { TaskTable } from "@/components/TaskTable";

export default function HomePage() {
  const { data: tasks = [], isLoading } = useSWR("/tasks", () => api.listTasks(), {
    refreshInterval: 3000,
  });

  const stats = {
    total: tasks.length,
    processing: tasks.filter((t) => t.status === "processing").length,
    review: tasks.filter((t) => t.status === "review").length,
    published: tasks.filter((t) => t.status === "published").length,
  };

  return (
    <main className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">视频任务总览</h1>
        <Link href="/tasks/new" className="bg-black text-white px-4 py-2 rounded-lg text-sm hover:bg-gray-800">
          + 新建任务
        </Link>
      </div>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {[
          { label: "全部", value: stats.total },
          { label: "生成中", value: stats.processing },
          { label: "待审核", value: stats.review },
          { label: "已发布", value: stats.published },
        ].map((s) => (
          <div key={s.label} className="border rounded-lg p-4 text-center">
            <div className="text-2xl font-bold">{s.value}</div>
            <div className="text-sm text-gray-500">{s.label}</div>
          </div>
        ))}
      </div>
      {isLoading ? <p className="text-gray-400">加载中…</p> : <TaskTable tasks={tasks} />}
    </main>
  );
}
