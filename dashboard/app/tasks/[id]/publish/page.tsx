"use client";
import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import { api } from "@/lib/api";

export default function PublishPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: task } = useSWR(`task-${id}`, () => api.getTask(id));
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [privacy, setPrivacy] = useState("private");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ youtube_url: string } | null>(null);
  const [error, setError] = useState("");

  async function handlePublish(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/backend/orchestrator/tasks/${id}/publish`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title || task?.title, description, privacy }),
      });
      if (!res.ok) throw new Error(await res.text());
      setResult(await res.json());
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  if (!task) return <p className="p-6 text-gray-400">加载中…</p>;

  return (
    <main className="max-w-2xl mx-auto p-6">
      <a href={`/tasks/${id}/review`} className="text-sm text-gray-500 hover:underline">← 返回审核</a>
      <h1 className="text-2xl font-bold mt-2 mb-6">发布到 YouTube</h1>
      {result ? (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <p className="text-green-700 font-medium mb-2">发布成功！</p>
          <a href={result.youtube_url} target="_blank" rel="noreferrer"
             className="text-blue-600 hover:underline break-all">{result.youtube_url}</a>
          <button onClick={() => router.push("/")} className="mt-4 block w-full text-sm bg-black text-white py-2 rounded-lg">
            返回总览
          </button>
        </div>
      ) : (
        <form onSubmit={handlePublish} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">视频标题</label>
            <input value={title || task.title} onChange={(e) => setTitle(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">描述</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)}
              rows={4} className="w-full border rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">可见性</label>
            <select value={privacy} onChange={(e) => setPrivacy(e.target.value)}
              className="w-full border rounded-lg px-3 py-2 text-sm">
              <option value="private">私密（推荐先测试）</option>
              <option value="unlisted">不公开链接</option>
              <option value="public">公开</option>
            </select>
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-red-600 text-white py-2 rounded-lg text-sm hover:bg-red-700 disabled:opacity-50">
            {loading ? "上传中…" : "发布到 YouTube"}
          </button>
        </form>
      )}
    </main>
  );
}
