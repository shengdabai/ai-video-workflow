from __future__ import annotations
from typing import Optional
from datetime import datetime
from orchestrator.db import get_db, set_db_path
from orchestrator.models import VideoTask, ShotTask


class QueueManager:
    def __init__(self, db_path: str | None = None):
        if db_path:
            set_db_path(db_path)

    async def create_video_task(self, task: VideoTask) -> VideoTask:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO video_tasks
                   (id, title, script, style_pack_id, character_pack_id, status, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (task.id, task.title, task.script, task.style_pack_id,
                 task.character_pack_id, task.status, task.created_at, task.updated_at),
            )
            await conn.commit()
        return task

    async def get_video_task(self, task_id: str) -> Optional[VideoTask]:
        async with get_db() as conn:
            cursor = await conn.execute("SELECT * FROM video_tasks WHERE id=?", (task_id,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return VideoTask(**dict(row))

    async def list_video_tasks(self) -> list[VideoTask]:
        async with get_db() as conn:
            cursor = await conn.execute("SELECT * FROM video_tasks ORDER BY created_at DESC")
            rows = await cursor.fetchall()
        return [VideoTask(**dict(r)) for r in rows]

    async def update_video_task(self, task_id: str, **kwargs) -> None:
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [task_id]
        async with get_db() as conn:
            await conn.execute(f"UPDATE video_tasks SET {sets} WHERE id=?", vals)
            await conn.commit()

    async def create_shots(self, shots: list[ShotTask]) -> list[ShotTask]:
        async with get_db() as conn:
            for s in shots:
                await conn.execute(
                    """INSERT INTO shot_tasks
                       (id, video_task_id, shot_index, prompt, duration, aspect_ratio,
                        status, retry_count, provider, provider_job_id, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (s.id, s.video_task_id, s.shot_index, s.prompt, s.duration,
                     s.aspect_ratio, s.status, s.retry_count, s.provider,
                     s.provider_job_id, s.created_at, s.updated_at),
                )
            await conn.commit()
        return shots

    async def get_shot(self, shot_id: str) -> Optional[ShotTask]:
        async with get_db() as conn:
            cursor = await conn.execute("SELECT * FROM shot_tasks WHERE id=?", (shot_id,))
            row = await cursor.fetchone()
        if row is None:
            return None
        return ShotTask(**dict(row))

    async def get_shots_by_video(self, video_task_id: str) -> list[ShotTask]:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT * FROM shot_tasks WHERE video_task_id=? ORDER BY shot_index",
                (video_task_id,),
            )
            rows = await cursor.fetchall()
        return [ShotTask(**dict(r)) for r in rows]

    async def get_shots_by_status(self, status: str) -> list[ShotTask]:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT * FROM shot_tasks WHERE status=? ORDER BY created_at", (status,)
            )
            rows = await cursor.fetchall()
        return [ShotTask(**dict(r)) for r in rows]

    async def update_shot(self, shot_id: str, **kwargs) -> None:
        kwargs["updated_at"] = datetime.utcnow().isoformat()
        sets = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [shot_id]
        async with get_db() as conn:
            await conn.execute(f"UPDATE shot_tasks SET {sets} WHERE id=?", vals)
            await conn.commit()

    async def increment_retry(self, shot_id: str) -> int:
        async with get_db() as conn:
            await conn.execute(
                "UPDATE shot_tasks SET retry_count=retry_count+1, updated_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), shot_id),
            )
            await conn.commit()
            cursor = await conn.execute("SELECT retry_count FROM shot_tasks WHERE id=?", (shot_id,))
            row = await cursor.fetchone()
        return row["retry_count"]
