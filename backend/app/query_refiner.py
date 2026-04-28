from groq import Groq
from app.cache import get_cached_refined_query, store_refined_query
from app.config import GROQ_API_KEY, LLM_MODEL

REFINE_PROMPT = """You are a prompt improvement assistant.

Rewrite the user's question to make it:

* Clear
* Specific
* Complete
* Suitable for document retrieval
* Suitable for web search
* Grammatically correct

Do NOT change meaning.

Do NOT add new facts.

Only improve clarity.

Return ONLY the improved question.

User Question:
{question}

Improved Question:"""

_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None


def _latest_history_message(history: str) -> str:
    if not history:
        return ""
    lines = [line.strip() for line in history.splitlines() if line.strip()]
    filtered = [line for line in lines if line != "Chat History:"]
    return filtered[-1] if filtered else ""


def _refinement_context(history: str) -> str:
    latest = _latest_history_message(history)
    if not latest:
        return ""
    return latest


def _build_refine_prompt(question: str, history: str = "") -> str:
    prompt = REFINE_PROMPT.format(question=question)
    history_context = _refinement_context(history)
    if not history_context:
        return prompt
    return (
        "Previous conversation context:\n"
        f"{history_context}\n\n"
        "Use the previous conversation context only to resolve vague references if needed.\n\n"
        f"{prompt}"
    )


def _normalize_refined_query(refined_query: str, original_question: str) -> str:
    cleaned = refined_query.strip()
    if cleaned.lower().startswith("improved question:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    cleaned = cleaned.strip("`").strip().strip('"').strip("'")
    cleaned = " ".join(cleaned.split())
    return cleaned or original_question


def _rewrite_query(question: str, history: str = "") -> str:
    if _client is None:
        return question

    response = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": _build_refine_prompt(question, history),
            }
        ],
        max_tokens=128,
        temperature=0.0,
    )
    content = response.choices[0].message.content or question
    return _normalize_refined_query(content, question)


def refine_query(question: str, history: str = "") -> str:
    original_question = question.strip()
    if not original_question:
        return original_question

    history_context = _refinement_context(history)
    cached_refined_query = get_cached_refined_query(original_question, history_context)
    if cached_refined_query:
        return cached_refined_query

    try:
        refined_question = _rewrite_query(original_question, history)
    except Exception as exc:
        print(f"QUERY REFINEMENT FAILED: {exc}")
        return original_question

    store_refined_query(original_question, refined_question, history_context)
    return refined_question
