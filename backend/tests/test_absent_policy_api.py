"""缺考策略 API 级验收：种子先占格保留再改为释放；切换失败整体回滚。"""
import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="hallspan_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import SessionLocal
from app.main import app
from app.models.models import Candidate, Hall
from app.services import planning


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _absent_ids() -> set[int]:
    db = SessionLocal()
    try:
        return {c.id for c in db.scalars(select(Candidate).where(Candidate.absent == True)).all()}
    finally:
        db.close()


def test_seed_starts_with_reserve_policy(client):
    hall = client.get("/api/halls").json()[0]
    assert hall["absent_policy"] == "reserve"
    assert hall["absent_policy_configured"] is True
    assert len(_absent_ids()) == 2


def test_reserve_writes_ledger_rows_for_absent(client):
    plan = client.post("/api/seating/run?hall_id=1").json()
    absent_ids = _absent_ids()
    reserved = [a for a in plan["assignments"] if a["kind"] == "absent_reserve"]
    # 占格保留：每个缺考生在占用账留一行占格
    assert {a["candidate_id"] for a in reserved} == absent_ids
    # 统计占格含缺考生本人
    assert plan["stats"]["absent_reserved"] == 2
    assert plan["stats"]["occupied"] == plan["stats"]["seated"] + plan["stats"]["absent_reserved"]
    # 未排名单不得再把缺考生当可调剂未排
    assert all(u["id"] not in absent_ids for u in plan["unplaced"])
    # 占用账与排座图同一套结果
    ledger = client.get("/api/seating/ledger?hall_id=1").json()["rows"]
    assert len(ledger) == len(plan["assignments"]) == plan["stats"]["occupied"]
    assert {r["candidate_id"] for r in ledger if r["kind"] == "absent_reserve"} == absent_ids


def test_switch_to_release_rewrites_ledger_map_stats(client):
    absent_ids = _absent_ids()
    before = client.get("/api/seating/ledger?hall_id=1").json()["rows"]
    assert any(r["candidate_id"] in absent_ids for r in before)

    res = client.put("/api/halls/1/absent-policy", json={"policy": "release"})
    assert res.status_code == 200
    assert res.json()["absent_policy"] == "release"

    # 同一缺考从占用账有行变为无行
    after = client.get("/api/seating/ledger?hall_id=1").json()["rows"]
    assert not any(r["candidate_id"] in absent_ids for r in after)
    # 图与统计一起变：不再展示旧策略占格
    latest = client.get("/api/seating/latest?hall_id=1").json()
    assert not any(a["candidate_id"] in absent_ids for a in latest["assignments"])
    assert latest["stats"]["absent_reserved"] == 0
    assert latest["stats"]["absent_released"] == 2
    assert latest["stats"]["occupied"] == len(latest["assignments"]) == len(after)
    # 缺考名单仍在（状态为已释放），未排名单仍不含缺考生
    assert {a["id"] for a in latest["absent"]} == absent_ids
    assert all(a["status"] == "released" for a in latest["absent"])
    assert all(u["id"] not in absent_ids for u in latest["unplaced"])
    assert client.get("/api/halls").json()[0]["absent_policy"] == "release"


def test_invalid_policy_rejected(client):
    res = client.put("/api/halls/1/absent-policy", json={"policy": "keep"})
    assert res.status_code == 400


def test_failed_switch_rolls_back_everything(client, monkeypatch):
    before_policy = client.get("/api/halls").json()[0]["absent_policy"]
    before_ledger = client.get("/api/seating/ledger?hall_id=1").json()["rows"]
    before_latest = client.get("/api/seating/latest?hall_id=1").json()
    before_stats = client.get("/api/seating/stats?hall_id=1").json()

    def boom(*args, **kwargs):
        raise RuntimeError("engine failure")

    monkeypatch.setattr(planning, "place_candidates", boom)
    res = client.put("/api/halls/1/absent-policy", json={"policy": "reserve"})
    assert res.status_code == 500

    # 策略字段、占用账、最新方案、统计全部回到保存前
    assert client.get("/api/halls").json()[0]["absent_policy"] == before_policy
    assert client.get("/api/seating/ledger?hall_id=1").json()["rows"] == before_ledger
    assert client.get("/api/seating/latest?hall_id=1").json() == before_latest
    assert client.get("/api/seating/stats?hall_id=1").json() == before_stats


def test_unconfigured_policy_defaults_to_release(client):
    db = SessionLocal()
    try:
        hall = db.get(Hall, 1)
        hall.absent_policy = None
        db.commit()
    finally:
        db.close()
    hall = client.get("/api/halls").json()[0]
    assert hall["absent_policy"] == "release"
    assert hall["absent_policy_configured"] is False
    plan = client.post("/api/seating/run?hall_id=1").json()
    absent_ids = _absent_ids()
    assert not any(a["candidate_id"] in absent_ids for a in plan["assignments"])
    assert plan["stats"]["absent_released"] == 2


def test_patch_candidate_absent_flag(client):
    cands = client.get("/api/candidates").json()
    target = next(c for c in cands if not c["absent"])
    res = client.patch(f"/api/candidates/{target['id']}", json={"absent": True})
    assert res.status_code == 200 and res.json()["absent"] is True
    res = client.patch(f"/api/candidates/{target['id']}", json={"absent": False})
    assert res.status_code == 200 and res.json()["absent"] is False
