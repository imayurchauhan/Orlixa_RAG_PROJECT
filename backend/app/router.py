from langchain_core.tools import tool
from app.rag import document_pipeline, has_documents
from app.config import UPLOAD_DIR
from app.web_search import web_search_tool
from app.llm import generate_answer
from app.query_refiner import refine_query
from app.cache import get_cached, store_cache, get_history, add_history as add_history_db, clear_history

# Phrases that indicate the LLM does not know the answer
_UNCERTAIN_PHRASES = [
    "NOT_FOUND", "NOT FOUND",
    "I DON'T KNOW", "I DO NOT KNOW",
    "I'M NOT SURE", "I AM NOT SURE",
    "I'M NOT AWARE", "I AM NOT AWARE",
    "I DON'T HAVE ACCESS", "I DO NOT HAVE ACCESS",
    "I'M UNABLE TO PROVIDE", "I AM UNABLE TO PROVIDE",
    "I CANNOT PROVIDE REAL-TIME",
    "VISIT THE OFFICIAL", "FOLLOW THE LIVE", "SCORECARD ON", "AVAILABLE ON",
    "CHECK THE LATEST", "REAL-TIME UPDATES", "BALL-BY-BALL",
]
_FINAL_FALLBACK_ANSWER = "I could not find a reliable answer. Please try rephrasing your question."
_LIVE_QUERY_TERMS = (
    "live",
    "today",
    "yesterday",
    "current",
    "now",
    "latest",
    "score",
    "scores",
    "result",
    "results",
    "winner",
    "who won",
    "match update",
    "weather",
    "stock",
    "stocks",
    "price",
    "prices",
    "breaking news",
    "news update",
    "recent",
    "this week",
    "this month",
)
_ACKNOWLEDGEMENT_REPLIES = {
    "ok": "Okay.",
    "okay": "Okay.",
    "k": "Okay.",
    "alright": "Alright.",
    "all right": "Alright.",
    "fine": "Okay.",
    "cool": "Cool.",
    "got it": "Got it.",
    "understood": "Understood.",
    "noted": "Noted.",
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
    "ok thanks": "You're welcome.",
    "okay thanks": "You're welcome.",
    "thanks okay": "You're welcome.",
}
_LEAVE_IT_PHRASES = {
    "leave it",
    "leave it for now",
    "ok leave it",
    "okay leave it",
    "ok, leave it",
    "okay, leave it",
    "its ok leave it",
    "it's ok leave it",
    "skip it",
    "forget it",
    "nevermind",
    "never mind",
}
_EXIT_PHRASES = {"bye", "ok bye", "goodbye", "exit", "quit", "end chat", "end session", "see you"}

def get_history_str(session_id: str) -> str:
    hist = get_history(session_id)
    if not hist:
        return ""
    return "Chat History:\n" + "\n".join([f"{m['role']}: {m['content']}" for m in hist]) + "\n\n"

def add_history(session_id: str, question: str, answer: str):
    add_history_db(session_id, "User", question)
    add_history_db(session_id, "Assistant", answer)

def clear_chat_history(session_id: str):
    clear_history(session_id)

def _is_uncertain(answer: str) -> bool:
    """Check if the LLM response indicates uncertainty or missing knowledge."""
    # Normalize curly/smart apostrophes to straight ones
    upper = answer.upper().strip().replace("\u2018", "'").replace("\u2019", "'")
    for phrase in _UNCERTAIN_PHRASES:
        if phrase in upper:
            return True
    return False

def _is_live_or_time_sensitive(question: str) -> bool:
    """Return True if either the original OR refined question looks time-sensitive."""
    lowered = question.lower()
    # Also detect common misspellings of 'yesterday'
    import re
    if re.search(r"yest[a-z]*day", lowered):
        return True
    return any(term in lowered for term in _LIVE_QUERY_TERMS)

def _is_non_reusable_cached_answer(answer: str) -> bool:
    return answer.strip() == _FINAL_FALLBACK_ANSWER

