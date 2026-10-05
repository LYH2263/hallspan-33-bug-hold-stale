from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.models import Candidate, Hall, PaperSet

# 种子缺考生（名册下标）：先按占格保留演示，之后可在「考室」改为释放空出，
# 同一缺考生会从占用账有占格行变为无行，排座图与统计一起变。
ABSENT_INDEXES = {4, 9}

def seed_if_empty(db: Session) -> None:
    if (db.scalar(select(func.count()).select_from(Hall)) or 0) > 0:
        return
    hall = Hall(code="H101", name="一号考室", rows=5, cols=6, min_manhattan=2,
                absent_policy="reserve")
    db.add(hall); db.flush()
    papers = [("P-A", "语文 A 卷"), ("P-B", "语文 B 卷"), ("P-C", "语文 C 卷")]
    paper_ids = []
    for code, title in papers:
        p = PaperSet(code=code, title=title)
        db.add(p); db.flush()
        paper_ids.append(p.id)
    names = ["陈一", "李二", "张三", "赵四", "钱五", "孙六", "周七", "吴八", "郑九", "王十", "冯十一", "陈十二"]
    for i, name in enumerate(names):
        db.add(Candidate(hall_id=hall.id, name=name, ticket_no=f"T{2026001+i}",
                         paper_id=paper_ids[i % len(paper_ids)], absent=i in ABSENT_INDEXES))
    db.commit()
