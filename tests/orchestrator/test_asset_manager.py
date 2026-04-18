import pytest
import os
from orchestrator.db import init_db
from orchestrator.assets.manager import AssetManager
from orchestrator.models import Asset


@pytest.fixture
async def manager(tmp_path):
    db_path = str(tmp_path / "test.db")
    await init_db(db_path)
    return AssetManager(db_path)


@pytest.mark.asyncio
async def test_register_asset(manager, tmp_path):
    fake_file = tmp_path / "clip.mp4"
    fake_file.write_bytes(b"fake video data")
    asset = Asset(
        shot_id="shot-123",
        type="video_clip",
        file_path=str(fake_file),
        file_size=len(b"fake video data"),
    )
    created = await manager.register(asset)
    assert created.id == asset.id
    assert created.file_size == 15


@pytest.mark.asyncio
async def test_get_assets_by_shot(manager, tmp_path):
    fake_file = tmp_path / "clip2.mp4"
    fake_file.write_bytes(b"data")
    asset = Asset(shot_id="shot-456", type="video_clip", file_path=str(fake_file))
    await manager.register(asset)
    assets = await manager.get_by_shot("shot-456")
    assert len(assets) == 1
    assert assets[0].shot_id == "shot-456"


@pytest.mark.asyncio
async def test_download_and_register(manager, tmp_path, httpx_mock):
    url = "https://example.com/video.mp4"
    httpx_mock.add_response(url=url, content=b"fake mp4 content")
    dest = str(tmp_path / "downloads" / "video.mp4")
    asset = await manager.download_and_register(
        url=url,
        dest_path=dest,
        shot_id="shot-789",
        asset_type="video_clip",
    )
    assert os.path.exists(dest)
    assert asset.file_size == len(b"fake mp4 content")
