export function VideoPlayer({ src }: { src: string }) {
  return (
    <video
      src={src}
      controls
      className="w-full rounded-lg bg-black"
      style={{ maxHeight: "480px" }}
    />
  );
}
