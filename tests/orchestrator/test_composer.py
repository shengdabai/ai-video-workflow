import asyncio

import pytest

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


class _FakeProcess:
    returncode = 0

    async def communicate(self):
        return b"", b""


@pytest.fixture
def ffmpeg_lists(monkeypatch):
    """Stub ffmpeg; record the concat list file content of every call."""
    lists = []

    async def fake_exec(*args, **kwargs):
        list_file = args[args.index("-i") + 1]
        with open(list_file, encoding="utf-8") as f:
            lists.append(f.read())
        return _FakeProcess()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    return lists


def _ffmpeg_unquote(token: str) -> str:
    """Undo ffmpeg's quoting for one token: '...' is literal, \\x outside quotes is x."""
    out = []
    quoted = False
    chars = iter(token)
    for c in chars:
        if c == "'":
            quoted = not quoted
        elif c == "\\" and not quoted:
            out.append(next(chars))
        else:
            out.append(c)
    assert not quoted, token
    return "".join(out)


def _listed_paths(content: str) -> list[str]:
    paths = []
    for line in content.splitlines():
        directive, _, token = line.partition(" ")
        assert directive == "file"
        paths.append(_ffmpeg_unquote(token))
    return paths


@pytest.mark.parametrize(
    "name",
    [
        "it's.mp4",
        "a'b'c.mp4",
        "'leading.mp4",
        "trailing'.mp4",
        "x'\\''y.mp4",
        "back\\slash.mp4",
        "with space.mp4",
        "clip'; file '..'.mp4",
    ],
)
async def test_concat_list_quotes_single_quotes_in_clip_paths(tmp_path, ffmpeg_lists, name):
    clip_dir = tmp_path / "Bob's clips"
    clip_dir.mkdir()
    clips = [clip_dir / name, tmp_path / "plain.mp4"]
    for clip in clips:
        clip.write_bytes(b"")
    output_path = str(tmp_path / "exports" / "final.mp4")

    await compose_video(clip_paths=[str(c) for c in clips], output_path=output_path)

    (content,) = ffmpeg_lists
    assert _listed_paths(content) == [str(c) for c in clips]
    # Every line is one directive: the quote in a name cannot end the path.
    assert len(content.splitlines()) == len(clips)


async def test_concat_list_line_for_quoted_path(tmp_path, ffmpeg_lists):
    clip = tmp_path / "it's.mp4"
    clip.write_bytes(b"")
    await compose_video(clip_paths=[str(clip)], output_path=str(tmp_path / "out" / "final.mp4"))
    expected_path = str(clip).replace("'", "'\\''")
    assert ffmpeg_lists == [f"file '{expected_path}'\n"]


@pytest.mark.parametrize("name", ["new\nline.mp4", "carriage\rreturn.mp4"])
async def test_concat_list_refuses_line_breaks(tmp_path, ffmpeg_lists, name):
    output_path = tmp_path / "out" / "final.mp4"
    with pytest.raises(ValueError):
        await compose_video(clip_paths=[str(tmp_path / name)], output_path=str(output_path))
    assert ffmpeg_lists == []
    assert not (tmp_path / "out" / "final.mp4.txt").exists()
