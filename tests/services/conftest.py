"""Shared stub for the Playwright browser used by HTMLFrameGenerator.

The stub records the HTML page that ``generate_frame`` asks Chromium to load
and writes a PNG signature as the screenshot, so render tests run without a
browser.
"""

from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import pytest

from pixelle_video.services.frame_html import HTMLFrameGenerator


class StubPage:
    def __init__(self, pages: list):
        self._pages = pages

    async def goto(self, url, wait_until=None):
        assert url.startswith("file://")
        self._pages.append(Path(url2pathname(urlparse(url).path)).read_text(encoding="utf-8"))

    async def screenshot(self, path, type, omit_background):
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")

    async def close(self):
        pass


class StubBrowser:
    def __init__(self):
        self.pages: list[str] = []

    async def new_page(self, viewport, device_scale_factor):
        return StubPage(self.pages)


@pytest.fixture
def browser(monkeypatch):
    stub = StubBrowser()

    async def _ensure_browser(cls):
        return stub

    monkeypatch.setattr(HTMLFrameGenerator, "_ensure_browser", classmethod(_ensure_browser))
    return stub
