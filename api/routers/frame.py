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
Frame/Template rendering endpoints
"""

import re
from pathlib import Path, PurePosixPath
from typing import Optional

from fastapi import APIRouter, HTTPException
from loguru import logger

from api.dependencies import PixelleVideoDep
from api.pathsafe import file_inside, split_relative_path
from api.schemas.frame import FrameRenderRequest, FrameRenderResponse, TemplateParamsResponse
from pixelle_video.services.frame_html import HTMLFrameGenerator
from pixelle_video.utils.os_util import get_pixelle_video_root_path
from pixelle_video.utils.template_util import parse_template_size, resolve_template_path

router = APIRouter(prefix="/frame", tags=["Frame Rendering"])

# Template keys are "<WIDTH>x<HEIGHT>/<name>.html" (or just "<name>.html" for
# the default size). The legacy "templates/..." and "data/templates/..."
# prefixes are accepted and removed first.
_TEMPLATE_ROOTS = ("data/templates", "templates")
_TEMPLATE_SIZE = re.compile(r"[0-9]+x[0-9]+")
_DEFAULT_TEMPLATE_SIZE = "1080x1920"
_TEMPLATE_NOT_FOUND = "Template not found"


def _resolve_template_file(template: Optional[str]) -> Optional[str]:
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
    for prefix in _TEMPLATE_ROOTS:
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

    try:
        candidate = resolve_template_path(f"{size}/{name}")
    except (FileNotFoundError, ValueError):
        return None
    project_root = Path(get_pixelle_video_root_path())
    if any(file_inside(candidate, project_root / root) for root in _TEMPLATE_ROOTS):
        # Keep the path as resolve_template_path built it: the generator
        # reads the size from its parent directory name.
        return candidate
    return None


def _template_file_or_404(template: Optional[str]) -> str:
    template_path = _resolve_template_file(template)
    if template_path is None:
        # Same answer for every rejected key; the key itself is not echoed.
        raise HTTPException(status_code=404, detail=_TEMPLATE_NOT_FOUND)
    return template_path


@router.post("/render", response_model=FrameRenderResponse)
async def render_frame(
    request: FrameRenderRequest,
    pixelle_video: PixelleVideoDep
):
    """
    Render a single frame using HTML template
    
    Generates a frame image by combining template, title, text, and image.
    This is useful for previewing templates or generating custom frames.
    
    - **template**: Template key (e.g., '1080x1920/default.html')
    - **title**: Optional title text
    - **text**: Frame text content
    - **image**: Image path (can be local path or URL)
    
    Returns path to generated frame image.
    
    Example:
    ```json
    {
        "template": "1080x1920/modern.html",
        "title": "Welcome",
        "text": "This is a beautiful frame with custom styling",
        "image": "resources/example.png"
    }
    ```
    """
    # Resolve the template inside templates/ or data/templates/ (404 otherwise)
    template_path = _template_file_or_404(request.template)

    try:
        logger.info(f"Frame render request: template={request.template}")
        
        # Parse template size
        width, height = parse_template_size(template_path)
        
        # Create HTML frame generator
        generator = HTMLFrameGenerator(template_path)
        
        # Generate frame
        frame_path = await generator.generate_frame(
            title=request.title,
            text=request.text,
            image=request.image
        )
        
        return FrameRenderResponse(
            frame_path=frame_path,
            width=width,
            height=height
        )
        
    except Exception as e:
        logger.error(f"Frame render error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/template/params", response_model=TemplateParamsResponse)
async def get_template_params(
    template: str
):
    """
    Get custom parameters for a template
    
    Returns the custom parameters defined in the template HTML file.
    These parameters can be passed via `template_params` in video generation requests.
    
    Template parameters are defined using syntax: `{{param_name:type=default}}`
    
    Supported types:
    - `text`: String input
    - `number`: Numeric input
    - `color`: Color picker (hex format)
    - `bool`: Boolean checkbox
    
    Example template syntax:
    ```html
    <div style="color: {{accent_color:color=#ff0000}}">
        {{custom_text:text=Hello World}}
    </div>
    ```
    
    Args:
        template: Template path (e.g., '1080x1920/image_default.html')
    
    Returns:
        Template parameters with their types, defaults, and labels
    
    Example response:
    ```json
    {
        "template": "1080x1920/image_default.html",
        "media_width": 1080,
        "media_height": 1440,
        "params": {
            "accent_color": {
                "type": "color",
                "default": "#ff0000",
                "label": "accent_color"
            },
            "background": {
                "type": "text", 
                "default": "https://example.com/bg.jpg",
                "label": "background"
            }
        }
    }
    ```
    """
    # Resolve the template inside templates/ or data/templates/ (404 otherwise)
    template_path = _template_file_or_404(template)

    try:
        logger.info(f"Get template params: {template}")
        
        # Create generator and parse parameters
        generator = HTMLFrameGenerator(template_path)
        params = generator.parse_template_parameters()
        media_width, media_height = generator.get_media_size()
        
        return TemplateParamsResponse(
            template=template,
            media_width=media_width,
            media_height=media_height,
            params=params
        )
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=_TEMPLATE_NOT_FOUND)
    except Exception as e:
        logger.error(f"Get template params error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

