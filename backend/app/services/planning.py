"""重排落库：新方案 + 占用账整批重写，同一事务提交。

调用方若在事务中途失败，rollback 即可让策略字段、占用账、最新方案、统计
全部回到保存前（统计/图/账都由最新方案与占用账行派生）。
"""
import json
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.models import Candidate, Hall, SeatOccupancy, SeatPlan
from app.services.seat_engine import (
    effective_absent_policy,
    find_violations,
    place_candidates,
    plan_to_dict,
)


def build_plan_result(db: Session, hall: Hall) -> dict:
    policy = effective_absent_policy(hall.absent_policy)
    cands = [
        {"id": c.id, "name": c.name, "ticket_no": c.ticket_no, "paper_id": c.paper_id, "absent": c.absent}
        for c in db.scalars(select(Candidate).where(Candidate.hall_id == hall.id)).all()
    ]
    assigns, unplaced, absent_rows = place_candidates(hall.rows, hall.cols, hall.min_manhattan, cands, policy)
    viols = find_violations(hall.rows, hall.cols, hall.min_manhattan, assigns)
    result = plan_to_dict(assigns, unplaced, absent_rows, viols, hall.rows, hall.cols, policy)
    result["hall"] = {"id": hall.id, "name": hall.name, "min_manhattan": hall.min_manhattan}
    return result


def persist_plan(db: Session, hall: Hall, new_policy: str | None = None) -> tuple[SeatPlan, dict]:
    """按考室缺考策略重排并落库：策略字段（如有切换）、新方案、占用账同一事务提交。

    任何一步失败由调用方 rollback，策略字段、占用账、最新方案、统计全部回到保存前。
    """
    if new_policy is not None:
        hall.absent_policy = new_policy
    result = build_plan_result(db, hall)
    plan = SeatPlan(hall_id=hall.id, created_at=datetime.utcnow(),
                    result_json=json.dumps(result, ensure_ascii=False))
    db.add(plan)
    db.flush()
    # 占用账整批重写：先删旧行，再按新方案写新行（含缺考占格行；释放空出者无行）。
    # 与上面的策略字段更新、方案插入在同一事务，禁止留下旧策略占格。
    db.execute(delete(SeatOccupancy).where(SeatOccupancy.hall_id == hall.id))
    for a in result["assignments"]:
        db.add(SeatOccupancy(
            hall_id=hall.id, plan_id=plan.id, row=a["row"], col=a["col"],
            candidate_id=a["candidate_id"], name=a["name"], ticket_no=a["ticket_no"],
            paper_id=a["paper_id"], kind=a["kind"], created_at=datetime.utcnow(),
        ))
    db.commit()
    db.refresh(plan)
    return plan, result


def latest_plan(db: Session, hall_id: int) -> SeatPlan | None:
    return db.scalars(
        select(SeatPlan).where(SeatPlan.hall_id == hall_id).order_by(SeatPlan.id.desc())
    ).first()


def ensure_ledger(db: Session, hall_id: int, plan: SeatPlan) -> list[SeatOccupancy]:
    """读取占用账；若现网升级后旧方案尚无账行（或账行不属于最新方案），按方案结果补写。"""
    rows = db.scalars(
        select(SeatOccupancy).where(SeatOccupancy.hall_id == hall_id).order_by(SeatOccupancy.row, SeatOccupancy.col)
    ).all()
    if rows and rows[0].plan_id == plan.id:
        return rows
    if rows:
        db.execute(delete(SeatOccupancy).where(SeatOccupancy.hall_id == hall_id))
    data = json.loads(plan.result_json)
    for a in data.get("assignments", []):
        db.add(SeatOccupancy(
            hall_id=hall_id, plan_id=plan.id, row=a["row"], col=a["col"],
            candidate_id=a["candidate_id"], name=a["name"], ticket_no=a["ticket_no"],
            paper_id=a["paper_id"], kind=a.get("kind", "seat"), created_at=datetime.utcnow(),
        ))
    db.commit()
    return db.scalars(
        select(SeatOccupancy).where(SeatOccupancy.hall_id == hall_id).order_by(SeatOccupancy.row, SeatOccupancy.col)
    ).all()
