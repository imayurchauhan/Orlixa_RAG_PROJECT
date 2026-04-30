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

    # Core Real-Time Indicators
    "live",
    "now",
    "right now",
    "currently",
    "at the moment",
    "real time",
    "real-time",
    "instant",
    "ongoing",
    "happening now",

    # Time-Sensitive Queries
    "today",
    "yesterday",
    "tomorrow",
    "latest",
    "recent",
    "recently",
    "current",
    "new",
    "newest",
    "just now",
    "just happened",
    "last",
    "previous",
    "this week",
    "this month",
    "this year",
    "latest update",
    "latest news",
    "latest info",
    "latest information",

    # News Related
    "news",
    "breaking news",
    "headline",
    "headlines",
    "news update",
    "news today",
    "top news",
    "world news",
    "local news",
    "recent news",
    "news alert",
    "trending news",

    # Sports Related
    "score",
    "scores",
    "live score",
    "match",
    "match update",
    "match result",
    "results",
    "winner",
    "who won",
    "won",
    "final score",
    "scorecard",
    "live match",
    "live cricket",
    "live football",
    "live match score",
    "match status",
    "match summary",
    "live commentary",

    # IPL & Cricket Specific
    "ipl",
    "ipl score",
    "ipl match",
    "ipl result",
    "ipl live",
    "cricket score",
    "cricket live",
    "t20",
    "odi",
    "test match",

    # Weather Related
    "weather",
    "weather today",
    "weather now",
    "temperature",
    "forecast",
    "rain",
    "rainfall",
    "humidity",
    "wind speed",
    "storm",
    "heatwave",
    "weather forecast",

    # Financial / Stock Market
    "stock",
    "stocks",
    "stock price",
    "share price",
    "market",
    "market update",
    "market news",
    "stock market",
    "sensex",
    "nifty",
    "nifty50",
    "banknifty",
    "price",
    "prices",
    "rate",
    "rates",

    # Cryptocurrency
    "crypto",
    "cryptocurrency",
    "bitcoin",
    "btc",
    "ethereum",
    "eth",
    "crypto price",
    "coin price",
    "token price",
    "live crypto",
    "crypto market",

    # Commodity Prices
    "gold price",
    "silver price",
    "petrol price",
    "diesel price",
    "fuel price",
    "oil price",
    "commodity price",

    # Elections & Politics
    "election",
    "election results",
    "vote result",
    "poll result",
    "exit poll",
    "election update",
    "vote counting",

    # Technology / Releases
    "release date",
    "launch date",
    "launch today",
    "new release",
    "new update",
    "software update",
    "version update",

    # Trends / Social Media
    "trending",
    "trending now",
    "viral",
    "what's trending",
    "top trending",
    "trend",

    # Events & Alerts
    "alert",
    "emergency",
    "incident",
    "traffic update",
    "road condition",
    "flight status",
    "train status",
    "bus status",

    # Generic Update Terms
    "update",
    "updates",
    "status",
    "latest status",
    "current status",
    "live update",
    "recent update"
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
    "hii": "Hello! How can I help you today?",
    "hiii": "Hello! How can I help you today?",
    "hiiii": "Hello! How can I help you today?",
    "heyyy": "Hello! How can I help you today?",
    "hola": "Hola! How can I help you today?",
    "yo": "Hello! How can I help you today?",
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

    # Basic Identity Questions
    "who are you",
    "what are you",
    "what is your name",
    "what's your name",
    "who are u",
    "who r you",
    "who is this",
    "who's this",

    # Name Related
    "your name",
    "tell me your name",
    "what should i call you",
    "what are you called",
    "do you have a name",
    "name please",
    "your identity",

    # Introduction Requests
    "introduce yourself",
    "can you introduce yourself",
    "tell me about yourself",
    "about yourself",
    "self introduction",
    "give introduction",

    # Purpose / Role
    "what do you do",
    "what can you do",
    "what's your purpose",
    "your purpose",
    "what is your purpose",
    "why are you here",
    "what are you made for",
    "what is your job",

    # Capability Inquiry
    "how can you help me",
    "how do you help",
    "what help can you provide",
    "what services do you offer",

    # Conversational Variations
    "who am i talking to",
    "who am i chatting with",
    "who is talking",
    "who is answering",

    # Hindi Identity Queries
    "tum kaun ho",
    "aap kaun ho",
    "aap kaun hain",
    "tumhara naam kya hai",
    "aapka naam kya hai",
    "tera naam kya hai",

    # Hinglish Variants
    "tumhara name kya hai",
    "aapka name kya hai",
    "apka naam kya hai",
    "apka name kya hai",

    # Hindi Introduction Requests
    "apne bare me batao",
    "apne baare me batao",
    "apna parichay do",
    "khud ke baare me batao",

    # Hindi Purpose Queries
    "tum kya karte ho",
    "aap kya karte ho",
    "aap kya kar sakte ho",
    "tum kya kar sakte ho",
    "tumhara kaam kya hai",

    # Short / Casual Queries
    "who u",
    "name",
    "id",
    "identity",
    "about you",

    # AI-Specific Curiosity
    "are you ai",
    "are you human",
    "are you bot",
    "are you chatbot",
    "are you real",
    "are you robot",
    "what type of ai are you",

    # Model / System Curiosity
    "which model are you",
    "what model are you",
    "what ai model are you",
    "which ai are you",
    "what version are you",

    # Brand / Assistant Identity
    "who created you",
    "who made you",
    "who developed you",
    "who built you",

}

