"""Caller-supplied text is escaped when frame templates are filled.

- ``title``, ``text`` and template parameters are HTML-escaped with
  ``html.escape(value, quote=True)``, so markup in them shows as text.
- ``image`` is a URL: the characters that could end a quoted attribute, a CSS
  string or a JS string are percent-encoded; ``&`` and ``%`` are kept.
- Defaults written in the template itself are inserted unchanged.

The render tests use the real templates and the real ``generate_frame`` path
with the browser stubbed: the stub reads the HTML page the generator writes and
navigates to, so the assertions check what Chromium would have loaded.
"""

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import pytest
from fastapi.testclient import TestClient

from pixelle_video.services.frame_html import HTMLFrameGenerator, fill_value

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = REPO_ROOT / "templates"

IMG_TITLE = '<img src="file:///etc/hosts">'
IMG_TITLE_ESCAPED = "&lt;img src=&quot;file:///etc/hosts&quot;&gt;"
SCRIPT_TEXT = "<script>document.title='x'</script> Tom & Jerry"
SCRIPT_TEXT_ESCAPED = (
    "&lt;script&gt;document.title=&#x27;x&#x27;&lt;/script&gt; Tom &amp; Jerry"
)


# ---------------------------------------------------------------- fill_value


@pytest.mark.parametrize(
    "value, expected",
    [
        (IMG_TITLE, IMG_TITLE_ESCAPED),
        (SCRIPT_TEXT, SCRIPT_TEXT_ESCAPED),
        ('say "hi"', "say &quot;hi&quot;"),
        ("it's", "it&#x27;s"),
        ("a & b", "a &amp; b"),
        ("&amp;", "&amp;amp;"),
        ("<iframe src=file:///etc/passwd></iframe>", "&lt;iframe src=file:///etc/passwd&gt;&lt;/iframe&gt;"),
        ("line one\nline two", "line one\nline two"),
        ("如何提高学习效率", "如何提高学习效率"),
    ],
)
def test_fill_value_html_escapes_text(value, expected):
    assert fill_value("title", value) == expected
    assert fill_value("text", value) == expected
    assert fill_value("author", value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        (None, ""),
        (True, "true"),
        (False, "false"),
        (3, "3"),
        (72.5, "72.5"),
        ("#764ba2", "#764ba2"),
    ],
)
def test_fill_value_plain_values(value, expected):
    assert fill_value("index", value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("https://example.com/a.png?x=1&y=2", "https://example.com/a.png?x=1&y=2"),
        ("file:///srv/app/output/a%20b.png", "file:///srv/app/output/a%20b.png"),
        ("data:image/png;base64,iVBORw0KGgo=", "data:image/png;base64,iVBORw0KGgo="),
        ('x" onerror="alert(1)', "x%22%20onerror=%22alert%281%29"),
        ('x");}</style><img src="file:///etc/hosts">', "x%22%29;}%3C/style%3E%3Cimg%20src=%22file:///etc/hosts%22%3E"),
        ("x';</script>", "x%27;%3C/script%3E"),
        ("a\\b`c", "a%5Cb%60c"),
        ("a\tb\nc", "a%09b%0Ac"),
        ("data:image/svg+xml,<svg/>", "data:image/svg+xml,%3Csvg/%3E"),
    ],
)
def test_fill_value_percent_encodes_image_urls(value, expected):
    assert fill_value("image", value) == expected


def test_template_defaults_and_markup_are_kept(tmp_path):
    template = tmp_path / "1080x1920" / "image_test.html"
    template.parent.mkdir()
    template.write_text(
        '<div class="t" style="color: {{accent:color=#ff0000}}">{{title}}</div>'
        "<p>{{signature=@Pixelle.AI}}</p><b>{{text}}</b>",
        encoding="utf-8",
    )
    generator = HTMLFrameGenerator(str(template))

    filled = generator._replace_parameters(
        generator.template, {"title": "<b>{{text}}</b>", "text": "a & b"}
    )

    assert filled == (
        '<div class="t" style="color: #ff0000">&lt;b&gt;{{text}}&lt;/b&gt;</div>'
        "<p>@Pixelle.AI</p><b>a &amp; b</b>"
    )


# ---------------------------------------------------------------- render path


class _StubPage:
    def __init__(self, pages: list):
        self._pages = pages

    async def goto(self, url, wait_until=None):
        assert url.startswith("file://")
        self._pages.append(Path(url2pathname(urlparse(url).path)).read_text(encoding="utf-8"))

    async def screenshot(self, path, type, omit_background):
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

    async def close(self):
        pass


