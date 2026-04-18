from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime


def _now() -> str:
    return datetime.utcnow().isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


class VideoTask(BaseModel):
    id: str = Field(default_factory=_uid)
    title: str
    script: str
    style_pack_id: Optional[str] = None
    character_pack_id: Optional[str] = None
    status: str = "pending"  # pending|processing|review|approved|published|failed
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class ShotTask(BaseModel):
    id: str = Field(default_factory=_uid)
    video_task_id: str
    shot_index: int
    prompt: str
    duration: float = 5.0
    aspect_ratio: str = "9:16"
    status: str = "pending"  # pending|generating|failed|review_pending|approved|rejected
    retry_count: int = 0
    provider: str = "pixverse"
    provider_job_id: Optional[str] = None
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class Asset(BaseModel):
    id: str = Field(default_factory=_uid)
    task_id: Optional[str] = None
    shot_id: Optional[str] = None
    type: str  # video_clip|image|audio|subtitle|cover|export
    file_path: str
    file_size: int = 0
    meta: str = "{}"  # JSON string
    created_at: str = Field(default_factory=_now)


class Pack(BaseModel):
    id: str = Field(default_factory=_uid)
    name: str
    type: str  # character|style
    config: str = "{}"  # JSON string
    created_at: str = Field(default_factory=_now)


class PublishRecord(BaseModel):
    id: str = Field(default_factory=_uid)
    video_task_id: str
    platform: str = "youtube"
    platform_video_id: Optional[str] = None
    url: Optional[str] = None
    status: str = "pending"  # pending|uploading|published|failed
    published_at: Optional[str] = None
