from __future__ import annotations

import asyncio
import os
from typing import Optional


def _concat_list_line(path: str) -> str:
    """
    Return one "file" line for ffmpeg's concat demuxer list.

    The path is single-quoted. A single quote inside it is written as '\\''
    (end the quoted part, an escaped quote, start a new quoted part), which
    is how ffmpeg's quoting rules spell a literal quote. A line break cannot
    be quoted in this format, so such a path is refused.
    """
    if any(c in path for c in "\n\r\x00"):
        raise ValueError("clip path must not contain line breaks or NUL bytes")
    return "file '" + path.replace("'", "'\\''") + "'\n"


async def compose_video(
    clip_paths: list[str],
    output_path: str,
    bgm_path: Optional[str] = None,
) -> str:
    lines = [_concat_list_line(os.path.abspath(p)) for p in clip_paths]
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    list_file = output_path + ".txt"
    with open(list_file, "w", encoding="utf-8") as f:
        f.writelines(lines)

    if bgm_path:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-stream_loop", "-1", "-i", bgm_path,
            "-map", "0:v", "-map", "1:a",
            "-shortest", "-c:v", "copy",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", list_file,
            "-c", "copy",
            output_path,
        ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if os.path.exists(list_file):
        os.unlink(list_file)

    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {stderr.decode()}")

    return output_path
