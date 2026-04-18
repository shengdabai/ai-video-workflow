import pytest
from orchestrator.providers.pixverse import PixVerseProvider
from orchestrator.providers.base import ProviderResult
from orchestrator.models import ShotTask


@pytest.mark.asyncio
async def test_submit_returns_job_id(httpx_mock):
    httpx_mock.add_response(
        method="POST",
        url="https://api.pixverse.ai/v2/video/text",
        json={"ErrCode": 0, "Resp": {"video_id": 99999}},
    )
    provider = PixVerseProvider(api_key="test-key")
    shot = ShotTask(video_task_id="t1", shot_index=0, prompt="海边日落")
    job_id = await provider.submit(shot)
    assert job_id == "99999"


@pytest.mark.asyncio
async def test_poll_finished(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://api.pixverse.ai/v2/video/result/99999",
        json={
            "ErrCode": 0,
            "Resp": {"status": 1, "url": "https://cdn.pixverse.ai/video.mp4"},
        },
    )
    provider = PixVerseProvider(api_key="test-key")
    result = await provider.poll("99999")
    assert result.status == "finished"
    assert result.video_url == "https://cdn.pixverse.ai/video.mp4"


@pytest.mark.asyncio
async def test_poll_processing(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://api.pixverse.ai/v2/video/result/88888",
        json={"ErrCode": 0, "Resp": {"status": 0, "url": ""}},
    )
    provider = PixVerseProvider(api_key="test-key")
    result = await provider.poll("88888")
    assert result.status == "processing"
    assert result.video_url is None
