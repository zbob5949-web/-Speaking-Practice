from app.repositories import CoachRepository
from app.db import init_db

def test_get_or_create_session_resumes_same_day(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    s1 = repo.get_or_create_session(plan_day_id=1, day_index=1, topic="Topic 1")
    repo.add_turn(s1["id"], "user", "Hello")
    
    s2 = repo.get_or_create_session(plan_day_id=1, day_index=1, topic="Topic 1")
    assert s1["id"] == s2["id"]
    
    turns = repo.get_turns(s2["id"])
    assert len(turns) == 1

def test_get_or_create_session_isolates_different_plan_days(tmp_path):
    db_path = tmp_path / "coach.sqlite"
    init_db(db_path)
    repo = CoachRepository(db_path)
    
    # Session for plan day 1 (Profile A's Day 1)
    s1 = repo.get_or_create_session(plan_day_id=1, day_index=1, topic="Profile A Topic")
    
    # Session for plan day 2 (Profile B's Day 1)
    s2 = repo.get_or_create_session(plan_day_id=2, day_index=1, topic="Profile B Topic")
    
    assert s1["id"] != s2["id"]

