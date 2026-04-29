from langchain_core.tools import tool
from app.rag import document_pipeline, has_documents
from app.config import UPLOAD_DIR
from app.web_search import web_search_tool
from app.llm import generate_answer
from app.query_refiner import refine_query
from app.template_manager import get_chat_template
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
    "hi": "Hello! How can I help you today?",
    "hello": "Hello! How can I help you today?",
    "hey": "Hello! How can I help you today?",
    "heyy": "Hello! How can I help you today?",
    "gm": "Good morning! How can I help you today?",
    "good morning": "Good morning! How can I help you today?",
    "good afternoon": "Good afternoon! How can I help you today?",
    "good evening": "Good evening! How can I help you today?",
    "hi orlixa": "Hello! How can I help you today?",
    "hello orlixa": "Hello! How can I help you today?",
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

# Identity query responses for Orlixa AI
_IDENTITY_RESPONSES = {
    "I am Orlixa, an AI assistant designed to help you with information retrieval and answering questions. "
    "I can help you search through documents, access web information, and have meaningful conversations. "
    "What can I assist you with today?"
}

_IDENTITY_PHRASES = {
    "who are you",
    "what are you",
    "what is your name",
    "what are you called",
    "who am i talking to",
    "what should i call you",
    "your name",
    "your identity",
    "what's your name",
    "who's this",
    "introduce yourself",
    "tell me about yourself",
    "what do you do",
    "what's your purpose",
    "what can you do",
}

# Hindi/Hinglish Common Knowledge Base
_HINDI_KNOWLEDGE_BASE = {
    # Indian President & Father of Nation
    ("rastrapati", "droupadi murmu"): "Bharat ke vartaman Rashtrapati (President) Droupadi Murmu hain.",
    ("rashtrapita", "gandhi"): "Bharat ke Rashtrapita (Father of the Nation) Mahatma Gandhi hain. Unhe Bapu bhi kehte hain.",
    ("bapu", "gandhi"): "Bapu (Father) Mahatma Gandhi the Rashtrapita (Father of the Nation) of India.",
    
    # Indian Prime Minister
    ("pradhan mantri", "narendra modi"): "Bharat ke vartaman Pradhan Mantri (Prime Minister) Narendra Modi hain.",
    ("pm", "narendra modi"): "Bharat ke Prime Minister Narendra Modi hain.",
    
    # Other common Indian facts
    ("bharat ki rajdhani", "delhi"): "Bharat ki Rajdhani (Capital) New Delhi hai.",
    ("capital", "india"): "The capital of India is New Delhi.",
    ("rashtra gaan", "jana gana mana"): "Bharat ka Rashtra Gaan (National Anthem) 'Jana Gana Mana' hai.",
    ("national anthem", "india"): "The National Anthem of India is 'Jana Gana Mana' composed by Rabindranath Tagore.",
    ("rashtra bhasha", "hindi"): "Bharat ki Rashtra Bhasha (National Language) Hindi hai.",
    ("national language", "india"): "The national language of India is Hindi.",
}

# Clarification detection keywords
_CLARIFICATION_KEYWORDS = {
    "nahi", "no", "not", "bilkul nahi", "absolutely not",
    "galat", "wrong", "incorrect", "galat tha",
    "nai", "nahin", "nahi",
    "pata hai", "means", "matlab",
    "alag", "different", "doosra",
    "aur", "and", "also",
    "haan", "yes", "bilkul",
}


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

def _get_conversational_reply(question: str, history: str = ""):
    normalized = " ".join(question.strip().lower().split())
    if not normalized:
        return None
    if normalized in _EXIT_PHRASES:
        return {"answer": "Goodbye! I'll be here whenever you're ready to continue our chat.", "source": "system"}
    if normalized in _LEAVE_IT_PHRASES:
        return {"answer": "Okay, we can leave it here. Let me know if you want to ask something else.", "source": "system"}
    if normalized in _ACKNOWLEDGEMENT_REPLIES:
        return {"answer": _ACKNOWLEDGEMENT_REPLIES[normalized], "source": "system"}
    
    # Check for identity queries
    for phrase in _IDENTITY_PHRASES:
        if phrase in normalized:
            return {"answer": list(_IDENTITY_RESPONSES)[0], "source": "system"}
    
    # Check Hindi/Hinglish knowledge base
    for (key1, key2), answer in _HINDI_KNOWLEDGE_BASE.items():
        if key1 in normalized or key2 in normalized:
            return {"answer": answer, "source": "knowledge"}
    
    # Check for clarification intent (e.g., "nahi, mujhe X janna hai" = "No, I want to know X")
    has_negation = any(kw in normalized for kw in ["nahi", "no", "not", "bilkul nahi", "galat"])
    
    if has_negation and history:
        # User is correcting/clarifying with a negation like "nahi" (no)
        # Look for any Hindi knowledge key in the current question
        for (key1, key2), answer in _HINDI_KNOWLEDGE_BASE.items():
            if key1 in normalized:
                return {"answer": answer, "source": "knowledge"}
    
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
    template = get_chat_template(session_id)
    answer = generate_answer(context, question, "document", history, images=images, template=template)
    if _is_uncertain(answer):
        return None
    return {"answer": answer, "source": "document"}

def _try_llm(question: str, history: str, images: list = None, session_id: str = None):
    """Step 2: Try direct LLM answer."""
    template = get_chat_template(session_id) if session_id else None
    answer = generate_answer("", question, "general", history, images=images, template=template)
    if _is_uncertain(answer):
        print(f"LLM UNCERTAIN -> triggering web fallback for: {question}")
        return None
    return {"answer": answer, "source": "llm"}

def _try_web(question: str, history: str, images: list = None, original_question: str = "", session_id: str = None):
    """Step 3: Web search fallback."""
    # Use the refined question for search (cleaner), but fall back to original if empty
    search_q = question if question.strip() else (original_question or question)
    context = web_search_tool.invoke({"query": search_q})
    if not context:
        return None
    template = get_chat_template(session_id) if session_id else None
    answer = generate_answer(context, question, "web", history, images=images, template=template)
    if not answer or _is_uncertain(answer):
        return None
    return {"answer": answer, "source": "web"}

def route_query(session_id: str, question: str) -> dict:
    print(f"SESSION: {session_id}")
    history = get_history_str(session_id)
    original_question = question.strip()
    conversational_reply = _get_conversational_reply(original_question, history)
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
        result = _try_llm(question, history, images=images, session_id=session_id)

    # Step 2: For live/time-sensitive queries, go straight to web search (skip LLM hallucination)
    if not result and is_live:
        print(f"LIVE QUERY DETECTED -> Prioritizing web search: {question}")
        result = _try_web(question, history, original_question=original_question, session_id=session_id)

    # Step 3: LLM direct answer for general knowledge
    if not result:
        result = _try_llm(question, history, session_id=session_id)

    # Step 4: Web fallback if LLM was uncertain
    if not result:
        result = _try_web(question, history, original_question=original_question, session_id=session_id)

    # Final fallback
    if not result:
        result = {"answer": _FINAL_FALLBACK_ANSWER, "source": "web"}

    print(f"SOURCE USED: {result['source']}")
    if use_answer_cache and not _is_non_reusable_cached_answer(result["answer"]):
        store_cache(session_id, original_question, result["answer"], result["source"], history)
    add_history(session_id, original_question, result["answer"])

    return result
