"""The video generation endpoints check file inputs before any work starts.

POST /api/video/generate/sync and /api/video/generate/async take a
frame_template key such as "1080x1920/image_default.html". The key is looked
up in data/templates/ and templates/ with the same rules as the frame
endpoints; anything else answers 404 with a fixed body. bgm_path must name an
audio file in bgm/, data/bgm/ or output/, as for the orchestrator publish
route; anything else answers 400. Both checks run before a task is created or
the pipeline is called. The pipeline is replaced by a stub that records its
keyword arguments.
"""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

OUTER_MARKER = "outer-template-marker-5c21"

TEMPLATE_HTML = """<!DOCTYPE html>
<html><head>
<meta name="template:media-width" content="800">
<meta name="template:media-height" content="600">
</head><body>{{text}}</body></html>
"""
TEMPLATE_NOT_FOUND = {"detail": "Template not found"}
BGM_ERROR = {"detail": "bgm_path must name an audio file in bgm/, data/bgm/ or output/"}


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    """Project root with default and custom templates, plus files that must not be used."""
    monkeypatch.setenv("ORCHESTRATOR_DB_PATH", str(tmp_path / "orchestrator.db"))
    (tmp_path / "outer.html").write_text(
        f'<html><head><meta name="template:media-width" content="1"></head>{OUTER_MARKER}</html>\n',
        encoding="utf-8",
    )

    app_dir = tmp_path / "app"
    portrait = app_dir / "templates" / "1080x1920"
    portrait.mkdir(parents=True)
    (portrait / "image_test.html").write_text(TEMPLATE_HTML, encoding="utf-8")
    (portrait / "notes.txt").write_text("not a template\n", encoding="utf-8")
    custom = app_dir / "data" / "templates" / "1920x1080"
    custom.mkdir(parents=True)
    (custom / "image_custom.html").write_text(TEMPLATE_HTML, encoding="utf-8")
    (app_dir / "config.html").write_text(TEMPLATE_HTML, encoding="utf-8")

    (tmp_path / "outer.mp3").write_bytes(b"outer audio")
    (app_dir / "bgm").mkdir()
    (app_dir / "bgm" / "default.mp3").write_bytes(b"default audio")
    (app_dir / "bgm" / "shared.mp3").write_bytes(b"default shared audio")
    (app_dir / "data" / "bgm").mkdir()
    (app_dir / "data" / "bgm" / "custom.mp3").write_bytes(b"custom audio")
    (app_dir / "data" / "bgm" / "shared.mp3").write_bytes(b"custom shared audio")
    (app_dir / "output" / "audio").mkdir(parents=True)
    (app_dir / "output" / "audio" / "voice.wav").write_bytes(b"voice audio")
    (app_dir / "output" / "notes.txt").write_text("not audio\n", encoding="utf-8")
    (app_dir / "config.yaml").write_text("key: value\n", encoding="utf-8")

    monkeypatch.setenv("PIXELLE_VIDEO_ROOT", str(app_dir))
    monkeypatch.chdir(app_dir)
    return app_dir


