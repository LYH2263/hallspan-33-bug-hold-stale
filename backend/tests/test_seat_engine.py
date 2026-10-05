from app.services.seat_engine import (
    effective_absent_policy, find_violations, manhattan, place_candidates, SeatAssign,
)

def test_manhattan():
    assert manhattan((0, 0), (2, 1)) == 3

def test_min_distance_placement():
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1 + (i % 2)} for i in range(4)]
    assigns, unplaced, _ = place_candidates(4, 4, 2, cands)
    assert len(assigns) + len(unplaced) == 4
    for i, a in enumerate(assigns):
        for b in assigns[i+1:]:
            assert manhattan((a.row, a.col), (b.row, b.col)) >= 2

def test_same_paper_not_adjacent_in_result():
    # Force two same paper — engine should avoid 4-neigh
    cands = [
        {"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1},
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 1},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 2},
    ]
    assigns, _, _ = place_candidates(3, 3, 1, cands)
    viols = find_violations(3, 3, 1, assigns)
    assert not any(v.kind == "same_paper_adjacent" for v in viols)

def test_violation_detection():
    assigns = [
        SeatAssign(1, "A", "T1", 1, 0, 0),
        SeatAssign(2, "B", "T2", 1, 0, 1),
    ]
    viols = find_violations(2, 2, 2, assigns)
    kinds = {v.kind for v in viols}
    assert "distance" in kinds
    assert "same_paper_adjacent" in kinds

def _mixed_cands():
    return [
        {"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1, "absent": False},
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 2, "absent": True},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 1, "absent": False},
        {"id": 4, "name": "D", "ticket_no": "T4", "paper_id": 2, "absent": False},
    ]

def test_effective_policy_default_release():
    # 策略未配置按释放，兼容现网
    assert effective_absent_policy(None) == "release"
    assert effective_absent_policy("bogus") == "release"
    assert effective_absent_policy("reserve") == "reserve"
    assert effective_absent_policy("release") == "release"

def test_absent_reserve_holds_seat_row():
    assigns, unplaced, absent_rows = place_candidates(3, 3, 1, _mixed_cands(), "reserve")
    reserved = [a for a in assigns if a.kind == "absent_reserve"]
    # 每个缺考生必须占一格留账
    assert [a.candidate_id for a in reserved] == [2]
    # 该格别人不得坐
    positions = [(a.row, a.col) for a in assigns]
    assert len(set(positions)) == len(positions)
    # 未排名单不得再把缺考生当可调剂未排
    assert all(u["id"] != 2 for u in unplaced)
    assert absent_rows[0]["status"] == "reserved"
    assert (absent_rows[0]["row"], absent_rows[0]["col"]) == (reserved[0].row, reserved[0].col)

def test_absent_release_frees_seat():
    assigns, unplaced, absent_rows = place_candidates(3, 3, 1, _mixed_cands(), "release")
    # 释放空出：缺考生无占用行，座位还给后续考生
    assert all(a.candidate_id != 2 for a in assigns)
    assert all(a.kind == "seat" for a in assigns)
    assert absent_rows[0]["status"] == "released"
    assert absent_rows[0]["row"] is None
    assert all(u["id"] != 2 for u in unplaced)

def test_same_absent_row_to_no_row_on_switch():
    # 同一缺考生：占格保留时占用账有行，改释放后无行（两策略互斥）
    reserve_assigns, _, _ = place_candidates(3, 3, 1, _mixed_cands(), "reserve")
    assert any(a.candidate_id == 2 for a in reserve_assigns)
    release_assigns, _, _ = place_candidates(3, 3, 1, _mixed_cands(), "release")
    assert not any(a.candidate_id == 2 for a in release_assigns)

def test_unplaced_never_contains_absent_when_full():
    cands = [
        {"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1, "absent": True},
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 2, "absent": False},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 1, "absent": False},
    ]
    assigns, unplaced, _ = place_candidates(1, 1, 2, cands, "reserve")
    assert [a.candidate_id for a in assigns] == [1]
    assert {u["id"] for u in unplaced} == {2, 3}
