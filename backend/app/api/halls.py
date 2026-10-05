from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Hall
from app.services import planning
from app.services.seat_engine import ABSENT_POLICIES, effective_absent_policy
router = APIRouter(prefix="/halls", tags=["halls"])

class AbsentPolicyIn(BaseModel):
    policy: str  # reserve=占格保留 / release=释放空出，互斥

@router.get("")
def list_halls(db: Session = Depends(get_db)):
    return [{"id": r.id, "code": r.code, "name": r.name, "rows": r.rows, "cols": r.cols,
             "min_manhattan": r.min_manhattan,
             "absent_policy": effective_absent_policy(r.absent_policy),
             "absent_policy_configured": r.absent_policy is not None}
            for r in db.scalars(select(Hall).order_by(Hall.id)).all()]

@router.put("/{hall_id}/absent-policy")
def switch_absent_policy(hall_id: int, payload: AbsentPolicyIn, db: Session = Depends(get_db)):
    """切换缺考策略并立即按新策略重排：策略字段、占用账、最新方案同一事务提交。

    保存失败时整体回滚，策略字段、占用账、最新方案、统计全部回到保存前。
    """
    if payload.policy not in ABSENT_POLICIES:
        raise HTTPException(400, "缺考策略只能是 reserve（占格保留）或 release（释放空出）")
    hall = db.get(Hall, hall_id)
    if not hall:
        raise HTTPException(404, "考室不存在")
    try:
        hall.absent_policy = payload.policy
        db.commit()
        plan, result = planning.persist_plan(db, hall)
    except Exception:
        db.rollback()
        raise HTTPException(500, "缺考策略保存失败，已回滚到保存前状态")
    return {"hall_id": hall.id, "absent_policy": effective_absent_policy(hall.absent_policy),
            "plan_id": plan.id, "stats": result["stats"]}
