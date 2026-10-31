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
Resolve user-supplied relative paths inside fixed root directories.

The API routers receive file names and relative paths from clients (request
paths, query parameters, JSON fields). They use these helpers so that every
such input is looked up the same way: split into segments, then resolved
against one configured root, and accepted only when the result is a regular
file inside that root.
"""

from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional, Union


def split_relative_path(user_path: Optional[str]) -> Optional[tuple[str, ...]]:
    """
    Split a user-supplied relative path into its segments.

    Backslashes count as separators. "." segments are dropped. The input is
    not percent-decoded. Returns None when the input is empty, contains a NUL
    byte, is absolute (POSIX or Windows form), or contains a ".." segment.
    """
    if not user_path or "\x00" in user_path:
        return None
    if PurePosixPath(user_path).is_absolute() or PureWindowsPath(user_path).is_absolute():
        return None
    parts = PurePosixPath(user_path.replace("\\", "/")).parts
    if not parts or ".." in parts:
        return None
    return parts


def resolve_file_inside(root: Union[str, Path], *parts: str) -> Optional[Path]:
    """
    Join ``parts`` onto ``root`` and return the result if it stays inside root.

    Both paths are resolved first (symlinks are followed); a relative root is
    resolved against the current working directory. Returns the resolved path
    only when it is a regular file strictly inside the resolved root; returns
    None otherwise, also when the path cannot be resolved.
    """
    try:
        root_resolved = Path(root).resolve()
        resolved = Path(root_resolved, *parts).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    return _regular_file_inside(resolved, root_resolved)


def file_inside(path: Union[str, Path], root: Union[str, Path]) -> Optional[Path]:
    """
    Return ``path`` resolved if it is a regular file strictly inside ``root``.

    For a path that some other function already built, for example from a
    lookup table. Symlinks are followed and relative paths are resolved
    against the current working directory, as in ``resolve_file_inside``.
    """
    try:
        root_resolved = Path(root).resolve()
        resolved = Path(path).resolve()
    except (OSError, RuntimeError, ValueError):
        return None
    return _regular_file_inside(resolved, root_resolved)


# A request's bgm_path names an audio file in one of these directories
# (relative to the working directory, like the files API). "bgm/<name>",
# "data/bgm/<name>" and "output/<path>" name the directory; any other relative
# path, such as a bare "<name>", is looked up in data/bgm/ first, then bgm/,
# the same order the video pipeline uses.
BGM_ROOTS = ("data/bgm", "bgm", "output")
BGM_SEARCH_ROOTS = ("data/bgm", "bgm")
BGM_SUFFIXES = (".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac")
BGM_PATH_ERROR = "bgm_path must name an audio file in bgm/, data/bgm/ or output/"


def resolve_bgm_file(bgm_path: Optional[str]) -> Optional[Path]:
    """
    Map a request's bgm_path to an audio file inside the BGM/output roots.

    Uses the same rules as the files API: no NUL byte, no absolute path, no
    ".." segment, and the resolved file (symlinks followed) must be a regular
    file inside its root with an audio suffix. Returns None for anything else.
    """
    parts = split_relative_path(bgm_path)
    if parts is None:
        return None
    resolved = None
    for root in BGM_ROOTS:
        root_parts = tuple(root.split("/"))
        if len(parts) > len(root_parts) and parts[: len(root_parts)] == root_parts:
            resolved = resolve_file_inside(root, *parts[len(root_parts):])
            break
    else:
        for root in BGM_SEARCH_ROOTS:
            resolved = resolve_file_inside(root, *parts)
            if resolved is not None:
                break
    if resolved is None or resolved.suffix.lower() not in BGM_SUFFIXES:
        return None
    return resolved


def _regular_file_inside(resolved: Path, root_resolved: Path) -> Optional[Path]:
    if resolved == root_resolved or not resolved.is_relative_to(root_resolved):
        return None
    if not resolved.is_file():
        return None
    return resolved
