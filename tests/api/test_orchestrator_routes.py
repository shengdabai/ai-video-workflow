import pytest
import os
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
async def setup_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("ORCHESTRATOR_DB_PATH", db_path)
    import orchestrator.db as db_module
    db_module._DB_PATH = db_path
    import api.routers.orchestrator as orch_module
    orch_module._DB_PATH = db_path
    from orchestrator.db import init_db
    await init_db(db_path)


@pytest.mark.asyncio
async def test_create_video_task():
    from api.app import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/orchestrator/tasks", json={
            "title": "测试视频",
            "script": "镜头1：日落\n镜头2：夜景",
        })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "测试视频"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_list_video_tasks():
    from api.app import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/orchestrator/tasks", json={"title": "视频A", "script": "s1"})
        resp = await client.get("/api/orchestrator/tasks")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_approve_shot():
    from api.app import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        task_resp = await client.post("/api/orchestrator/tasks", json={"title": "t", "script": "s"})
        task_id = task_resp.json()["id"]
        shot_resp = await client.post(f"/api/orchestrator/tasks/{task_id}/shots", json={
            "shots": [{"shot_index": 0, "prompt": "海边", "duration": 5, "aspect_ratio": "9:16"}]
        })
        shot_id = shot_resp.json()[0]["id"]
        resp = await client.post(f"/api/orchestrator/shots/{shot_id}/approve")
    assert resp.status_code == 200
