"""The frame endpoints only accept template keys inside the template roots.

GET /api/frame/template/params?template=... and POST /api/frame/render take a
template key such as "1080x1920/image_default.html". The key is looked up in
data/templates/ and templates/; anything else answers 404 with a fixed body
that does not repeat the key.

`_get_as_is` builds the ASGI request by hand, so the query string reaches the
app exactly as written here and is percent-decoded once by the server, the
way uvicorn passes it on.
"""

import asyncio
from pathlib import Path
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

OUTER_MARKER = "outer-template-marker-91be"
APP_MARKER = "app-config-marker-3d07"

TEMPLATE_HTML = """<!DOCTYPE html>
<html><head>
<meta name="template:media-width" content="800">
<meta name="template:media-height" content="600">
</head><body style="color: {{accent_color:color=#123456}}">{{text}}</body></html>
"""
CUSTOM_HTML = """<!DOCTYPE html>
<html><body>{{custom_title:text=Custom}}{{text}}</body></html>
"""


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    """Project root with default and custom templates, plus files that must not be used."""
    monkeypatch.setenv("ORCHESTRATOR_DB_PATH", str(tmp_path / "orchestrator.db"))
    (tmp_path / "outer.html").write_text(
        f"<html>{{{{{OUTER_MARKER}=x}}}}</html>\n", encoding="utf-8"
    )

    app_dir = tmp_path / "app"
    portrait = app_dir / "templates" / "1080x1920"
    portrait.mkdir(parents=True)
    (portrait / "image_test.html").write_text(TEMPLATE_HTML, encoding="utf-8")
    (portrait / "notes.txt").write_text("not a template\n", encoding="utf-8")
    (portrait / "nested").mkdir()
    (portrait / "nested" / "image_test.html").write_text(TEMPLATE_HTML, encoding="utf-8")
    custom = app_dir / "data" / "templates" / "1920x1080"
    custom.mkdir(parents=True)
    (custom / "image_custom.html").write_text(CUSTOM_HTML, encoding="utf-8")
    # In the project root but outside both template roots.
    (app_dir / "config.html").write_text(
        f"<html>{{{{{APP_MARKER}=x}}}}</html>\n", encoding="utf-8"
    )

    monkeypatch.setenv("PIXELLE_VIDEO_ROOT", str(app_dir))
    monkeypatch.chdir(app_dir)
    return app_dir


