import hashlib
import sqlite3
from app.config import CACHE_DB

def _conn():
    conn = sqlite3.connect(str(CACHE_DB))
    conn.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, answer TEXT, source TEXT)")
    conn.execute("CREATE TABLE IF NOT EXISTS chat_memory (session_id TEXT, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("CREATE TABLE IF NOT EXISTS refined_query_cache (key TEXT PRIMARY KEY, refined_query TEXT)")
    return conn

def _hash(session_id: str, q: str, context: str = "") -> str:
    return hashlib.md5((session_id + q.strip().lower() + context).encode()).hexdigest()

def _refined_query_hash(question: str, context: str = "") -> str:
    return hashlib.md5(("refine::" + question.strip().lower() + context).encode()).hexdigest()

def get_cached(session_id: str, question: str, context: str = ""):
    conn = _conn()
    row = conn.execute("SELECT answer, source FROM cache WHERE key=?", (_hash(session_id, question, context),)).fetchone()
    conn.close()
    if row:
        return {"answer": row[0], "source": row[1]}
    return None

def store_cache(session_id: str, question: str, answer: str, source: str, context: str = ""):
    conn = _conn()
    conn.execute("INSERT OR REPLACE INTO cache (key, answer, source) VALUES (?,?,?)",
                 (_hash(session_id, question, context), answer, source))
    conn.commit()
    conn.close()

def get_cached_refined_query(question: str, context: str = ""):
    conn = _conn()
    row = conn.execute(
        "SELECT refined_query FROM refined_query_cache WHERE key=?",
        (_refined_query_hash(question, context),),
    ).fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def store_refined_query(question: str, refined_query: str, context: str = ""):
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO refined_query_cache (key, refined_query) VALUES (?, ?)",
        (_refined_query_hash(question, context), refined_query),
    )
    conn.commit()
    conn.close()

def add_history(session_id: str, role: str, content: str):
    conn = _conn()
    conn.execute("INSERT INTO chat_memory (session_id, role, content) VALUES (?,?,?)", (session_id, role, content))
    conn.commit()
    conn.close()

def get_history(session_id: str) -> list:
    conn = _conn()
    rows = conn.execute("SELECT role, content FROM chat_memory WHERE session_id=? ORDER BY timestamp ASC", (session_id,)).fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows[-10:]]

def clear_history(session_id: str):
    conn = _conn()
    conn.execute("DELETE FROM chat_memory WHERE session_id=?", (session_id,))
    conn.commit()
    conn.close()
