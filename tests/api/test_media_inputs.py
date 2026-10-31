"""Media fields that may name local files only accept files inside output/, data/ or resources/.

- POST /api/frame/render: ``image`` is an http(s) URL, a data:image/ URI, or
  an image or video file in output/, data/ or resources/.
- POST /api/tts/synthesize: ``ref_audio`` is an http(s) URL or an audio file
  in output/, data/ or resources/ (a ComfyUI TTS workflow uploads a local
  file to the ComfyUI server).

Other values answer 400 with a fixed body before the generator or the TTS
service is called. Accepted local paths are passed on resolved.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

IMAGE_ERROR = {
    "detail": "image must be an http(s) URL, a data:image/ URI, or an image or video file "
    "in output/, data/ or resources/"
}
REF_AUDIO_ERROR = {
    "detail": "ref_audio must be an http(s) URL or an audio file in output/, data/ or resources/"
}

TEMPLATE_HTML = """<!DOCTYPE html>
<html><head>
<meta name="template:media-width" content="800">
<meta name="template:media-height" content="600">
</head><body><img src="{{image}}">{{text}}</body></html>
"""


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_DB_PATH", str(tmp_path / "orchestrator.db"))
    (tmp_path / "outer.png").write_bytes(b"outer image")
    (tmp_path / "outer.wav").write_bytes(b"outer audio")

    app_dir = tmp_path / "app"
    portrait = app_dir / "templates" / "1080x1920"
    portrait.mkdir(parents=True)
    (portrait / "image_test.html").write_text(TEMPLATE_HTML, encoding="utf-8")
    (app_dir / "output" / "frames").mkdir(parents=True)
    (app_dir / "output" / "frames" / "a.png").write_bytes(b"png")
    (app_dir / "output" / "clips").mkdir()
    (app_dir / "output" / "clips" / "0.mp4").write_bytes(b"clip")
    (app_dir / "output" / "ref").mkdir()
    (app_dir / "output" / "ref" / "voice.wav").write_bytes(b"voice")
    (app_dir / "output" / "notes.txt").write_text("not media\n", encoding="utf-8")
    (app_dir / "data" / "images").mkdir(parents=True)
    (app_dir / "data" / "images" / "b.jpg").write_bytes(b"jpg")
    (app_dir / "data" / "orchestrator.db").write_bytes(b"SQLite format 3\x00")
    (app_dir / "resources").mkdir()
    (app_dir / "resources" / "example.png").write_bytes(b"png")
    (app_dir / "config.png").write_bytes(b"png outside the roots")
    (app_dir / "config.yaml").write_text("key: value\n", encoding="utf-8")

    monkeypatch.setenv("PIXELLE_VIDEO_ROOT", str(app_dir))
    monkeypatch.chdir(app_dir)
    return app_dir


class _RecordingGenerator:
    """Stands in for HTMLFrameGenerator so no browser is started."""

    images: list = []

    def __init__(self, template_path: str):
        pass

    async def generate_frame(self, title, text, image):
        type(self).images.append(image)
        return "output/frame.png"


class _RecordingCore:
    def __init__(self):
        self.tts_calls: list[dict] = []

    async def tts(self, **kwargs):
        self.tts_calls.append(kwargs)
        return "output/speech.mp3"


@pytest.fixture
def core():
    return _RecordingCore()


@pytest.fixture
def client(app_dir, core, monkeypatch):
    import api.routers.frame as frame_routes
    import api.routers.tts as tts_routes
    from api.app import app
    from api.dependencies import get_pixelle_video

    _RecordingGenerator.images = []
    monkeypatch.setattr(frame_routes, "HTMLFrameGenerator", _RecordingGenerator)
    monkeypatch.setattr(tts_routes, "get_audio_duration", lambda path: 1.25)
    app.dependency_overrides[get_pixelle_video] = lambda: core
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_pixelle_video, None)


def _render(client, image):
    body = {"template": "1080x1920/image_test.html", "text": "hello"}
    if image is not ...:
        body["image"] = image
    return client.post("/api/frame/render", json=body)


def _symlinks(app_dir) -> None:
    try:
        (app_dir / "output" / "link.png").symlink_to(app_dir.parent / "outer.png")
        (app_dir / "output" / "link.wav").symlink_to(app_dir.parent / "outer.wav")
        (app_dir / "output" / "inside.png").symlink_to(app_dir / "output" / "frames" / "a.png")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")


# ---------------------------------------------------------------- frame image

REJECTED_IMAGES = [
    "../outer.png",
    "output/../../outer.png",
    "output\\..\\..\\outer.png",
    "/etc/hosts",
    "C:\\Windows\\win.ini",
    "file:///etc/hosts",
    "file:output/frames/a.png",
    "javascript:alert(1)",
    "data:text/html,<p>x</p>",
    "output/frames/a.png\x00",
    "config.png",  # inside the project root, outside output/, data/, resources/
    "templates/1080x1920/image_test.html",
    "output/notes.txt",
    "data/orchestrator.db",
    "output/missing.png",
    "output",
    "output/frames",
]


@pytest.mark.parametrize("image", REJECTED_IMAGES)
def test_render_rejects_images_outside_media_roots(client, image):
    resp = _render(client, image)
    assert resp.status_code == 400
    assert resp.json() == IMAGE_ERROR
    assert _RecordingGenerator.images == []


def test_render_rejects_absolute_image_outside_media_roots(client, app_dir):
    for target in (app_dir.parent / "outer.png", app_dir / "config.png"):
        resp = _render(client, str(target))
        assert resp.status_code == 400
        assert resp.json() == IMAGE_ERROR
    assert _RecordingGenerator.images == []


def test_render_rejects_image_symlink_leaving_root(client, app_dir):
    _symlinks(app_dir)
    resp = _render(client, "output/link.png")
    assert resp.status_code == 400
    assert resp.json() == IMAGE_ERROR
    assert _RecordingGenerator.images == []

    resp = _render(client, "output/inside.png")
    assert resp.status_code == 200
    assert _RecordingGenerator.images == [str((app_dir / "output" / "frames" / "a.png").resolve())]


@pytest.mark.parametrize(
    "image",
    [
        "output/frames/a.png",
        "./output/frames/a.png",
        "output/clips/0.mp4",
        "data/images/b.jpg",
        "resources/example.png",
    ],
)
def test_render_passes_resolved_local_image(client, app_dir, image):
    resp = _render(client, image)
    assert resp.status_code == 200, resp.text
    assert _RecordingGenerator.images == [str((app_dir / Path(image)).resolve())]


def test_render_accepts_absolute_image_inside_media_roots(client, app_dir):
    target = (app_dir / "output" / "frames" / "a.png").resolve()
    resp = _render(client, str(target))
    assert resp.status_code == 200
    assert _RecordingGenerator.images == [str(target)]


@pytest.mark.parametrize(
    "image",
    [
        "http://example.com/a.png",
        "https://example.com/a.png?x=1",
        "data:image/png;base64,iVBORw0KGgo=",
        "",
        None,
        ...,
    ],
)
def test_render_passes_urls_and_empty_image_unchanged(client, image):
    resp = _render(client, image)
    assert resp.status_code == 200, resp.text
    assert _RecordingGenerator.images == [None if image is ... else image]


# ---------------------------------------------------------------- TTS ref_audio

def _synthesize(client, ref_audio):
    body = {"text": "hello", "workflow": "selfhost/tts_index2.json"}
    if ref_audio is not ...:
        body["ref_audio"] = ref_audio
    return client.post("/api/tts/synthesize", json=body)


REJECTED_REF_AUDIO = [
    "../outer.wav",
    "output/../../outer.wav",
    "output\\..\\..\\outer.wav",
    "/etc/hosts",
    "C:\\Windows\\win.ini",
    "file:///etc/hosts",
    "output/ref/voice.wav\x00",
    "config.yaml",
    "output/notes.txt",
    "data/orchestrator.db",
    "output/frames/a.png",
    "output/ref/missing.wav",
    "output/ref",
]


@pytest.mark.parametrize("ref_audio", REJECTED_REF_AUDIO)
def test_tts_rejects_ref_audio_outside_media_roots(client, core, ref_audio):
    resp = _synthesize(client, ref_audio)
    assert resp.status_code == 400
    assert resp.json() == REF_AUDIO_ERROR
    assert core.tts_calls == []


def test_tts_rejects_absolute_and_symlinked_ref_audio_outside_roots(client, core, app_dir):
    _symlinks(app_dir)
    for value in (str(app_dir.parent / "outer.wav"), str(app_dir / "config.yaml"), "output/link.wav"):
        resp = _synthesize(client, value)
        assert resp.status_code == 400
        assert resp.json() == REF_AUDIO_ERROR
    assert core.tts_calls == []


@pytest.mark.parametrize(
    ("ref_audio", "expected"),
    [
        ("output/ref/voice.wav", "resolved"),
        (None, "absent"),
        ("", "absent"),
        (..., "absent"),
        ("https://example.com/voice.wav", "unchanged"),
    ],
)
def test_tts_passes_checked_ref_audio(client, core, app_dir, ref_audio, expected):
    resp = _synthesize(client, ref_audio)
    assert resp.status_code == 200, resp.text
    assert resp.json()["audio_path"] == "output/speech.mp3"
    (call,) = core.tts_calls
    assert call["workflow"] == "selfhost/tts_index2.json"
    if expected == "resolved":
        assert call["ref_audio"] == str((app_dir / "output" / "ref" / "voice.wav").resolve())
    elif expected == "unchanged":
        assert call["ref_audio"] == ref_audio
    else:
        assert "ref_audio" not in call


def test_tts_accepts_absolute_ref_audio_inside_media_roots(client, core, app_dir):
    target = (app_dir / "output" / "ref" / "voice.wav").resolve()
    resp = _synthesize(client, str(target))
    assert resp.status_code == 200
    assert core.tts_calls[0]["ref_audio"] == str(target)