class _StubBrowser:
    def __init__(self):
        self.pages: list[str] = []

    async def new_page(self, viewport, device_scale_factor):
        return _StubPage(self.pages)


@pytest.fixture
def browser(monkeypatch):
    stub = _StubBrowser()

    async def _ensure_browser(cls):
        return stub

    monkeypatch.setattr(HTMLFrameGenerator, "_ensure_browser", classmethod(_ensure_browser))
    return stub


@pytest.mark.parametrize(
    "template",
    [
        "1080x1920/image_default.html",
        "1080x1920/image_excerpt.html",
        "1080x1920/image_cartoon.html",
        "1080x1920/static_default.html",
        "1080x1920/asset_default.html",
    ],
)
async def test_render_writes_escaped_title_and_text(template, browser, tmp_path):
    template_path = TEMPLATES / template
    template_html = template_path.read_text(encoding="utf-8")
    generator = HTMLFrameGenerator(str(template_path))

    out = await generator.generate_frame(
        title=IMG_TITLE,
        text=SCRIPT_TEXT,
        image="https://example.com/a.png?x=1&y=2",
        ext={"index": 1},
        output_path=str(tmp_path / "frames" / "frame.png"),
    )

    assert Path(out).read_bytes().startswith(b"\x89PNG")
    [page] = browser.pages
    assert IMG_TITLE_ESCAPED in page
    assert SCRIPT_TEXT_ESCAPED in page
    assert IMG_TITLE not in page
    assert "file:///etc/hosts\">" not in page
    assert "<script>document.title" not in page
    # No <img> or <script> tag came from the input: the counts match the template's own.
    assert page.count("<img") == template_html.count("<img")
    assert page.count("<script") == template_html.count("<script")


async def test_render_keeps_image_url_and_typed_params(browser, tmp_path):
    generator = HTMLFrameGenerator(str(TEMPLATES / "1080x1920" / "image_modern.html"))

    await generator.generate_frame(
        title="Title",
        text="Text",
        image='https://example.com/a.png?x=1&y=2"); } </style><img src="file:///etc/hosts">',
        ext={"index": 2, "accent_color": "#123456", "title_font_size": 64},
        output_path=str(tmp_path / "frame.png"),
    )

    [page] = browser.pages
    assert "background: #123456;" in page
    assert "font-size: 64px;" in page
    assert "https://example.com/a.png?x=1&y=2%22%29;%20}%20%3C/style%3E%3Cimg" in page
    assert page.count("</style>") == 1
    assert '<img src="file:///etc/hosts">' not in page


# ---------------------------------------------------------------- API render

TEMPLATE_HTML = """<!DOCTYPE html>
<html><head>
<meta name="template:media-width" content="800">
<meta name="template:media-height" content="600">
<style>.bg { background-image: url("{{image}}"); }</style>
</head><body><div class="bg"></div><h1 title="{{title}}">{{title}}</h1><p>{{text}}</p></body></html>
"""


@pytest.fixture
def client(tmp_path, monkeypatch, browser):
    monkeypatch.setenv("ORCHESTRATOR_DB_PATH", str(tmp_path / "orchestrator.db"))
    app_dir = tmp_path / "app"
    portrait = app_dir / "templates" / "1080x1920"
    portrait.mkdir(parents=True)
    (portrait / "image_test.html").write_text(TEMPLATE_HTML, encoding="utf-8")
    (app_dir / "output").mkdir()
    monkeypatch.setenv("PIXELLE_VIDEO_ROOT", str(app_dir))
    monkeypatch.chdir(app_dir)

    from api.app import app

    with TestClient(app) as c:
        yield c


def test_api_render_escapes_title_text_and_image(client, browser):
    response = client.post(
        "/api/frame/render",
        json={
            "template": "1080x1920/image_test.html",
            "title": IMG_TITLE,
            "text": SCRIPT_TEXT,
            "image": 'data:image/png,"); }</style><img src="file:///etc/hosts">',
        },
    )

    assert response.status_code == 200, response.text
    assert Path(response.json()["frame_path"]).name.startswith("frame_")
    [page] = browser.pages
    assert f'<h1 title="{IMG_TITLE_ESCAPED}">{IMG_TITLE_ESCAPED}</h1>' in page
    assert f"<p>{SCRIPT_TEXT_ESCAPED}</p>" in page
    assert 'url("data:image/png,%22%29;%20}%3C/style%3E%3Cimg%20src=%22file:///etc/hosts%22%3E")' in page
    assert "<img" not in page
    assert "<script" not in page
