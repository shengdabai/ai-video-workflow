from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from orchestrator.models import ShotTask


@dataclass
class ProviderResult:
    status: str          # processing | finished | failed
    video_url: Optional[str] = None
    error: Optional[str] = None


class VideoProvider(ABC):
    @abstractmethod
    async def submit(self, shot: ShotTask) -> str:
        """提交生成任务，返回 provider_job_id"""

    @abstractmethod
    async def poll(self, job_id: str) -> ProviderResult:
        """轮询任务状态"""
