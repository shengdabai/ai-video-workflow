"""moviepy 1.0.3 + Pillow >= 10: the ANTIALIAS shim in the module that imports moviepy.

moviepy 1.0.3 resizes frames with ``Image.ANTIALIAS``, which Pillow 10 removed.
``web/pipelines/action_transfer.py`` restores the alias before it imports
moviepy. The check runs in a fresh interpreter so that no other test has
already patched Pillow.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CHECK = """
from PIL import Image
assert not hasattr(Image, "ANTIALIAS"), "Pillow still has ANTIALIAS; shim not exercised"

import web.pipelines.action_transfer  # noqa: F401  (applies the shim, imports moviepy)

assert Image.ANTIALIAS == Image.LANCZOS

from moviepy.editor import ColorClip
from moviepy.video.fx.resize import resize

clip = resize(ColorClip(size=(8, 6), color=(255, 0, 0), duration=0.1), newsize=(4, 3))
frame = clip.get_frame(0)
assert frame.shape == (3, 4, 3), frame.shape
print("ok")
"""


def test_moviepy_resize_works_with_current_pillow():
    result = subprocess.run(
        [sys.executable, "-c", CHECK],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip().endswith("ok")
