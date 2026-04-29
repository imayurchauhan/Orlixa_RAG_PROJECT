import sqlite3
from app.config import CHAT_DB


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(CHAT_DB), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT,
            google_sub TEXT UNIQUE,
            full_name TEXT,
            avatar_url TEXT,
            auth_provider TEXT NOT NULL DEFAULT 'email',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chats (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    chat_columns = {row["name"] for row in conn.execute("PRAGMA table_info(chats)").fetchall()}
    if "user_id" not in chat_columns:
        conn.execute("ALTER TABLE chats ADD COLUMN user_id TEXT")

    user_indexes = {
        row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name IS NOT NULL"
        ).fetchall()
    }
    if "idx_chats_user_id" not in user_indexes:
        conn.execute("CREATE INDEX idx_chats_user_id ON chats(user_id)")
    if "idx_messages_chat_id" not in user_indexes:
        conn.execute("CREATE INDEX idx_messages_chat_id ON messages(chat_id)")
    conn.commit()
    conn.close()
