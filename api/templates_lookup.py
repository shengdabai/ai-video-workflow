# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Map a template key from a request to a template file inside the template roots.

Used by the frame endpoints and the video generation endpoints, so that every
request that names a frame template is checked the same way.
"""

import re
from pathlib import Path, PurePosixPath
from typing import NamedTuple, Optional

from fastapi import HTTPException

from api.pathsafe import file_inside, split_relative_path
from pixelle_video.utils.os_util import get_pixelle_video_root_path
from pixelle_video.utils.template_util import resolve_template_path

# Template keys are "<WIDTH>x<HEIGHT>/<name>.html" (or just "<name>.html" for
# the default size). The legacy "templates/..." and "data/templates/..."
# prefixes are accepted and removed first.
TEMPLATE_ROOTS = ("data/templates", "templates")
TEMPLATE_NOT_FOUND = "Template not found"
_TEMPLATE_SIZE = re.compile(r"[0-9]+x[0-9]+")
_DEFAULT_TEMPLATE_SIZE = "1080x1920"


class TemplateFile(NamedTuple):
    """A template key that names a template file inside the template roots."""

    key: str
    """Normalized key, always "<size>/<name>.html"."""
    path: str
    """The file path as ``resolve_template_path`` built it."""


def resolve_template_file(template: Optional[str]) -> Optional[TemplateFile]:
    """
    Map a template key from a request to a template file inside the template roots.

    The key is split into segments with the same rules as the files API
    (no NUL byte, no absolute path, no ".." segment). What remains must be
    exactly a size directory and an ``.html`` file name. The file is then
    looked up with ``resolve_template_path`` (custom templates in
    data/templates/ take priority over templates/), and the result is accepted
    only when it is a regular file inside one of the template roots.
    Returns None for anything else.
    """
    parts = split_relative_path(template)
    if parts is None:
        return None
    for prefix in TEMPLATE_ROOTS:
        prefix_parts = tuple(prefix.split("/"))
        if parts[: len(prefix_parts)] == prefix_parts:
            parts = parts[len(prefix_parts):]
            break
    if len(parts) == 1:
        parts = (_DEFAULT_TEMPLATE_SIZE, parts[0])
    if len(parts) != 2:
        return None
    size, name = parts
    if not _TEMPLATE_SIZE.fullmatch(size) or PurePosixPath(name).suffix.lower() != ".html":
        return None

    key = f"{size}/{name}"
    try:
        candidate = resolve_template_path(key)
    except (FileNotFoundError, ValueError):
        return None
    project_root = Path(get_pixelle_video_root_path())
    if any(file_inside(candidate, project_root / root) for root in TEMPLATE_ROOTS):
        # Keep the path as resolve_template_path built it: the generator
        # reads the size from its parent directory name.
        return TemplateFile(key=key, path=candidate)
    return None


def template_file_or_404(template: Optional[str]) -> TemplateFile:
    """Like ``resolve_template_file``, but answer 404 for a rejected key."""
    template_file = resolve_template_file(template)
    if template_file is None:
        # Same answer for every rejected key; the key itself is not echoed.
        raise HTTPException(status_code=404, detail=TEMPLATE_NOT_FOUND)
    return template_file
