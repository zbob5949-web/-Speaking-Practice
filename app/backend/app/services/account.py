"""Account preferences and favorites scoped to the authenticated identity."""
from fastapi import HTTPException
from app.context import current_user_id
from app.services.auth_service import _connection

AVATARS = {"fox": "🦊", "cat": "🐱", "panda": "🐼", "rabbit": "🐰", "koala": "🐨", "penguin": "🐧"}

def owner():
    key = current_user_id.get()
    if not key:
        raise HTTPException(401, "请先登录")
    return key

def account():
    key = owner()
    with _connection() as conn:
        row = conn.execute("SELECT username, avatar FROM users WHERE phone = ?", (key,)).fetchone()
        if row is None:
            row = conn.execute("SELECT username, avatar FROM account_preferences WHERE owner_key = ?", (key,)).fetchone()
    return {**(dict(row) if row else {"username": "英语学习者", "avatar": "fox"}), "is_guest": key.startswith("guest_"), "avatars": AVATARS}

def update(username, avatar):
    key = owner()
    with _connection() as conn:
        if conn.execute("SELECT id FROM users WHERE phone = ?", (key,)).fetchone():
            conn.execute("UPDATE users SET username = ?, avatar = ? WHERE phone = ?", (username, avatar, key))
        else:
            conn.execute("INSERT INTO account_preferences(owner_key, username, avatar) VALUES (?, ?, ?) ON CONFLICT(owner_key) DO UPDATE SET username=excluded.username, avatar=excluded.avatar", (key, username, avatar))
    return account()

def favorite_rows():
    with _connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM account_favorites WHERE owner_key = ? ORDER BY id DESC", (owner(),))]
