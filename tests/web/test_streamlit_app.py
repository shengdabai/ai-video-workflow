"""Smoke tests for the Streamlit web UI.

They run the real page scripts with Streamlit's AppTest harness (no browser,
no server), so a Streamlit or Pillow upgrade that breaks page rendering fails
here instead of only at runtime.
"""

from pathlib import Path

import pytest

pytest.importorskip("streamlit.testing.v1")
from streamlit.testing.v1 import AppTest  # noqa: E402

# AppTest resolves relative paths against the calling file, so pass an
# absolute path to the entry point.
APP_PATH = Path(__file__).resolve().parents[2] / "web" / "app.py"


def _run_app() -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    at.run()
    return at


def test_home_page_renders_without_exception():
    at = _run_app()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Pixelle-Video" in m.value for m in at.markdown)
    assert len(at.button) > 0


def test_history_page_renders_without_exception():
    at = _run_app()
    at.switch_page("pages/2_📚_History.py")
    at.run()
    assert not at.exception, [e.value for e in at.exception]