# Hindi/Hinglish Common Knowledge Base
# Keys are specific Hindi/Hinglish trigger phrases only.
# English queries (e.g. "PM of India") are handled by the LLM — no hardcoding.
_HINDI_KNOWLEDGE_BASE = {

    # President & Prime Minister (Dynamic Info)
    "rashtrapati": "Bharat ke vartaman Rashtrapati (President) Droupadi Murmu hain.",
    "rastrapati": "Bharat ke vartaman Rashtrapati (President) Droupadi Murmu hain.",

    "pradhan mantri": "Bharat ke vartaman Pradhan Mantri (Prime Minister) Narendra Modi hain.",
    "pm kaun hai": "Bharat ke vartaman Pradhan Mantri (Prime Minister) Narendra Modi hain.",

    # National Leaders
    "rashtrapita": "Bharat ke Rashtrapita (Father of the Nation) Mahatma Gandhi hain.",
    "bapu kaun": "Bapu Mahatma Gandhi ko kaha jata hai.",
    "gandhi ji kaun": "Mahatma Gandhi Bharat ke Rashtrapita (Father of the Nation) the.",

    # Capital
    "bharat ki rajdhani": "Bharat ki Rajdhani (Capital) New Delhi hai.",
    "bharat ka capital": "Bharat ki Rajdhani (Capital) New Delhi hai.",

    # National Symbols
    "rashtra gaan": "Bharat ka Rashtra Gaan (National Anthem) 'Jana Gana Mana' hai.",
    "national anthem india": "India ka National Anthem 'Jana Gana Mana' hai.",

    "rashtra geet": "Bharat ka Rashtra Geet (National Song) 'Vande Mataram' hai.",
    "national song india": "India ka National Song 'Vande Mataram' hai.",

    "rashtriya pakshi": "Bharat ka Rashtriya Pakshi (National Bird) Mor (Peacock) hai.",
    "national bird india": "India ka National Bird Mor (Peacock) hai.",

    "rashtriya janwar": "Bharat ka Rashtriya Janwar (National Animal) Bagh (Tiger) hai.",
    "national animal india": "India ka National Animal Bagh (Tiger) hai.",

    "rashtriya phool": "Bharat ka Rashtriya Phool (National Flower) Kamal (Lotus) hai.",
    "national flower india": "India ka National Flower Kamal (Lotus) hai.",

    "rashtriya fal": "Bharat ka Rashtriya Fal (National Fruit) Aam (Mango) hai.",
    "national fruit india": "India ka National Fruit Aam (Mango) hai.",

    "rashtriya vriksh": "Bharat ka Rashtriya Vriksh (National Tree) Bargad (Banyan Tree) hai.",
    "national tree india": "India ka National Tree Bargad hai.",

    # Languages
    "rashtra bhasha": "Bharat ki koi ek Rashtra Bhasha nahi hai, lekin Hindi aur English adhikarik bhashayein hain.",
    "national language india": "India ki koi official national language nahi hai.",

    # Currency
    "bharat ki mudra": "Bharat ki Mudra (Currency) Rupee (₹) hai.",
    "currency india": "India ki Currency Rupee (₹) hai.",

    # Independence & Republic Day
    "independence day": "Bharat ka Independence Day 15 August ko manaya jata hai.",
    "azadi kab mili": "Bharat ko 15 August 1947 ko azadi mili.",

    "republic day": "Bharat ka Republic Day 26 January ko manaya jata hai.",
    "ganatantra diwas": "Ganatantra Diwas 26 January ko manaya jata hai.",

    # States & Geography
    "bharat me kitne rajya": "Bharat me vartaman me 28 rajya (states) hain.",
    "how many states in india": "India me 28 states hain.",

    "sabse bada rajya": "Bharat ka sabse bada rajya Rajasthan hai (area ke hisab se).",
    "sabse chota rajya": "Bharat ka sabse chota rajya Goa hai (area ke hisab se).",

    # Population
    "bharat ki jansankhya": "Bharat duniya ka sabse adhik jansankhya wala desh hai.",

    # Rivers
    "sabse lambi nadi": "Bharat ki sabse lambi nadi Ganga hai.",
    "ganga kaha se nikalti hai": "Ganga nadi Gangotri glacier se nikalti hai.",

    # Science Basic
    "surya kya hai": "Surya ek tara (star) hai.",
    "chand kya hai": "Chand Prithvi ka ek upgrah (satellite) hai.",

    # Maths Basic
    "2+2": "2 + 2 = 4",
    "5+5": "5 + 5 = 10",

}

