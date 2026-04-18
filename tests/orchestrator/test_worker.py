import pytest
from unittest.mock import AsyncMock, patch
from orchestrator.db import init_db
from orchestrator.queue.manager import QueueManager
from orchestrator.models import VideoTask, ShotTask
from orchestrator.worker import process_one_cycle


@pytest.fixture
async def setup(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    queue = QueueManager(db_path)
    task = VideoTask(title="t", script="s", status="processing")
    await queue.create_video_task(task)
    shot = ShotTask(video_task_id=task.id, shot_index=0, prompt="海边")
    await queue.create_shots([shot])
    return db_path, queue, shot


@pytest.mark.asyncio
async def test_pending_shot_submitted(setup, tmp_path):
    db_path, queue, shot = setup
    mock_provider = AsyncMock()
    mock_provider.submit = AsyncMock(return_value="pv-job-001")
    with patch("orchestrator.worker.get_provider", return_value=mock_provider):
        await process_one_cycle(db_path=db_path)
    updated = await queue.get_shot(shot.id)
    assert updated.status == "generating"
    assert updated.provider_job_id == "pv-job-001"


@pytest.mark.asyncio
async def test_generating_shot_polled_to_review(setup, tmp_path):
    db_path, queue, shot = setup
    await queue.update_shot(shot.id, status="generating", provider_job_id="pv-job-002")
    mock_provider = AsyncMock()
    from orchestrator.providers.base import ProviderResult
    mock_provider.poll = AsyncMock(
        return_value=ProviderResult(
            status="finished",
            video_url="https://cdn.example.com/video.mp4",
        )
    )
    mock_asset_mgr = AsyncMock()
    mock_asset_mgr.download_and_register = AsyncMock()
    with patch("orchestrator.worker.get_provider", return_value=mock_provider), \
         patch("orchestrator.worker.AssetManager", return_value=mock_asset_mgr):
        await process_one_cycle(db_path=db_path)
    updated = await queue.get_shot(shot.id)
    assert updated.status == "review_pending"
