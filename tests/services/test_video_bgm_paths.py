"""VideoService only uses BGM files inside data/bgm/, bgm/ or output/.

The Streamlit UI and the API both reach VideoService._resolve_bgm_path. A
bare file name is looked up in data/bgm/ first, then bgm/; "bgm/...",
"data/bgm/..." and "output/..." name the directory; an absolute path is used
only when it points inside one of these directories. Everything else raises
FileNotFoundError. The directories are inside PIXELLE_VIDEO_ROOT.
"""

import pytest

from pixelle_video.services.video import VideoService


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Project root with BGM directories, and a working directory elsewhere."""
    (tmp_path / "outer.mp3").write_bytes(b"outer audio")

    root = tmp_path / "app"
    (root / "bgm").mkdir(parents=True)
    (root / "bgm" / "default.mp3").write_bytes(b"default audio")
    (root / "bgm" / "shared.mp3").write_bytes(b"default shared audio")
    (root / "data" / "bgm").mkdir(parents=True)
    (root / "data" / "bgm" / "custom.mp3").write_bytes(b"custom audio")
    (root / "data" / "bgm" / "shared.mp3").write_bytes(b"custom shared audio")
    (root / "output" / "audio").mkdir(parents=True)
    (root / "output" / "audio" / "voice.wav").write_bytes(b"voice audio")
    (root / "config.yaml").write_text("key: value\n", encoding="utf-8")
    monkeypatch.setenv("PIXELLE_VIDEO_ROOT", str(root))

    # Files that exist relative to the working directory but outside the
    # project's BGM directories must not be picked up.
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    (cwd / "local.mp3").write_bytes(b"local audio")
    (cwd / "default.mp3").write_bytes(b"cwd default audio")
    monkeypatch.chdir(cwd)
    return root


@pytest.mark.parametrize(
    ("bgm_path", "expected"),
    [
        ("default.mp3", "bgm/default.mp3"),
        ("custom.mp3", "data/bgm/custom.mp3"),
        ("shared.mp3", "data/bgm/shared.mp3"),  # data/bgm/ before bgm/
        ("bgm/shared.mp3", "bgm/shared.mp3"),
        ("./bgm/default.mp3", "bgm/default.mp3"),
        ("data/bgm/custom.mp3", "data/bgm/custom.mp3"),
        ("output/audio/voice.wav", "output/audio/voice.wav"),
    ],
)
def test_resolves_names_and_paths_inside_bgm_roots(project, bgm_path, expected):
    assert VideoService()._resolve_bgm_path(bgm_path) == str((project / expected).resolve())


def test_accepts_absolute_path_inside_bgm_roots(project):
    target = (project / "data" / "bgm" / "custom.mp3").resolve()
    assert VideoService()._resolve_bgm_path(str(target)) == str(target)


@pytest.mark.parametrize(
    "bgm_path",
    [
        "../outer.mp3",
        "../../outer.mp3",
        "bgm/../../outer.mp3",
        "data/bgm/../../config.yaml",
        "output/../../outer.mp3",
        "bgm\\..\\..\\outer.mp3",
        "bgm/default.mp3\x00",
        "",
        "config.yaml",
        "local.mp3",  # exists in the working directory only
        "bgm",
        "output/audio",
        "missing.mp3",
    ],
)
def test_rejects_paths_outside_bgm_roots(project, bgm_path):
    with pytest.raises(FileNotFoundError):
        VideoService()._resolve_bgm_path(bgm_path)


def test_rejects_absolute_paths_outside_bgm_roots(project):
    service = VideoService()
    for target in (
        project.parent / "outer.mp3",
        project / "config.yaml",
        project.parent / "cwd" / "local.mp3",
        project / "bgm" / ".." / "config.yaml",
    ):
        with pytest.raises(FileNotFoundError):
            service._resolve_bgm_path(str(target))


def test_rejects_symlink_leaving_bgm_root(project):
    bgm = project / "bgm"
    try:
        (bgm / "link.mp3").symlink_to(project.parent / "outer.mp3")
        (bgm / "inside.mp3").symlink_to(bgm / "default.mp3")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    service = VideoService()
    with pytest.raises(FileNotFoundError):
        service._resolve_bgm_path("link.mp3")
    with pytest.raises(FileNotFoundError):
        service._resolve_bgm_path("bgm/link.mp3")
    assert service._resolve_bgm_path("inside.mp3") == str((bgm / "default.mp3").resolve())


def test_add_bgm_is_not_called_for_rejected_path(project, monkeypatch):
    calls = []
    service = VideoService()
    monkeypatch.setattr(service, "add_bgm", lambda **kwargs: calls.append(kwargs))

    with pytest.raises(FileNotFoundError):
        service._add_bgm_to_video(video="in.mp4", bgm_path="../outer.mp3", output="out.mp4")
    assert calls == []

    service._add_bgm_to_video(video="in.mp4", bgm_path="default.mp3", output="out.mp4")
    assert calls[0]["bgm"] == str((project / "bgm" / "default.mp3").resolve())
