"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function NewTaskPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [script, setScript] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim() || !script.trim()) { setError("标题和脚本不能为空"); return; }
    setLoading(true);
    try {
      const task = await api.createTask({ title, script });
      router.push(`/tasks/${task.id}`);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">新建视频任务</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">视频标题</label>
          <input
            value={title} onChange={(e) => setTitle(e.target.value)}
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="输入视频标题"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">脚本（每行一个镜头描述）</label>
          <textarea
            value={script} onChange={(e) => setScript(e.target.value)}
            rows={8}
            className="w-full border rounded-lg px-3 py-2 text-sm font-mono"
            placeholder={"镜头1：海边日落，金色光芒洒在水面\n镜头2：城市夜景，霓虹灯光璀璨"}
          />
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit" disabled={loading}
          className="w-full bg-black text-white py-2 rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50"
        >
          {loading ? "创建中…" : "创建任务"}
        </button>
      </form>
    </main>
  );
}
