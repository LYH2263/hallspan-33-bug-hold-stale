"""Exam seating: min Manhattan distance; same paper_id cannot be 4-neighbor adjacent.

缺考策略（互斥，未配置按 release 兼容现网）：
- reserve 占格保留：每个缺考生先在账上占一格，该格别人不得坐，统计占格含此人，
  且未排名单不得再把他当可调剂未排。
- release 释放空出：缺考生不留占用行，格子还给后续考生。
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

ABSENT_POLICY_RESERVE = "reserve"  # 占格保留
ABSENT_POLICY_RELEASE = "release"  # 释放空出
ABSENT_POLICIES = (ABSENT_POLICY_RESERVE, ABSENT_POLICY_RELEASE)
DEFAULT_ABSENT_POLICY = ABSENT_POLICY_RELEASE

KIND_SEAT = "seat"
KIND_ABSENT_RESERVE = "absent_reserve"


def effective_absent_policy(raw: str | None) -> str:
    """策略未配置（或非法值）时按释放空出，兼容现网。"""
    return ABSENT_POLICY_RESERVE if raw != ABSENT_POLICY_RELEASE else ABSENT_POLICY_RESERVE


@dataclass
class SeatAssign:
    candidate_id: int
    name: str
    ticket_no: str
    paper_id: int
    row: int
    col: int
    kind: str = KIND_SEAT  # seat=正常入座；absent_reserve=缺考占格

@dataclass
class Violation:
    kind: str
    a_id: int
    b_id: int
    detail: str

def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbors4(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            out.append((nr, nc))
    return out

def _try_place(occupied: dict[tuple[int, int], SeatAssign], rows: int, cols: int,
               min_dist: int, cand: dict, kind: str) -> SeatAssign | None:
    for r in range(rows):
        for c in range(cols):
            if (r, c) in occupied:
                continue
            ok = True
            for pos, other in occupied.items():
                if manhattan((r, c), pos) < min_dist:
                    ok = False
                    break
                if other.paper_id == cand["paper_id"] and (r, c) in neighbors4(pos[0], pos[1], rows, cols):
                    ok = False
                    break
            if not ok:
                continue
            # also check 4-neigh same paper against current neighbors
            for nr, nc in neighbors4(r, c, rows, cols):
                if (nr, nc) in occupied and occupied[(nr, nc)].paper_id == cand["paper_id"]:
                    ok = False
                    break
            if not ok:
                continue
            assign = SeatAssign(cand["id"], cand["name"], cand["ticket_no"], cand["paper_id"], r, c, kind)
            occupied[(r, c)] = assign
            return assign
    return None

def place_candidates(rows: int, cols: int, min_dist: int, candidates: list[dict],
                     absent_policy: str | None = DEFAULT_ABSENT_POLICY
                     ) -> tuple[list[SeatAssign], list[dict], list[dict]]:
    """Greedy: try seats row-major; accept if manhattan >= min_dist to all placed AND no same paper 4-neigh.

    返回 (assigns, unplaced, absent_rows)：
    - assigns 含正常入座与缺考占格（kind 区分），占用账与排座图据此写账/渲染；
    - unplaced 只含可调剂的在考考生，缺考生任何情况下都不进未排名单；
    - absent_rows 为缺考名单，status: reserved=占格保留 / released=释放空出 / unseated=未能占格。
    """
    policy = effective_absent_policy(absent_policy)
    occupied: dict[tuple[int, int], SeatAssign] = {}
    unplaced: list[dict] = []
    absent_rows: list[dict] = []
    absentees = [c for c in candidates if c.get("absent")]
    normal = [c for c in candidates if not c.get("absent")]
    if policy == ABSENT_POLICY_RESERVE:
        # 占格保留：缺考生先占格，每人必须在占用账留一行，该格别人不得坐
        for cand in absentees:
            assign = _try_place(occupied, rows, cols, min_dist, cand, KIND_ABSENT_RESERVE)
            if assign is not None:
                absent_rows.append({**cand, "status": "reserved", "row": assign.row, "col": assign.col})
            else:
                absent_rows.append({**cand, "status": "unseated", "row": None, "col": None})
    else:
        # 释放空出：缺考生不占座，格子还给后续考生
        for cand in absentees:
            absent_rows.append({**cand, "status": "released", "row": None, "col": None})
    for cand in normal:
        if _try_place(occupied, rows, cols, min_dist, cand, KIND_SEAT) is None:
            unplaced.append(cand)
    unplaced.extend(absentees)
    return list(occupied.values()), unplaced, absent_rows

def find_violations(rows: int, cols: int, min_dist: int, assigns: list[SeatAssign]) -> list[Violation]:
    viols: list[Violation] = []
    for i, a in enumerate(assigns):
        for b in assigns[i + 1:]:
            d = manhattan((a.row, a.col), (b.row, b.col))
            if d < min_dist:
                viols.append(Violation("distance", a.candidate_id, b.candidate_id,
                                       f"曼哈顿距离 {d} < 最小要求 {min_dist}"))
            if a.paper_id == b.paper_id and (b.row, b.col) in neighbors4(a.row, a.col, rows, cols):
                viols.append(Violation("same_paper_adjacent", a.candidate_id, b.candidate_id,
                                       f"同试卷套 {a.paper_id} 四邻相邻"))
    return viols

def plan_to_dict(assigns: list[SeatAssign], unplaced: list[dict], absent_rows: list[dict],
                 viols: list[Violation], rows: int, cols: int,
                 absent_policy: str | None = DEFAULT_ABSENT_POLICY) -> dict:
    policy = effective_absent_policy(absent_policy)
    seated = sum(1 for a in assigns if a.kind == KIND_SEAT)
    reserved = sum(1 for a in absent_rows if a["status"] == "reserved")
    released = sum(1 for a in absent_rows if a["status"] == "released")
    return {
        "rows": rows,
        "cols": cols,
        "absent_policy": policy,
        "assignments": [asdict(a) for a in assigns],
        "unplaced": unplaced,
        "absent": absent_rows,
        "violations": [asdict(v) for v in viols],
        "stats": {
            "seated": seated,
            "absent_reserved": len(absent_rows),
            "absent_released": 0,
            # 占格合计：正常入座 + 缺考占格，含缺考生本人
            "occupied": len(assigns),
            "unplaced": len(unplaced),
            "violations": len(viols),
            "capacity": rows * cols,
        },
    }
