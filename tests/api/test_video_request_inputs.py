"""The video generation endpoints check file inputs before any work starts.

POST /api/video/generate/sync and /api/video/generate/async take a
frame_template key such as "1080x1920/image_default.html". The key is looked
up in data/templates/ and templates/ with the same rules as the frame
endpoints; anything else answers 404 with a fixed body, before a task is
created or the pipeline is called. The pipeline is replaced by a stub that
records its keyword arguments.
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
