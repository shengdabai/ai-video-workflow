const colorMap: Record<string, string> = {
  pending: "bg-gray-100 text-gray-800",
  processing: "bg-blue-100 text-blue-800",
  generating: "bg-blue-100 text-blue-800",
  review: "bg-yellow-100 text-yellow-800",
  review_pending: "bg-yellow-100 text-yellow-800",
  approved: "bg-green-100 text-green-800",
  published: "bg-purple-100 text-purple-800",
  failed: "bg-red-100 text-red-800",
  rejected: "bg-red-100 text-red-800",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colorMap[status] ?? "bg-gray-100"}`}>
      {status}
    </span>
  );
}
