import pytest
from orchestrator.db import init_db
from orchestrator.queue.manager import QueueManager
from orchestrator.models import VideoTask, ShotTask


@pytest.fixture
async def manager(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return QueueManager(db_path)


@pytest.mark.asyncio
async def test_create_video_task(manager):
    task = VideoTask(title="测试视频", script="镜头1：海边日落\n镜头2：城市夜景")
    created = await manager.create_video_task(task)
    assert created.id == task.id
    assert created.status == "pending"


@pytest.mark.asyncio
async def test_create_shots_for_task(manager):
    task = VideoTask(title="测试", script="s")
    await manager.create_video_task(task)
    shots = [
        ShotTask(video_task_id=task.id, shot_index=0, prompt="海边日落，金色光芒"),
        ShotTask(video_task_id=task.id, shot_index=1, prompt="城市夜景，霓虹灯"),
    ]
    created = await manager.create_shots(shots)
    assert len(created) == 2


@pytest.mark.asyncio
async def test_get_pending_shots(manager):
    task = VideoTask(title="测试", script="s")
    await manager.create_video_task(task)
    shot = ShotTask(video_task_id=task.id, shot_index=0, prompt="测试镜头")
    await manager.create_shots([shot])
    pending = await manager.get_shots_by_status("pending")
    assert len(pending) == 1
    assert pending[0].id == shot.id


@pytest.mark.asyncio
async def test_update_shot_status(manager):
    task = VideoTask(title="测试", script="s")
    await manager.create_video_task(task)
    shot = ShotTask(video_task_id=task.id, shot_index=0, prompt="测试")
    await manager.create_shots([shot])
    await manager.update_shot(shot.id, status="generating", provider_job_id="pv-123")
    updated = await manager.get_shot(shot.id)
    assert updated.status == "generating"
    assert updated.provider_job_id == "pv-123"
