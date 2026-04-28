import os
import re
import shutil
import numpy as np
import faiss
import pickle
from pypdf import PdfReader
from docx import Document
from rank_bm25 import BM25Okapi
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnableLambda
from app.config import (
    VECTOR_DIR,
    EMBED_MODEL,
    RERANK_MODEL,
    ENABLE_RERANK,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

SIMILARITY_THRESHOLD = 0.65

_models = {"embed": None, "rerank": None}  # type: ignore

# Per-session storage
_sessions = {}

def _get_models():
    global _models
    if _models["embed"] is None:
        from sentence_transformers import SentenceTransformer

        _models["embed"] = SentenceTransformer(EMBED_MODEL, device="cpu")  # type: ignore
    if ENABLE_RERANK and _models["rerank"] is None:
        from sentence_transformers import CrossEncoder

        _models["rerank"] = CrossEncoder(RERANK_MODEL, device="cpu")  # type: ignore
    return _models

def _session_dir(session_id: str):
    d = VECTOR_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def _get_session(session_id: str) -> dict:
    if session_id in _sessions:
        return _sessions[session_id]
    sess = {"index": None, "chunks": [], "bm25": None}
    idx_p = _session_dir(session_id) / "faiss.index"
    ch_p = _session_dir(session_id) / "chunks.npy"
    bm25_p = _session_dir(session_id) / "bm25.pkl"
    if idx_p.exists() and ch_p.exists():
        sess["index"] = faiss.read_index(str(idx_p))
        sess["chunks"] = list(np.load(str(ch_p), allow_pickle=True))
    if bm25_p.exists():
        with open(bm25_p, "rb") as f:
            sess["bm25"] = pickle.load(f)
    _sessions[session_id] = sess
    return sess

def _save_session(session_id: str):
    sess = _sessions[session_id]
    d = _session_dir(session_id)
    faiss.write_index(sess["index"], str(d / "faiss.index"))
    np.save(str(d / "chunks.npy"), np.array(sess["chunks"], dtype=object))
    if sess["bm25"] is not None:
        with open(d / "bm25.pkl", "wb") as f:
            pickle.dump(sess["bm25"], f)

def _clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned.append("")
            continue
        chars = stripped.split(" ")
        if len(chars) > 3 and all(len(c) <= 2 for c in chars if c):
            joined = "".join(chars)
            joined = re.sub(r'([a-z])([A-Z])', r'\1 \2', joined)
            joined = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', joined)
            cleaned.append(joined)
        else:
            cleaned.append(stripped)
    result = "\n".join(cleaned)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def load_pdf(path: str) -> str:
    reader = PdfReader(path)
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    return _clean_text(text)

def load_docx(path: str) -> str:
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

def load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

LOADERS = {".pdf": load_pdf, ".docx": load_docx, ".txt": load_txt}

def extract_text(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ""
    loader = LOADERS.get(ext)
    if not loader:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader(path)

def split_text(text: str) -> list:
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    return splitter.split_text(text)

def index_document(session_id: str, file_path: str):
    text = extract_text(file_path)
    raw_chunks = split_text(text)
    if not raw_chunks:
        return
        
    filename = os.path.basename(file_path)
    new_chunks = [f"[File: {filename}]\n{chunk}" for chunk in raw_chunks]
    models = _get_models()
    embeddings = models["embed"].encode(  # type: ignore
        new_chunks,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    dim = embeddings.shape[1]
    sess = _get_session(session_id)
    if sess["index"] is None:
        sess["index"] = faiss.IndexFlatIP(dim)
        sess["chunks"] = []
    sess["index"].add(np.array(embeddings, dtype=np.float32))  # type: ignore
    sess["chunks"].extend(new_chunks)
    
    tokenized_corpus = [doc.lower().split(" ") for doc in sess["chunks"]]
    sess["bm25"] = BM25Okapi(tokenized_corpus)
    
    _save_session(session_id)

def retrieve_chunks(session_id: str, query: str):
    sess = _get_session(session_id)
    if sess["index"] is None or sess["index"].ntotal == 0:
        return "NOT_FOUND"
    
    models = _get_models()
    q_emb = models["embed"].encode(  # type: ignore
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    k = min(10, sess["index"].ntotal)
    
    # FAISS retrieval
    faiss_scores, faiss_indices = sess["index"].search(np.array(q_emb, dtype=np.float32), k)
    faiss_results = faiss_indices[0]
    
    # BM25 retrieval
    tokenized_query = query.lower().split(" ")
    bm25_scores = sess["bm25"].get_scores(tokenized_query)
    bm25_indices = np.argsort(bm25_scores)[::-1][:k]
    
    # Reciprocal Rank Fusion (RRF)
    rrf_k = 60
    rrf_scores = {}
    for rank, idx in enumerate(faiss_results):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
    for rank, idx in enumerate(bm25_indices):
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        
    sorted_fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    top_candidates = [idx for idx, score in sorted_fused[:10]]
    candidate_chunks = [sess["chunks"][i] for i in top_candidates if i < len(sess["chunks"])]
    
    final_chunks = candidate_chunks[:3]
    best_score = rrf_scores.get(top_candidates[0], 0.0) if top_candidates else 0.0

    reranker = models.get("rerank")
    if reranker is not None and len(candidate_chunks) > 1:
        pairs = [[query, chunk] for chunk in candidate_chunks]
        rerank_scores = reranker.predict(pairs)  # type: ignore
        top_3_indices = np.argsort(rerank_scores)[::-1][:3]
        final_chunks = [candidate_chunks[i] for i in top_3_indices]
        if len(rerank_scores) > 0:
            best_score = float(rerank_scores[top_3_indices[0]])
    
    # Context Size limit
    total_len = 0
    trimmed_chunks = []
    for c in final_chunks:
        if total_len + len(c) > 6000:
            break
        trimmed_chunks.append(c)
        total_len += len(c)
        
    if reranker is not None:
        print("RERANK COMPLETE")
    return trimmed_chunks, best_score

def _document_pipeline_func(inputs: dict):
    return retrieve_chunks(inputs["session_id"], inputs["query"])

document_pipeline = RunnableLambda(_document_pipeline_func)

def has_documents(session_id: str) -> bool:
    sess = _get_session(session_id)
    return sess["index"] is not None and sess["index"].ntotal > 0

def clear_session(session_id: str):
    _sessions.pop(session_id, None)
    d = _session_dir(session_id)
    if d.exists():
        shutil.rmtree(d)
