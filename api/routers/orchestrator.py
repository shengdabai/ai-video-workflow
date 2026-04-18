from __future__ import annotations
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from orchestrator.db import set_db_path, get_db
from orchestrator.queue.manager import QueueManager
from orchestrator.review.manager import ReviewManager
from orchestrator.models import VideoTask, ShotTask, Asset, PublishRecord

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

_DB_PATH = os.environ.get("ORCHESTRATOR_DB_PATH", "orchestrator.db")


def _queue() -> QueueManager:
    return QueueManager(_DB_PATH)


def _review() -> ReviewManager:
    return ReviewManager(_DB_PATH)


class CreateVideoTaskRequest(BaseModel):
    title: str
    script: str
    style_pack_id: Optional[str] = None
    character_pack_id: Optional[str] = None


class ShotPayload(BaseModel):
    shot_index: int
    prompt: str
    duration: float = 5.0
    aspect_ratio: str = "9:16"


class CreateShotsRequest(BaseModel):
    shots: list[ShotPayload]


class RejectShotRequest(BaseModel):
    new_prompt: Optional[str] = None


class PublishRequest(BaseModel):
    title: str
    description: str = ""
    tags: list[str] = []
    privacy: str = "private"
    bgm_path: Optional[str] = None


@router.post("/tasks", status_code=201)
async def create_video_task(req: CreateVideoTaskRequest):
    task = VideoTask(
        title=req.title,
        script=req.script,
        style_pack_id=req.style_pack_id,
        character_pack_id=req.character_pack_id,
    )
    return await _queue().create_video_task(task)


@router.get("/tasks")
async def list_video_tasks():
    return await _queue().list_video_tasks()


@router.get("/tasks/{task_id}")
async def get_video_task(task_id: str):
    task = await _queue().get_video_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/tasks/{task_id}/shots", status_code=201)
async def create_shots(task_id: str, req: CreateShotsRequest):
    shots = [
        ShotTask(
            video_task_id=task_id,
            shot_index=s.shot_index,
            prompt=s.prompt,
            duration=s.duration,
            aspect_ratio=s.aspect_ratio,
        )
        for s in req.shots
    ]
    return await _queue().create_shots(shots)


@router.get("/tasks/{task_id}/shots")
async def get_shots(task_id: str):
    return await _queue().get_shots_by_video(task_id)


@router.post("/tasks/{task_id}/review/approve")
async def approve_video(task_id: str):
    await _review().approve_video(task_id)
    return {"ok": True}


@router.post("/shots/{shot_id}/approve")
async def approve_shot(shot_id: str):
    await _review().approve_shot(shot_id)
    return {"ok": True}


@router.post("/shots/{shot_id}/reject")
async def reject_shot(shot_id: str, req: RejectShotRequest):
    await _review().reject_shot(shot_id, new_prompt=req.new_prompt)
    return {"ok": True}


@router.post("/tasks/{task_id}/publish")
async def publish_task(task_id: str, req: PublishRequest):
    from orchestrator.publish.composer import compose_video
    from orchestrator.publish.youtube import upload_to_youtube, VideoMeta
    from orchestrator.assets.manager import AssetManager

    queue = _queue()
    shots = await queue.get_shots_by_video(task_id)
    approved = sorted(
        [s for s in shots if s.status == "approved"],
        key=lambda s: s.shot_index,
    )
    if not approved:
        raise HTTPException(status_code=400, detail="No approved shots")

    asset_mgr = AssetManager(_DB_PATH)
    clip_paths = []
    for shot in approved:
        assets = await asset_mgr.get_by_shot(shot.id)
        clips = [a for a in assets if a.type == "video_clip"]
        if not clips:
            raise HTTPException(
                status_code=400,
                detail=f"Shot {shot.shot_index} has no video_clip asset",
            )
        clip_paths.append(clips[-1].file_path)

    output_path = f"output/exports/{task_id}/final.mp4"
    await compose_video(clip_paths=clip_paths, output_path=output_path, bgm_path=req.bgm_path)

    export_asset = Asset(task_id=task_id, type="export", file_path=output_path)
    await asset_mgr.register(export_asset)

    meta = VideoMeta(
        title=req.title,
        description=req.description,
        tags=req.tags,
        privacy=req.privacy,
    )
    video_id = await upload_to_youtube(output_path, meta)

    record = PublishRecord(
        video_task_id=task_id,
        platform="youtube",
        platform_video_id=video_id,
        url=f"https://www.youtube.com/watch?v={video_id}",
        status="published",
        published_at=datetime.utcnow().isoformat(),
    )
    async with get_db() as conn:
        await conn.execute(
            """INSERT INTO publish_records
               (id, video_task_id, platform, platform_video_id, url, status, published_at)
               VALUES (?,?,?,?,?,?,?)""",
            (record.id, record.video_task_id, record.platform,
             record.platform_video_id, record.url, record.status, record.published_at),
        )
        await conn.commit()
    await queue.update_video_task(task_id, status="published")
    return {"youtube_url": record.url, "video_id": video_id}
