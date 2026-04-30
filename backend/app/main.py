import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import shutil
import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import UPLOAD_DIR
from app.db import init_db
from app.rag import index_document, clear_session
from app.router import route_query, clear_chat_history
from app.utils import validate_file
from app.auth import (
    create_user,
    authenticate_user,
    build_auth_response,
    get_current_user,
    generate_otp,
    verify_otp,
)
from app.chat_history import (
    create_chat,
    list_chats,
    get_chat_messages,
    add_message,
    delete_chat,
    chat_exists,
    rename_chat,
    ensure_chat,
    clear_chat_messages,
)
from app.template_manager import (
    list_templates,
    create_template,
    update_template,
    delete_template,
    set_chat_template,
    get_template,
    ensure_default_template,
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

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class OtpRequest(BaseModel):
    email: str

class OtpVerifyRequest(BaseModel):
    email: str
    otp_code: str

class TemplateRequest(BaseModel):
    name: str
    tone: Optional[str] = ""
    instructions: str
    is_default: Optional[bool] = False

class SetChatTemplateRequest(BaseModel):
    template_id: Optional[str] = None


@app.post("/auth/register", status_code=201)
async def api_register(req: RegisterRequest):
    result = create_user(req.email, req.password, req.full_name or "")
    if result.get("requires_otp"):
        return result
    return build_auth_response(result)


@app.post("/auth/login")
async def api_login(req: LoginRequest):
    result = authenticate_user(req.email, req.password)
    if result.get("requires_otp"):
        return result
    return build_auth_response(result)


@app.post("/auth/otp/request")
async def api_otp_request(req: OtpRequest):
    generate_otp(req.email)
    return {"message": "OTP sent successfully"}


@app.post("/auth/otp/verify")
async def api_otp_verify(req: OtpVerifyRequest):
    user = verify_otp(req.email, req.otp_code)
    return build_auth_response(user)


@app.get("/auth/me")
async def api_me(current_user: dict = Depends(get_current_user)):
    ensure_default_template(current_user["id"])
    return {"user": current_user}


# ── Chat history endpoints ───────────────────────────────────────────────────

@app.post("/chats", status_code=201)
async def api_create_chat(req: CreateChatRequest, current_user: dict = Depends(get_current_user)):
    return create_chat(current_user["id"], req.title or "New Chat")

@app.get("/chats")
async def api_list_chats(current_user: dict = Depends(get_current_user)):
    return {"chats": list_chats(current_user["id"])}

@app.get("/chats/{chat_id}")
async def api_get_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    if not chat_exists(current_user["id"], chat_id):
        return {"messages": []}
    return {"messages": get_chat_messages(current_user["id"], chat_id)}

@app.post("/messages", status_code=201)
async def api_add_message(req: AddMessageRequest, current_user: dict = Depends(get_current_user)):
    if not chat_exists(current_user["id"], req.chat_id):
        ensure_chat(current_user["id"], req.chat_id)
    return add_message(req.chat_id, req.role, req.content, req.source)

@app.delete("/chats/{chat_id}")
async def api_delete_chat(chat_id: str, current_user: dict = Depends(get_current_user)):
    deleted = delete_chat(current_user["id"], chat_id)
    if deleted:
        clear_session(chat_id)
        clear_chat_history(chat_id)
        upload_dir = UPLOAD_DIR / chat_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
    return {"status": "deleted"}

@app.patch("/chats/{chat_id}")
async def api_rename_chat(chat_id: str, req: RenameChatRequest, current_user: dict = Depends(get_current_user)):
    if not rename_chat(current_user["id"], chat_id, req.title):
        raise HTTPException(404, "Chat not found")
    return {"status": "renamed"}

@app.post("/chats/{chat_id}/clear")
async def api_clear_chat_messages(chat_id: str, current_user: dict = Depends(get_current_user)):
    """Clear all messages from a chat without deleting the chat itself."""
    if not clear_chat_messages(current_user["id"], chat_id):
        raise HTTPException(404, "Chat not found")
    clear_session(chat_id)
    clear_chat_history(chat_id)
    return {"status": "cleared"}


# ── Template endpoints ───────────────────────────────────────────────────────

@app.get("/templates")
async def api_list_templates(current_user: dict = Depends(get_current_user)):
    return {"templates": list_templates(current_user["id"])}

@app.post("/templates", status_code=201)
async def api_create_template(req: TemplateRequest, current_user: dict = Depends(get_current_user)):
    return create_template(current_user["id"], req.name, req.tone or "", req.instructions, req.is_default or False)

@app.put("/templates/{template_id}")
async def api_update_template(template_id: str, req: TemplateRequest, current_user: dict = Depends(get_current_user)):
    if not update_template(current_user["id"], template_id, req.name, req.tone or "", req.instructions, req.is_default or False):
        raise HTTPException(404, "Template not found")
    return {"status": "updated"}

@app.delete("/templates/{template_id}")
async def api_delete_template(template_id: str, current_user: dict = Depends(get_current_user)):
    if not delete_template(current_user["id"], template_id):
        raise HTTPException(400, "Cannot delete template")
    return {"status": "deleted"}

@app.post("/chats/{chat_id}/template")
async def api_set_chat_template(chat_id: str, req: SetChatTemplateRequest, current_user: dict = Depends(get_current_user)):
    if not set_chat_template(current_user["id"], chat_id, req.template_id):
        raise HTTPException(404, "Chat not found")
    
    # Add a system message notifying the chat of the persona change
    template = get_template(current_user["id"], req.template_id)
    if template:
        add_message(chat_id, "system", f"Persona switched to **{template['name']}** ({template['tone']})")
        
    return {"status": "template_updated"}


# ── RAG chat endpoint (chat_id-scoped) ───────────────────────────────────────

@app.post("/chat/{chat_id}", response_model=ChatResponse)
async def chat_scoped(chat_id: str, req: ChatRequest, current_user: dict = Depends(get_current_user)):
    if not chat_exists(current_user["id"], chat_id):
        ensure_chat(current_user["id"], chat_id)
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
    except Exception as e:
        print(f"ERROR IN ROUTE_QUERY: {str(e)}")
        # Return a meaningful error to the UI
        return ChatResponse(
            answer=f"I encountered an error while processing your request: {str(e)}. Please check your configuration or try again.",
            source="system"
        )

    # Persist assistant response
    add_message(chat_id, "assistant", result["answer"], result.get("source"))

    return ChatResponse(**result)


# ── Legacy endpoint (kept for backward compat) ───────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    req.session_id = req.session_id.strip() or uuid.uuid4().hex
    if not chat_exists(current_user["id"], req.session_id):
        ensure_chat(current_user["id"], req.session_id)
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
async def upload_file(
    files: List[UploadFile] = File(...),
    session_id: str = Form(""),
    current_user: dict = Depends(get_current_user),
):
    session_id = session_id.strip() or uuid.uuid4().hex
    if not chat_exists(current_user["id"], session_id):
        ensure_chat(current_user["id"], session_id)
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
async def list_files(session_id: str = Query(""), current_user: dict = Depends(get_current_user)):
    session_id = session_id.strip() or uuid.uuid4().hex
    if not chat_exists(current_user["id"], session_id):
        return {"files": []}
    session_upload_dir = UPLOAD_DIR / session_id
    if not session_upload_dir.exists():
        return {"files": []}
    files = [f.name for f in session_upload_dir.iterdir() if f.is_file()]
    return {"files": files}


@app.post("/clear")
async def clear(req: dict, current_user: dict = Depends(get_current_user)):
    session_id = req.get("session_id", "")
    if session_id and chat_exists(current_user["id"], session_id):
        clear_session(session_id)
        clear_chat_history(session_id)
        upload_dir = UPLOAD_DIR / session_id
        if upload_dir.exists():
            shutil.rmtree(upload_dir)
    return {"status": "cleared"}


@app.get("/health")
async def health():
    return {"status": "ok"}
