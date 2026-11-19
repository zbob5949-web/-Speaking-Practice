"""创建/提升管理员账号。

用法：
    python tools/create_admin.py 18800000000 admin123
    python tools/create_admin.py 18800000000 admin123 --super

说明：
    SpeakMate 的登录令牌统一签发 role=user，管理员权限由数据库判定：
    users.role = 'admin' 或 users.is_super_admin = 1。
    因此这里只负责把账号写进 users 表，登录流程无需改动。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "app" / "backend"
sys.path.insert(0, str(BACKEND_DIR))
# 数据库路径按工作目录相对解析，必须先切到后端目录，
# 否则会在仓库根目录下另外建一个空的 data/coach.sqlite。
os.chdir(BACKEND_DIR)

from app.config import load_settings  # noqa: E402
from app.db import connect, init_db  # noqa: E402
from app.security import hash_password  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="创建或提升 SpeakMate 管理员账号")
    parser.add_argument("phone", help="手机号，例如 18800000000")
    parser.add_argument("password", help="密码，至少 6 位")
    parser.add_argument("--super", action="store_true", help="同时设为超级管理员")
    args = parser.parse_args()

    if len(args.password) < 6:
        print("密码至少 6 位")
        return 1

    settings = load_settings()
    init_db(settings.database_path)

    connection = connect(settings.database_path)
    try:
        row = connection.execute("SELECT id, role FROM users WHERE phone = ?", (args.phone,)).fetchone()
        if row is None:
            connection.execute(
                "INSERT INTO users (phone, password, role, is_active, is_super_admin) VALUES (?, ?, 'admin', 1, ?)",
                (args.phone, hash_password(args.password), 1 if args.super else 0),
            )
            print(f"已创建管理员: {args.phone}")
        else:
            connection.execute(
                "UPDATE users SET role = 'admin', is_active = 1, password = ?, is_super_admin = CASE WHEN ? THEN 1 ELSE is_super_admin END "
                "WHERE id = ?",
                (hash_password(args.password), 1 if args.super else 0, row["id"]),
            )
            print(f"已提升为管理员并重置密码: {args.phone}")
        connection.commit()
    finally:
        connection.close()

    print(f"数据库: {settings.database_path}")
    print("登录后用返回的 access_token 访问 /admin/* 接口即可。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
