"""独立、幂等的管理模块初始化，不触碰现有业务数据。"""
from contextlib import contextmanager

from app.config import load_settings
from app.db import SCHEMA, connect


@contextmanager
def database():
    connection = connect(load_settings().database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.executescript(SCHEMA)
        connection.execute("""
            CREATE TABLE IF NOT EXISTS admin_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_id INTEGER,
                action TEXT NOT NULL,
                table_name TEXT,
                record_id TEXT,
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_admin_audit_time ON admin_audit_logs(created_at)")
        connection.commit()
        with connection:
            yield connection
    finally:
        connection.close()