def _get_conversational_reply(question: str):
    normalized = " ".join(question.strip().lower().split())
    if not normalized:
        return None
    if normalized in _EXIT_PHRASES:
        return {"answer": "Goodbye! I'll be here whenever you're ready to continue our chat.", "source": "system"}
    if normalized in _LEAVE_IT_PHRASES:
        return {"answer": "Okay, we can leave it here. Let me know if you want to ask something else.", "source": "system"}
    if normalized in _ACKNOWLEDGEMENT_REPLIES:
        return {"answer": _ACKNOWLEDGEMENT_REPLIES[normalized], "source": "system"}
    return None

def _get_session_images(session_id: str):
    session_upload_dir = UPLOAD_DIR / session_id
    if not session_upload_dir.exists():
        return []
    images = []
    for f in session_upload_dir.iterdir():
        if f.is_file() and f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            images.append(str(f))
    return images

def _try_document(session_id: str, question: str, history: str, images: list = None):
    """Step 1: Try document retrieval."""
    res = document_pipeline.invoke({"session_id": session_id, "query": question})
    if res == "NOT_FOUND":
        return None

    chunks, score = res
    if not chunks:
        return None

    context = "\n".join(chunks)
    answer = generate_answer(context, question, "document", history, images=images)
    if _is_uncertain(answer):
        return None
    return {"answer": answer, "source": "document"}

def _try_llm(question: str, history: str, images: list = None):
    """Step 2: Try direct LLM answer."""
    answer = generate_answer("", question, "general", history, images=images)
    if _is_uncertain(answer):
        print(f"LLM UNCERTAIN -> triggering web fallback for: {question}")
        return None
    return {"answer": answer, "source": "llm"}

def _try_web(question: str, history: str, images: list = None, original_question: str = ""):
    """Step 3: Web search fallback."""
    # Use the refined question for search (cleaner), but fall back to original if empty
    search_q = question if question.strip() else (original_question or question)
    context = web_search_tool.invoke({"query": search_q})
    if not context:
        return None
    answer = generate_answer(context, question, "web", history, images=images)
    if not answer or _is_uncertain(answer):
        return None
    return {"answer": answer, "source": "web"}

def route_query(session_id: str, question: str) -> dict:
    print(f"SESSION: {session_id}")
    history = get_history_str(session_id)
    original_question = question.strip()
    conversational_reply = _get_conversational_reply(original_question)
    if conversational_reply:
        add_history(session_id, original_question, conversational_reply["answer"])
        return conversational_reply

    refined_question = refine_query(original_question, history)
    print("ORIGINAL QUERY:", original_question)
    print("REFINED QUERY:", refined_question)
    question = refined_question
    images = _get_session_images(session_id)

    # Check time-sensitivity on BOTH original and refined query so typos/bad prompts still work
    is_live = _is_live_or_time_sensitive(original_question) or _is_live_or_time_sensitive(refined_question)
    use_answer_cache = not images and not is_live

    if use_answer_cache:
        cached = get_cached(session_id, original_question, history)
        if cached and not _is_non_reusable_cached_answer(cached["answer"]):
            add_history(session_id, original_question, cached["answer"])
            return cached

    result = None

    is_image_query = any(word in original_question.lower() for word in ["picture", "image", "photo", "screenshot", "pic"])

    # Step 1: Document retrieval
    # Only retrieve docs if they exist, AND the user isn't explicitly asking about a picture/image when we have images.
    if has_documents(session_id) and not (is_image_query and images):
        result = _try_document(session_id, question, history, images=images)

    if not result and images:
        # Images present but no docs (or we skipped docs) — try vision LLM
        result = _try_llm(question, history, images=images)

    # Step 2: For live/time-sensitive queries, go straight to web search (skip LLM hallucination)
    if not result and is_live:
        print(f"LIVE QUERY DETECTED -> Prioritizing web search: {question}")
        result = _try_web(question, history, original_question=original_question)

    # Step 3: LLM direct answer for general knowledge
    if not result:
        result = _try_llm(question, history)

    # Step 4: Web fallback if LLM was uncertain
    if not result:
        result = _try_web(question, history, original_question=original_question)

    # Final fallback
    if not result:
        result = {"answer": _FINAL_FALLBACK_ANSWER, "source": "web"}

    print(f"SOURCE USED: {result['source']}")
    if use_answer_cache and not _is_non_reusable_cached_answer(result["answer"]):
        store_cache(session_id, original_question, result["answer"], result["source"], history)
    add_history(session_id, original_question, result["answer"])

    return result