class _RecordingCore:
    """Stands in for PixelleVideoCore; records generate_video calls."""

    def __init__(self):
        self.calls: list[dict] = []

    async def generate_video(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(video_path="output/task/final.mp4", duration=1.5)


@pytest.fixture
async def core(app_dir):
    from api.app import app
    from api.dependencies import get_pixelle_video

    recording = _RecordingCore()
    app.dependency_overrides[get_pixelle_video] = lambda: recording
    try:
        yield recording
    finally:
        app.dependency_overrides.pop(get_pixelle_video, None)


@pytest.fixture
async def client(core):
    from api.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _generate(client, mode: str, **fields):
    body = {"text": "hello", "frame_template": "1080x1920/image_test.html"}
    body.update(fields)
    return await client.post(f"/api/video/generate/{mode}", json=body)


async def _finish_async(resp) -> None:
    """Wait for the background task that /generate/async started."""
    from api.tasks import task_manager

    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    await task_manager._task_futures[task_id]


def _task_count() -> int:
    from api.tasks import task_manager

    return len(task_manager._tasks)


REJECTED_TEMPLATES = [
    "1080x1920/../../config.html",
    "1080x1920/../../../outer.html",
    "../outer.html",
    "templates/../config.html",
    "data/templates/1920x1080/../../../config.html",
    "1080x1920\\..\\..\\config.html",
    "..\\outer.html",
    "/etc/hosts",
    "C:\\Windows\\win.ini",
    "C:/Windows/win.ini",
    "1080x1920/image_test.html\x00",
    "1080x1920/notes.txt",
    "1080x1920/missing.html",
    "portrait/image_test.html",
    "config.html",
]


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("frame_template", REJECTED_TEMPLATES)
async def test_generate_rejects_templates_outside_roots(client, core, mode, frame_template):
    tasks_before = _task_count()
    resp = await _generate(client, mode, frame_template=frame_template)
    assert resp.status_code == 404
    assert resp.json() == TEMPLATE_NOT_FOUND
    assert OUTER_MARKER not in resp.text
    assert core.calls == []
    assert _task_count() == tasks_before


@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_generate_rejects_absolute_template_paths(client, core, app_dir, mode):
    for target in (app_dir.parent / "outer.html", app_dir / "templates" / "1080x1920" / "image_test.html"):
        resp = await _generate(client, mode, frame_template=str(target))
        assert resp.status_code == 404
        assert resp.json() == TEMPLATE_NOT_FOUND
    assert core.calls == []


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize(
    ("frame_template", "key"),
    [
        ("1080x1920/image_test.html", "1080x1920/image_test.html"),
        ("image_test.html", "1080x1920/image_test.html"),  # default size directory
        ("templates/1080x1920/image_test.html", "1080x1920/image_test.html"),  # legacy prefix
        ("1080x1920/./image_test.html", "1080x1920/image_test.html"),
        ("1920x1080/image_custom.html", "1920x1080/image_custom.html"),  # data/templates/
        ("data/templates/1920x1080/image_custom.html", "1920x1080/image_custom.html"),
    ],
)
async def test_generate_passes_normalized_template_key(client, core, mode, frame_template, key):
    resp = await _generate(client, mode, frame_template=frame_template)
    if mode == "async":
        await _finish_async(resp)
    else:
        assert resp.status_code == 200, resp.text
        assert resp.json()["video_url"] == "http://test/api/files/task/final.mp4"
    assert len(core.calls) == 1
    assert core.calls[0]["frame_template"] == key
    assert (core.calls[0]["media_width"], core.calls[0]["media_height"]) == (800, 600)


async def test_generate_sync_without_template_still_reports_missing_template(client, core):
    resp = await client.post("/api/video/generate/sync", json={"text": "hello"})
    assert resp.status_code == 500
    assert "frame_template is required" in resp.json()["detail"]
    assert core.calls == []


REJECTED_BGM = [
    "../outer.mp3",
    "bgm/../../outer.mp3",
    "data/bgm/../../../outer.mp3",
    "output/../../outer.mp3",
    "bgm\\..\\..\\outer.mp3",
    "/etc/hosts",
    "C:\\Windows\\win.ini",
    "bgm/default.mp3\x00",
    "http://example.com/a.mp3",
    "file:bgm/default.mp3",
    "config.yaml",
    "output/notes.txt",
    "bgm",
    "bgm/missing.mp3",
    "missing.mp3",
]


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize("bgm_path", REJECTED_BGM)
async def test_generate_rejects_bgm_outside_roots(client, core, mode, bgm_path):
    tasks_before = _task_count()
    resp = await _generate(client, mode, bgm_path=bgm_path)
    assert resp.status_code == 400
    assert resp.json() == BGM_ERROR
    assert core.calls == []
    assert _task_count() == tasks_before


@pytest.mark.parametrize("mode", ["sync", "async"])
async def test_generate_rejects_absolute_bgm_paths(client, core, app_dir, mode):
    # Absolute paths are rejected even when they point inside a root.
    for target in (app_dir.parent / "outer.mp3", app_dir / "bgm" / "default.mp3"):
        resp = await _generate(client, mode, bgm_path=str(target))
        assert resp.status_code == 400
        assert resp.json() == BGM_ERROR
    assert core.calls == []


def _symlinks(app_dir) -> None:
    bgm = app_dir / "bgm"
    try:
        (bgm / "link.mp3").symlink_to(app_dir.parent / "outer.mp3")
        (bgm / "inside.mp3").symlink_to(bgm / "default.mp3")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")


async def test_generate_rejects_bgm_symlink_leaving_root(client, core, app_dir):
    _symlinks(app_dir)
    resp = await _generate(client, "sync", bgm_path="bgm/link.mp3")
    assert resp.status_code == 400
    assert resp.json() == BGM_ERROR
    assert core.calls == []

    # A symlink that stays inside the root is accepted.
    resp = await _generate(client, "sync", bgm_path="bgm/inside.mp3")
    assert resp.status_code == 200
    assert core.calls[0]["bgm_path"] == str((app_dir / "bgm" / "default.mp3").resolve())


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize(
    ("bgm_path", "expected"),
    [
        ("bgm/default.mp3", "bgm/default.mp3"),
        ("./bgm/default.mp3", "bgm/default.mp3"),
        ("default.mp3", "bgm/default.mp3"),
        ("data/bgm/custom.mp3", "data/bgm/custom.mp3"),
        ("custom.mp3", "data/bgm/custom.mp3"),
        ("shared.mp3", "data/bgm/shared.mp3"),  # data/bgm/ before bgm/
        ("bgm/shared.mp3", "bgm/shared.mp3"),
        ("output/audio/voice.wav", "output/audio/voice.wav"),
    ],
)
async def test_generate_passes_resolved_bgm(client, core, app_dir, mode, bgm_path, expected):
    resp = await _generate(client, mode, bgm_path=bgm_path)
    if mode == "async":
        await _finish_async(resp)
    else:
        assert resp.status_code == 200, resp.text
    assert len(core.calls) == 1
    assert core.calls[0]["bgm_path"] == str((app_dir / expected).resolve())


@pytest.mark.parametrize("bgm_path", [None, ""])
async def test_generate_without_bgm(client, core, bgm_path):
    resp = await _generate(client, "sync", bgm_path=bgm_path)
    assert resp.status_code == 200, resp.text
    assert core.calls[0]["bgm_path"] is None
