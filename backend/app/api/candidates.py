from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate
router = APIRouter(prefix="/candidates", tags=["candidates"])

class CandidatePatch(BaseModel):
    absent: bool

@router.get("")
def list_candidates(db: Session = Depends(get_db)):
    return [{"id": r.id, "hall_id": r.hall_id, "name": r.name, "ticket_no": r.ticket_no,
             "paper_id": r.paper_id, "absent": r.absent}
            for r in db.scalars(select(Candidate).order_by(Candidate.id)).all()]

@router.patch("/{candidate_id}")
def patch_candidate(candidate_id: int, payload: CandidatePatch, db: Session = Depends(get_db)):
    """仅改缺考标记；占格/释放是否生效由考室缺考策略决定，并在下次重排时落成占用账行。"""
    r = db.get(Candidate, candidate_id)
    if not r:
        raise HTTPException(404, "考生不存在")
    r.absent = payload.absent
    db.commit()
    return {"id": r.id, "hall_id": r.hall_id, "name": r.name, "ticket_no": r.ticket_no,
            "paper_id": r.paper_id, "absent": r.absent}
