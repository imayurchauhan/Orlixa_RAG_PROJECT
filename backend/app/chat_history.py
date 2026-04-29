import uuid
from fastapi import HTTPException
from app.db import get_conn


def create_chat(user_id: str, title: str = "New Chat") -> dict:
    conn = get_conn()
    chat_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO chats (id, title, user_id) VALUES (?, ?, ?)",
        (chat_id, title, user_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM chats WHERE id=?", (chat_id,)).fetchone()
    conn.close()
    return dict(row)


def list_chats(user_id: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM chats WHERE user_id=? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat_messages(user_id: str, chat_id: str) -> list:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT m.*
        FROM messages m
        JOIN chats c ON c.id = m.chat_id
        WHERE m.chat_id=? AND c.user_id=?
        ORDER BY m.created_at ASC
        """,
        (chat_id, user_id),
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


def delete_chat(user_id: str, chat_id: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM chats WHERE id=? AND user_id=?", (chat_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def chat_exists(user_id: str, chat_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT 1 FROM chats WHERE id=? AND user_id=?", (chat_id, user_id)).fetchone()
    conn.close()
    return row is not None


def rename_chat(user_id: str, chat_id: str, title: str) -> bool:
    conn = get_conn()
    cur = conn.execute("UPDATE chats SET title=? WHERE id=? AND user_id=?", (title, chat_id, user_id))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def ensure_chat(user_id: str, chat_id: str, title: str = "New Chat") -> dict:
    conn = get_conn()
    conn.execute(
        "INSERT OR IGNORE INTO chats (id, title, user_id) VALUES (?, ?, ?)",
        (chat_id, title, user_id),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM chats WHERE id=? AND user_id=?",
        (chat_id, user_id),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=403, detail="Chat does not belong to the current user")
    return dict(row)


def clear_chat_messages(user_id: str, chat_id: str) -> bool:
    """Clear all messages from a chat without deleting the chat itself."""
    conn = get_conn()
    # First verify the chat belongs to the user
    chat = conn.execute(
        "SELECT 1 FROM chats WHERE id=? AND user_id=?",
        (chat_id, user_id),
    ).fetchone()
    if chat is None:
        conn.close()
        return False
    # Delete all messages in the chat
    cur = conn.execute("DELETE FROM messages WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0
