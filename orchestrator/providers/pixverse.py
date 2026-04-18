from __future__ import annotations
import os
import httpx
from orchestrator.providers.base import VideoProvider, ProviderResult
from orchestrator.models import ShotTask

_STATUS_MAP = {
    0: "processing",
    1: "finished",
    2: "failed",
    3: "processing",
}


class PixVerseProvider(VideoProvider):
    BASE_URL = "https://api.pixverse.ai/v2"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ["PIXVERSE_API_KEY"]

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def submit(self, shot: ShotTask) -> str:
        payload = {
            "prompt": shot.prompt,
            "duration": int(shot.duration),
            "aspect_ratio": shot.aspect_ratio,
            "quality": "540p",
        }
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            resp = await client.post(
                f"{self.BASE_URL}/video/text",
                json=payload,
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("ErrCode", -1) != 0:
            raise RuntimeError(f"PixVerse submit error: {data}")
        return str(data["Resp"]["video_id"])

    async def poll(self, job_id: str) -> ProviderResult:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            resp = await client.get(
                f"{self.BASE_URL}/video/result/{job_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        if data.get("ErrCode", -1) != 0:
            return ProviderResult(status="failed", error=str(data))
        inner = data["Resp"]
        status = _STATUS_MAP.get(inner.get("status", -1), "failed")
        url = inner.get("url") or None
        return ProviderResult(status=status, video_url=url if url else None)
