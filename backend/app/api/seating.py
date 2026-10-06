import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Hall
from app.services import planning
router = APIRouter(prefix="/seating", tags=["seating"])

@router.post("/run")
def run_seating(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    plan, result = planning.persist_plan(db, hall)
    return {"id": plan.id, **result}

@router.get("/latest")
def latest(hall_id: int = 1, db: Session = Depends(get_db)):
    plan = planning.latest_plan(db, hall_id)
    if not plan:
        return run_seating(hall_id=hall_id, db=db)
    data = json.loads(plan.result_json)
    return {"id": plan.id, **data}

@router.get("/ledger")
def ledger(hall_id: int = 1, db: Session = Depends(get_db)):
    """占用账：当前生效的占格行（正常入座 + 缺考占格），与最新方案同一套结果。"""
    plan = planning.latest_plan(db, hall_id)
    if not plan:
        run_seating(hall_id=hall_id, db=db)
        plan = planning.latest_plan(db, hall_id)
    rows = planning.ensure_ledger(db, hall_id, plan)
    return {
        "hall_id": hall_id,
        "plan_id": plan.id,
        "rows": [
            {"id": r.id, "row": r.row, "col": r.col, "candidate_id": r.candidate_id,
             "name": r.name, "ticket_no": r.ticket_no, "paper_id": r.paper_id, "kind": r.kind}
            for r in rows
        ],
    }

@router.get("/violations")
def violations(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, "violations": data.get("violations", []),
            "unplaced": data.get("unplaced", []), "absent": data.get("absent", [])}

@router.get("/stats")
def stats(hall_id: int = 1, db: Session = Depends(get_db)):
    """统计与最新方案同一套结果：占格、未排、缺考名单都跟当前策略对齐。"""
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, **(data.get("stats") or {})}
