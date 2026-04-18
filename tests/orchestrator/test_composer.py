import pytest
import os
from orchestrator.publish.composer import compose_video


@pytest.mark.asyncio
async def test_compose_video(tmp_path):
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()
    clip1 = clips_dir / "0.mp4"
    clip1.write_bytes(b"")
    output_path = str(tmp_path / "output.mp4")
    clip_paths = [str(clip1)]
    with pytest.raises(Exception):
        await compose_video(clip_paths=clip_paths, output_path=output_path)
