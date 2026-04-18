from __future__ import annotations
from typing import Optional
from orchestrator.db import set_db_path
from orchestrator.queue.manager import QueueManager


class ReviewManager:
    def __init__(self, db_path: str | None = None):
        if db_path:
            set_db_path(db_path)
        self._queue = QueueManager(db_path)

    async def approve_video(self, video_task_id: str) -> None:
        await self._queue.update_video_task(video_task_id, status="approved")
        shots = await self._queue.get_shots_by_video(video_task_id)
        for shot in shots:
            if shot.status == "review_pending":
                await self._queue.update_shot(shot.id, status="approved")

    async def approve_shot(self, shot_id: str) -> None:
        await self._queue.update_shot(shot_id, status="approved")

    async def reject_shot(self, shot_id: str, new_prompt: Optional[str] = None) -> None:
        updates: dict = {"status": "pending"}
        if new_prompt:
            updates["prompt"] = new_prompt
        await self._queue.update_shot(shot_id, **updates)

    async def replace_shot_asset(self, shot_id: str, file_path: str, file_size: int) -> None:
        from orchestrator.assets.manager import AssetManager
        from orchestrator.models import Asset
        asset_mgr = AssetManager()
        asset = Asset(shot_id=shot_id, type="video_clip", file_path=file_path, file_size=file_size)
        await asset_mgr.register(asset)
        await self._queue.update_shot(shot_id, status="approved")