async def _get_as_is(path: str, query: str) -> tuple[int, bytes]:
    """Send GET path?query to the app the way uvicorn would (no re-encoding)."""
    from api.app import app

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("ascii"),
        "root_path": "",
        "query_string": query.encode("ascii"),
        "headers": [(b"host", b"testserver")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    sent = []
    request_sent = False
    response_done = asyncio.Event()

    async def receive():
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await response_done.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            response_done.set()

    await app(scope, receive, send)
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    body = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, body


# Query-string values as sent on the wire; the server decodes them once.
REJECTED_KEYS = [
    # ".." segments after a size directory, after a legacy prefix, or alone
    "1080x1920/../../config.html",
    "1080x1920/../../../outer.html",
    "templates/../config.html",
    "data/templates/1920x1080/../../../config.html",
    "../outer.html",
    "x/../../../outer.html",
    # percent-encoded dots and separators
    "%2e%2e/%2e%2e/outer.html",
    "1080x1920%2f..%2f..%2fconfig.html",
    "1080x1920%2F%2E%2E%2F%2E%2E%2F%2E%2E%2Fouter.html",
    # backslash separators
    "1080x1920%5c..%5c..%5cconfig.html",
    "..%5c..%5couter.html",
    # double-encoded: decoded once this is a literal "%2e%2e" name, not ".."
    "%252e%252e/outer.html",
    # deep chain up to the filesystem root
    "%2e%2e%2f" * 40 + "etc%2fhosts",
    # absolute paths
    "%2Fetc%2Fhosts",
    "/etc/hosts",
    "C:%5CWindows%5Cwin.ini",
    "C:/Windows/win.ini",
    # NUL byte
    "1080x1920/image_test.html%00",
    "%00",
    # not a "<size>/<name>.html" template file
    "",
    "1080x1920",
    "1080x1920/",
    "templates",
    "1080x1920/notes.txt",
    "1080x1920/image_test",
    "1080x1920/nested/image_test.html",
    "portrait/image_test.html",
    "config.html",
    "1080x1920/missing.html",
]


def _assert_rejected(status: int, body: bytes) -> None:
    assert status == 404
    text = body.decode("utf-8", errors="replace")
    assert OUTER_MARKER not in text
    assert APP_MARKER not in text
    assert "localhost" not in text  # /etc/hosts content
    # Fixed body: the requested key is not repeated in the answer.
    assert text == '{"detail":"Template not found"}'


@pytest.mark.parametrize("raw", REJECTED_KEYS)
async def test_template_params_rejects_keys_outside_template_roots(app_dir, raw):
    status, body = await _get_as_is("/api/frame/template/params", "template=" + raw)
    _assert_rejected(status, body)


async def test_template_params_rejects_absolute_path_to_existing_file(app_dir):
    for target in (app_dir.parent / "outer.html", app_dir / "templates" / "1080x1920" / "image_test.html"):
        status, body = await _get_as_is(
            "/api/frame/template/params", "template=" + quote(str(target), safe="")
        )
        _assert_rejected(status, body)


def test_template_params_rejects_symlink_leaving_template_root(app_dir):
    portrait = app_dir / "templates" / "1080x1920"
    try:
        (portrait / "image_link.html").symlink_to(app_dir.parent / "outer.html")
        (portrait / "image_inside.html").symlink_to(portrait / "image_test.html")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available on this platform")

    from api.app import app

    with TestClient(app) as client:
        resp = client.get("/api/frame/template/params", params={"template": "1080x1920/image_link.html"})
        _assert_rejected(resp.status_code, resp.content)

        # A symlink that stays inside the template root still works.
        resp = client.get(
            "/api/frame/template/params", params={"template": "1080x1920/image_inside.html"}
        )
        assert resp.status_code == 200
        assert "accent_color" in resp.json()["params"]


@pytest.mark.parametrize(
    ("key", "media_size", "param"),
    [
        ("1080x1920/image_test.html", (800, 600), "accent_color"),
        ("image_test.html", (800, 600), "accent_color"),  # default size directory
        ("templates/1080x1920/image_test.html", (800, 600), "accent_color"),  # legacy prefix
        ("1080x1920/./image_test.html", (800, 600), "accent_color"),
        ("1920x1080/image_custom.html", (1024, 1024), "custom_title"),  # data/templates/
        ("data/templates/1920x1080/image_custom.html", (1024, 1024), "custom_title"),
    ],
)
def test_template_params_for_templates_inside_roots(app_dir, key, media_size, param):
    from api.app import app

    with TestClient(app) as client:
        resp = client.get("/api/frame/template/params", params={"template": key})
    assert resp.status_code == 200
    data = resp.json()
    assert data["template"] == key
    assert (data["media_width"], data["media_height"]) == media_size
    assert param in data["params"]


class _RecordingGenerator:
    """Stands in for HTMLFrameGenerator so no browser is started."""

    created: list[str] = []

    def __init__(self, template_path: str):
        type(self).created.append(template_path)

    async def generate_frame(self, title, text, image):
        return "output/frame.png"


@pytest.fixture
def render_client(app_dir, monkeypatch):
    import api.routers.frame as frame_routes
    from api.app import app
    from api.dependencies import get_pixelle_video

    _RecordingGenerator.created = []
    monkeypatch.setattr(frame_routes, "HTMLFrameGenerator", _RecordingGenerator)
    app.dependency_overrides[get_pixelle_video] = lambda: object()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_pixelle_video, None)


@pytest.mark.parametrize(
    "key",
    [
        "1080x1920/../../config.html",
        "../outer.html",
        "1080x1920\\..\\..\\config.html",
        "/etc/hosts",
        "C:\\Windows\\win.ini",
        "1080x1920/image_test.html\x00",
        "1080x1920/notes.txt",
        "1080x1920/missing.html",
        "",
    ],
)
def test_render_rejects_keys_outside_template_roots(render_client, key):
    resp = render_client.post("/api/frame/render", json={"template": key, "text": "hello"})
    _assert_rejected(resp.status_code, resp.content)
    assert _RecordingGenerator.created == []


def test_render_absolute_path_to_existing_file_is_rejected(render_client, app_dir):
    resp = render_client.post(
        "/api/frame/render",
        json={"template": str(app_dir.parent / "outer.html"), "text": "hello"},
    )
    _assert_rejected(resp.status_code, resp.content)
    assert _RecordingGenerator.created == []


def test_render_uses_template_inside_root(render_client, app_dir):
    resp = render_client.post(
        "/api/frame/render", json={"template": "1080x1920/image_test.html", "text": "hello"}
    )
    assert resp.status_code == 200
    assert resp.json()["frame_path"] == "output/frame.png"
    assert (resp.json()["width"], resp.json()["height"]) == (1080, 1920)
    expected = (app_dir / "templates" / "1080x1920" / "image_test.html").resolve()
    assert [Path(p).resolve() for p in _RecordingGenerator.created] == [expected]
