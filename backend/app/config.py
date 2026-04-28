import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
VECTOR_DIR = BASE_DIR / "vectorstore"
CACHE_DB = BASE_DIR / "backend" / "cache.db"
CHAT_DB = BASE_DIR / "backend" / "chat_history.db"
EMBED_MODEL = "all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
ENABLE_RERANK = os.getenv("ENABLE_RERANK", "false").lower() == "true"
LLM_MODEL = "llama-3.1-8b-instant"
TOP_K = 3
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
