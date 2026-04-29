import uuid
from app.db import get_conn

def ensure_default_template(user_id: str):
    conn = get_conn()
    # Check if any template exists for this user
    row = conn.execute("SELECT 1 FROM templates WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        template_id = uuid.uuid4().hex
        conn.execute(
            """
            INSERT INTO templates (id, user_id, name, tone, instructions, is_default) 
            VALUES (?, ?, 'Default Assistant', 'Helpful & Professional', 'You are a highly capable AI assistant. Provide accurate, clear, and professional responses.', 1)
            """,
            (template_id, user_id)
        )
        conn.commit()
    conn.close()

def create_template(user_id: str, name: str, tone: str, instructions: str, is_default: bool = False):
    conn = get_conn()
    if is_default:
        conn.execute("UPDATE templates SET is_default=0 WHERE user_id=?", (user_id,))
    
    template_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO templates (id, user_id, name, tone, instructions, is_default) VALUES (?, ?, ?, ?, ?, ?)",
        (template_id, user_id, name, tone, instructions, 1 if is_default else 0)
    )
    conn.commit()
    row = conn.execute("SELECT * FROM templates WHERE id=?", (template_id,)).fetchone()
    conn.close()
    return dict(row)

def list_templates(user_id: str):
    ensure_default_template(user_id)
    conn = get_conn()
    rows = conn.execute("SELECT * FROM templates WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_template(user_id: str, template_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM templates WHERE id=? AND user_id=?", (template_id, user_id)).fetchone()
    conn.close()
    return dict(row) if row else None

def get_chat_template(chat_id: str):
    """Fetch the template assigned to a specific chat, or the user's default template."""
    conn = get_conn()
    # First try to get the chat-specific template
    row = conn.execute(
        """
        SELECT t.* 
        FROM templates t
        JOIN chats c ON c.template_id = t.id
        WHERE c.id = ?
        """,
        (chat_id,)
    ).fetchone()
    
    if not row:
        # Fallback to the user's default template for that chat's user
        row = conn.execute(
            """
            SELECT t.* 
            FROM templates t
            JOIN chats c ON c.user_id = t.user_id
            WHERE c.id = ? AND t.is_default = 1
            """,
            (chat_id,)
        ).fetchone()
        
    conn.close()
    return dict(row) if row else None

def update_template(user_id: str, template_id: str, name: str, tone: str, instructions: str, is_default: bool):
    conn = get_conn()
    if is_default:
        conn.execute("UPDATE templates SET is_default=0 WHERE user_id=?", (user_id,))
    
    conn.execute(
        "UPDATE templates SET name=?, tone=?, instructions=?, is_default=? WHERE id=? AND user_id=?",
        (name, tone, instructions, 1 if is_default else 0, template_id, user_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_template(user_id: str, template_id: str):
    conn = get_conn()
    # Don't delete the last default template
    row = conn.execute("SELECT is_default FROM templates WHERE id=?", (template_id,)).fetchone()
    if row and row["is_default"]:
        # Find another template to make default if possible
        other = conn.execute("SELECT id FROM templates WHERE user_id=? AND id != ?", (user_id, template_id)).fetchone()
        if other:
            conn.execute("UPDATE templates SET is_default=1 WHERE id=?", (other["id"],))
        else:
            conn.close()
            return False # Cannot delete the only template
            
    conn.execute("DELETE FROM templates WHERE id=? AND user_id=?", (template_id, user_id))
    conn.commit()
    conn.close()
    return True

def set_chat_template(user_id: str, chat_id: str, template_id: str | None):
    conn = get_conn()
    conn.execute(
        "UPDATE chats SET template_id=? WHERE id=? AND user_id=?",
        (template_id, chat_id, user_id)
    )
    conn.commit()
    conn.close()
    return True
