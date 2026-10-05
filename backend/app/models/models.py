from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Hall(Base):
    __tablename__ = "halls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    rows: Mapped[int] = mapped_column(Integer)
    cols: Mapped[int] = mapped_column(Integer)
    min_manhattan: Mapped[int] = mapped_column(Integer, default=2)
    # 缺考策略：reserve=占格保留 / release=释放空出，互斥；NULL=未配置，按 release 兼容现网
    absent_policy: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)

class PaperSet(Base):
    __tablename__ = "paper_sets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    title: Mapped[str] = mapped_column(String(128))

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.id"))
    name: Mapped[str] = mapped_column(String(64))
    ticket_no: Mapped[str] = mapped_column(String(32))
    paper_id: Mapped[int] = mapped_column(ForeignKey("paper_sets.id"))
    absent: Mapped[bool] = mapped_column(Boolean, default=False)

class SeatPlan(Base):
    __tablename__ = "seat_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    result_json: Mapped[str] = mapped_column(Text, default="{}")

class SeatOccupancy(Base):
    """占用账：每行一个被占格子（seat=正常入座，absent_reserve=缺考占格）。

    缺考策略必须落成此账行，不能只改考生标记。每次重排按当前策略整批重写，
    与 SeatPlan 同一事务提交，保证排座图、占用账、统计、未排/缺考名单是同一套结果。
    """
    __tablename__ = "seat_occupancies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hall_id: Mapped[int] = mapped_column(ForeignKey("halls.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("seat_plans.id"))
    row: Mapped[int] = mapped_column(Integer)
    col: Mapped[int] = mapped_column(Integer)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"))
    name: Mapped[str] = mapped_column(String(64))
    ticket_no: Mapped[str] = mapped_column(String(32))
    paper_id: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(16), default="seat")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
