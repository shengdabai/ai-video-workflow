"use client";
import Link from "next/link";
import { VideoTask } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

export function TaskTable({ tasks }: { tasks: VideoTask[] }) {
  if (tasks.length === 0) {
    return <p className="text-gray-500 text-sm py-8 text-center">暂无任务</p>;
  }
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b text-left text-gray-500">
          <th className="py-2 pr-4">标题</th>
          <th className="py-2 pr-4">状态</th>
          <th className="py-2 pr-4">创建时间</th>
          <th className="py-2">操作</th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((t) => (
          <tr key={t.id} className="border-b hover:bg-gray-50">
            <td className="py-2 pr-4 font-medium">{t.title}</td>
            <td className="py-2 pr-4"><StatusBadge status={t.status} /></td>
            <td className="py-2 pr-4 text-gray-500">{t.created_at.slice(0, 16)}</td>
            <td className="py-2">
              <Link href={`/tasks/${t.id}`} className="text-blue-600 hover:underline mr-3">详情</Link>
              {t.status === "review" && (
                <Link href={`/tasks/${t.id}/review`} className="text-yellow-600 hover:underline">审核</Link>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
