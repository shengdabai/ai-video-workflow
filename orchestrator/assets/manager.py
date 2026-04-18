from __future__ import annotations
import os
import httpx
from orchestrator.db import get_db, set_db_path
from orchestrator.models import Asset


class AssetManager:
    def __init__(self, db_path: str | None = None):
        if db_path:
            set_db_path(db_path)

    async def register(self, asset: Asset) -> Asset:
        async with get_db() as conn:
            await conn.execute(
                """INSERT INTO assets (id, task_id, shot_id, type, file_path, file_size, meta, created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (asset.id, asset.task_id, asset.shot_id, asset.type,
                 asset.file_path, asset.file_size, asset.meta, asset.created_at),
            )
            await conn.commit()
        return asset

    async def get_by_shot(self, shot_id: str) -> list[Asset]:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT * FROM assets WHERE shot_id=?", (shot_id,)
            )
            rows = await cursor.fetchall()
        return [Asset(**dict(r)) for r in rows]

    async def get_by_task(self, task_id: str) -> list[Asset]:
        async with get_db() as conn:
            cursor = await conn.execute(
                "SELECT * FROM assets WHERE task_id=?", (task_id,)
            )
            rows = await cursor.fetchall()
        return [Asset(**dict(r)) for r in rows]

    async def download_and_register(
        self,
        url: str,
        dest_path: str,
        shot_id: str | None = None,
        task_id: str | None = None,
        asset_type: str = "video_clip",
    ) -> Asset:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        async with httpx.AsyncClient(timeout=300, trust_env=False) as client:
            response = await client.get(url)
            response.raise_for_status()
            with open(dest_path, "wb") as f:
                f.write(response.content)
        file_size = os.path.getsize(dest_path)
        asset = Asset(
            shot_id=shot_id,
            task_id=task_id,
            type=asset_type,
            file_path=dest_path,
            file_size=file_size,
        )
        return await self.register(asset)