# Clarification detection keywords
_CLARIFICATION_KEYWORDS = {

    # Basic Negation / Correction
    "no",
    "not",
    "nope",
    "nah",
    "nahi",
    "nahin",
    "nai",
    "na",
    "bilkul nahi",
    "absolutely not",
    "not correct",
    "not right",
    "wrong",
    "incorrect",
    "galat",
    "galat tha",
    "galat hai",
    "ye galat hai",
    "that is wrong",

    # Confirmation / Agreement
    "yes",
    "haan",
    "han",
    "haa",
    "hmm",
    "bilkul",
    "bilkul sahi",
    "correct",
    "right",
    "exactly",
    "true",
    "sahi",
    "sahi hai",

    # Clarification Words
    "means",
    "meaning",
    "matlab",
    "iska matlab",
    "pata hai",
    "i mean",
    "what i mean",
    "let me clarify",
    "to clarify",
    "clarify",

    # Modification / Change Requests
    "change",
    "modify",
    "update",
    "edit",
    "revise",
    "replace",
    "correct this",
    "fix this",
    "update this",
    "modify this",

    # Alternative Requests
    "different",
    "alag",
    "doosra",
    "dusra",
    "another",
    "other",
    "else",
    "kuch aur",
    "aur",
    "and",
    "also",
    "instead",
    "rather",

    # Expansion / Addition
    "add",
    "include",
    "add this",
    "include this",
    "also add",
    "aur add karo",
    "ye bhi add karo",

    # Re-Explanation Requests
    "explain again",
    "repeat",
    "say again",
    "dobara",
    "phir se",
    "again",
    "once more",
    "re explain",
    "explain clearly",

    # Correction Feedback
    "you missed",
    "missing",
    "not included",
    "left out",
    "forgot",
    "missed this",

    # Refinement Requests
    "make it better",
    "improve",
    "refine",
    "enhance",
    "optimize",

    # Direction Changes
    "no i mean",
    "not that",
    "not this",
    "this one",
    "that one",
    "ye nahi",
    "wo nahi",
    "ye wala",
    "wo wala",

    # Tone Adjustments
    "short",
    "shorter",
    "long",
    "longer",
    "brief",
    "detailed",
    "simple",
    "simplify",
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
    
    # Ignore common casual conversational phrases that might contain "today" or "now"
    casual_phrases = ["how are you", "your day", "what are you doing", "who are you", "what is your name", "tell me about yourself", "tell me about your"]
    if any(phrase in lowered for phrase in casual_phrases):
        return False
        
    # Also detect common misspellings of 'yesterday'
    import re
    if re.search(r"yest[a-z]*day", lowered):
        return True
        
    # Exact word match for 'now' and 'today' to avoid partial matches
    words = lowered.split()
    if not words:
        return False
        
    # If the query is very short (1-2 words) and doesn't contain a heavy live term, ignore it.
    if len(words) <= 2 and not any(term in words for term in ["stock", "price", "score", "weather", "crypto", "bitcoin"]):
        # Special case: 'latest news' or 'today news' should still trigger
        if not ("news" in words or "latest" in words or "today" in words):
            return False

    if "today" in words or "now" in words or "current" in words or "latest" in words:
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
    
    # Check Hindi/Hinglish knowledge base (match on specific trigger phrase)
    for trigger, answer in _HINDI_KNOWLEDGE_BASE.items():
        if trigger in normalized:
            return {"answer": answer, "source": "knowledge"}
    
    # Check for clarification intent (e.g., "nahi, mujhe X janna hai" = "No, I want to know X")
    has_negation = any(kw in normalized for kw in ["nahi", "no", "not", "bilkul nahi", "galat"])
    
    if has_negation and history:
        # User is correcting/clarifying with a negation like "nahi" (no)
        # Look for any Hindi knowledge key in the current question
        for trigger, answer in _HINDI_KNOWLEDGE_BASE.items():
            if trigger in normalized:
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

def _extract_source_urls(context: str) -> list:
    """Extract source URLs from web search context for citation."""
    import re
    urls = re.findall(r'\[Source:\s*(https?://[^\]]+)\]', context)
    if not urls:
        # Fallback: extract URLs from snippet format "Title (URL): Body"
        urls = re.findall(r'\((https?://[^\)]+)\)', context)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique[:5]

def _boost_query_for_india(query: str) -> str:
    """Append 'India' to queries containing India-relevant keywords for better results."""
    india_keywords = [
        "ipl", "cricket", "gold price", "silver price",
        "weather", "news", "match", "score", "nifty",
        "sensex", "rupee", "petrol price", "diesel price",
    ]
    q = query.lower()
    if any(k in q for k in india_keywords):
        if "india" not in q:
            return query + " India"
    return query

def _try_web(question: str, history: str, images: list = None, original_question: str = "", session_id: str = None):
    """Step 3: Web search fallback."""
    # Use the refined question for search (cleaner), but fall back to original if empty
    search_q = question if question.strip() else (original_question or question)
    # Boost query for Indian relevance
    search_q = _boost_query_for_india(search_q)
    context = web_search_tool.invoke({"query": search_q})
    if not context:
        return None
    template = get_chat_template(session_id) if session_id else None
    answer = generate_answer(context, question, "web", history, images=images, template=template)
    if not answer or _is_uncertain(answer):
        return None

    # Append source citations to the answer
    source_urls = _extract_source_urls(context)
    if source_urls:
        citation_block = "\n\n**Sources:**"
        for i, url in enumerate(source_urls, 1):
            citation_block += f"\n{i}. {url}"
        answer += citation_block

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
        print(f"TRYING DOCUMENT RETRIEVAL for session: {session_id}")
        result = _try_document(session_id, question, history, images=images)
        if result: print(f"DOCUMENT MATCH FOUND")

    if not result and images:
        # Images present but no docs (or we skipped docs) — try vision LLM
        print(f"TRYING VISION LLM for session: {session_id}")
        result = _try_llm(question, history, images=images, session_id=session_id)
        if result: print(f"VISION ANSWER GENERATED")

    # Step 2: For live/time-sensitive queries, go straight to web search (skip LLM hallucination)
    if not result and is_live:
        print(f"LIVE QUERY DETECTED -> Prioritizing web search: {question}")
        result = _try_web(question, history, original_question=original_question, session_id=session_id)

    # Step 3: LLM direct answer for general knowledge
    if not result:
        print(f"TRYING LLM DIRECT ANSWER for query: {question}")
        result = _try_llm(question, history, session_id=session_id)

    # Step 4: Web fallback if LLM was uncertain
    if not result:
        print(f"LLM UNCERTAIN or NO ANSWER -> Falling back to web search")
        result = _try_web(question, history, original_question=original_question, session_id=session_id)

    # Final fallback
    if not result:
        print(f"ALL CHANNELS FAILED -> Returning final fallback answer")
        result = {"answer": _FINAL_FALLBACK_ANSWER, "source": "web"}

    print(f"SOURCE USED: {result['source']}")
    if use_answer_cache and not _is_non_reusable_cached_answer(result["answer"]):
        print(f"CACHING ANSWER for future use")
        store_cache(session_id, original_question, result["answer"], result["source"], history)
    add_history(session_id, original_question, result["answer"])

    return result
