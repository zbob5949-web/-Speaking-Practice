from app.db import init_db, connect
import sqlite3

def test_new_tables_exist(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with connect(db_path) as conn:
        tables = [row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        assert "daily_reviews" in tables
        assert "memory_items" in tables
        assert "plan_adjustments" in tables
        assert "practice_briefs" in tables


def test_agent_runs_table_exists(tmp_path):
    db_path = tmp_path / "test.db"
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_runs'"
        ).fetchone()
    assert row is not None

def test_new_prompts_seeded(tmp_path):
    pass # Prompts are no longer seeded by init_db, they are loaded dynamically
