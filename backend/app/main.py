import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import shutil
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import UPLOAD_DIR
from app.db import init_db
from app.rag import index_document, clear_session
from app.router import route_query, clear_chat_history
from app.utils import validate_file
from app.chat_history import (
    create_chat,
    list_chats,
    get_chat_messages,
    add_message,
    delete_chat,
    chat_exists,
    rename_chat,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@app.get("/")
def root():
    return {"message": "Orlixa API Running"}


# ── Pydantic models ──────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: str = ""

class ChatResponse(BaseModel):
    answer: str
    source: str

class CreateChatRequest(BaseModel):
    title: Optional[str] = "New Chat"

class AddMessageRequest(BaseModel):
    chat_id: str
    role: str
    content: str
    source: Optional[str] = None

class RenameChatRequest(BaseModel):
    title: str


# ── Chat history endpoints ───────────────────────────────────────────────────

@app.post("/chats", status_code=201)
async def api_create_chat(req: CreateChatRequest):
    return create_chat(req.title or "New Chat")

@app.get("/chats")
async def api_list_chats():
    return {"chats": list_chats()}

@app.get("/chats/{chat_id}")
async def api_get_chat(chat_id: str):
    if not chat_exists(chat_id):
        raise HTTPException(404, "Chat not found")
    return {"messages": get_chat_messages(chat_id)}

@app.post("/messages", status_code=201)
async def api_add_message(req: AddMessageRequest):
    if not chat_exists(req.chat_id):
        raise HTTPException(404, "Chat not found")
    return add_message(req.chat_id, req.role, req.content, req.source)

@app.delete("/chats/{chat_id}")
async def api_delete_chat(chat_id: str):
    if not delete_chat(chat_id):
        raise HTTPException(404, "Chat not found")
    # Also clear RAG session and upload files
    clear_session(chat_id)
    clear_chat_history(chat_id)
    upload_dir = UPLOAD_DIR / chat_id
    if upload_dir.exists():
        shutil.rmtree(upload_dir)
    return {"status": "deleted"}

@app.patch("/chats/{chat_id}")
async def api_rename_chat(chat_id: str, req: RenameChatRequest):
    if not rename_chat(chat_id, req.title):
        raise HTTPException(404, "Chat not found")
    return {"status": "renamed"}


# ── RAG chat endpoint (chat_id-scoped) ───────────────────────────────────────

@app.post("/chat/{chat_id}", response_model=ChatResponse)
async def chat_scoped(chat_id: str, req: ChatRequest):
    if not chat_exists(chat_id):
        raise HTTPException(404, "Chat not found")
    if not req.message.strip():
        raise HTTPException(400, "Empty message.")

    # Persist user message
    add_message(chat_id, "user", req.message.strip())

    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(route_query, chat_id, req.message.strip()),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Request timed out.")

    # Persist assistant response
    add_message(chat_id, "assistant", result["answer"], result.get("source"))

    return ChatResponse(**result)


# ── Legacy endpoint (kept for backward compat) ───────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    req.session_id = req.session_id.strip() or uuid.uuid4().hex
    if not req.message.strip():
        raise HTTPException(400, "Empty message.")
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(route_query, req.session_id, req.message.strip()),
            timeout=60.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(504, "Request timed out.")
    return ChatResponse(**result)


# ── File upload endpoints ────────────────────────────────────────────────────

@app.post("/upload")
async def upload_file(files: List[UploadFile] = File(...), session_id: str = Form("")):
    session_id = session_id.strip() or uuid.uuid4().hex
    results = []
    for file in files:
        if not validate_file(file.filename):
            results.append({"filename": file.filename, "status": "error", "error": "Unsupported file type"})
            continue

        file.file.seek(0, 2)
        size = file.file.tell()
        if size > MAX_FILE_SIZE:
            results.append({"filename": file.filename, "status": "error", "error": "File too large (max 20MB)"})
            continue
        file.file.seek(0)

        session_upload_dir = UPLOAD_DIR / session_id
        session_upload_dir.mkdir(parents=True, exist_ok=True)
        dest = session_upload_dir / file.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)

        try:
            await asyncio.wait_for(asyncio.to_thread(index_document, session_id, str(dest)), timeout=300.0)
            results.append({"filename": file.filename, "status": "indexed"})
        except asyncio.TimeoutError:
            results.append({"filename": file.filename, "status": "error", "error": "Indexing timed out"})

    return {"results": results}


@app.get("/files")
async def list_files(session_id: str = Query("")):
    session_id = session_id.strip() or uuid.uuid4().hex
    session_upload_dir = UPLOAD_DIR / session_id
    if not session_upload_dir.exists():
        return {"files": []}
    files = [f.name for f in session_upload_dir.iterdir() if f.is_file()]
    return {"files": files}


@app.post("/clear")
async def clear(req: dict):
    session_id = req.get("session_id", "")
    if session_id:
        clear_session(session_id)
        clear_chat_history(session_id)
        upload_dir = UPLOAD_DIR / session_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
    return {"status": "cleared"}


@app.get("/health")
async def health():
    return {"status": "ok"}
