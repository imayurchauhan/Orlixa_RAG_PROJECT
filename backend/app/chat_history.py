import uuid
from datetime import datetime
from app.db import get_conn


def create_chat(title: str = "New Chat") -> dict:
    conn = get_conn()
    chat_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO chats (id, title) VALUES (?, ?)",
        (chat_id, title),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
    conn.close()
    return dict(row)


def list_chats() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM chats ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat_messages(chat_id: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM messages WHERE chat_id=? ORDER BY created_at ASC",
        (chat_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_message(chat_id: str, role: str, content: str, source: str | None = None) -> dict:
    conn = get_conn()
    msg_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO messages (id, chat_id, role, content, source) VALUES (?,?,?,?,?)",
        (msg_id, chat_id, role, content, source),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM messages WHERE id=?", (msg_id,)).fetchone()
    conn.close()
    return dict(row)


def delete_chat(chat_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM chats WHERE id=?", (chat_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def chat_exists(chat_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM chats WHERE id=?", (chat_id,)).fetchone()
    conn.close()
    return row is not None


def rename_chat(chat_id: str, title: str) -> bool:
    conn = get_conn()
    cur = conn.execute("UPDATE chats SET title=? WHERE id=?", (title, chat_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0
