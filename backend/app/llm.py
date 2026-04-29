import datetime
from groq import Groq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from app.config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

DOCUMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are Orlixa, a strictly professional and highly intelligent AI assistant.\n"
     "Provide direct, factual, and well-structured responses.\n"
     "Avoid informal greetings. Get straight to the point.\n"
     "If corrected by the user, acknowledge it briefly and proceed with the correct info.\n"
     "DO NOT use redundant section headers like '🎯 Direct Answer' or 'The Person in the Picture'.\n"
     "Use the chat history to understand follow-up references like 'this', 'it', "
     "'that description', or 'explain in more detail'.\n\n"
     "{question_guidance}\n\n"
     "If the answer is not found in the context, return exactly: NOT_FOUND\n"),
    ("user", "--- DOCUMENT CONTEXT ---\n{context}\n\n--- CHAT HISTORY ---\n{history}\n\nQuestion: {question}\n\nAnswer:")
])

WEB_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a professional research intelligence system. Today's date is {current_date}.\n"
     "Answer the user's question USING ONLY the web search results provided below.\n"
     "Provide a structured, clean, and corporate-professional answer.\n"
     "Avoid wordy introductions or personality-driven headers.\n"
     "DO NOT use redundant headers like 'Information About X' or 'The Person in the Picture'.\n"
     "If the user corrects you, acknowledge briefly and provide the corrected facts directly.\n"
     "Use **bold text** for key facts and bullet points for lists if multiple points exist.\n\n"
     "CRITICAL INSTRUCTIONS:\n"
     "- If the user asks for a match result/winner and the teams are in the context, EXTRACT the winner directly.\n"
     "- NEVER suggest that the user do their own search online.\n"
     "- NEVER say you cannot verify or that results are unclear if the text mentions the outcome.\n"
     "- Provide the final answer definitively based on the text snippets provided."),
    ("user", "{history}Web search results:\n{context}\n\nQuestion: {question}")
])

GENERAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are Orlixa, a professional and concise AI assistant. Today's date is {current_date}.\n"
     "Respond with direct, factual information. Be as concise as possible.\n"
     "NEVER use informal greetings or personality-based intros.\n"
     "DO NOT use redundant headers like 'Summary' or 'The Individual in the Picture'.\n"
     "If corrected, acknowledge briefly and move on with the correct answer.\n"
     "Use the chat history carefully but prioritize a professional, neutral tone.\n"
     "{question_guidance}\n"
     "CRITICAL: If the question requires LIVE real-time data or any daily changing information, you MUST respond with EXACTLY and ONLY the word: NOT_FOUND"),
    ("user", "{history}Question: {question}")
])

_DETAIL_REQUEST_TERMS = (
    "detail",
    "detailed",
    "very detail",
    "very detailed",
    "point wise",
    "point-wise",
    "bullet",
    "long description",
    "describe more",
    "explain more",
    "elaborate",
    "in depth",
)

_DESCRIPTION_CHECK_TERMS = (
    "same picture",
    "same image",
    "match the image",
    "matches the image",
    "match this image",
    "description is correct",
    "description correct",
    "is this description",
    "check this description",
    "whether this description",
    "compare this description",
    "compare the description",
)

_TEXT_COMPARISON_TERMS = (
    "compare",
    "comparison",
    "difference",
    "differences",
    "diff",
    "same or different",
    "same paragraph",
    "same paragraphs",
    "two paragraphs",
    "these paragraphs",
    "paragraphs",
    "two descriptions",
    "these descriptions",
)

_YES_NO_TERMS = (
    "yes or no",
    "yes/no",
)


def _wants_detailed_answer(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in _DETAIL_REQUEST_TERMS)


def _is_description_check(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in _DESCRIPTION_CHECK_TERMS)


def _is_text_comparison(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in _TEXT_COMPARISON_TERMS)


def _wants_yes_no_answer(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in _YES_NO_TERMS)


def _build_question_guidance(question: str) -> str:
    guidance = []

    if _is_text_comparison(question):
        guidance.append(
            "If the user asks to compare paragraphs, descriptions, or answers, compare the text content directly. Focus on similarities, differences, missing details, and contradictions. Do not drift into a fresh scene description unless the user explicitly asks for one."
        )

    if _wants_yes_no_answer(question):
        guidance.append(
            "If the user explicitly asks for yes or no, start the answer with exactly 'Yes.' or 'No.' and then give a short reason."
        )

    if _is_description_check(question):
        guidance.append(
            "If checking whether a description matches an image, give the verdict first and then support it with point-by-point evidence."
        )

    return "\n".join(guidance).strip()


def _build_multimodal_user_text(question: str, history: str = "", context: str = "") -> str:
    sections = []
    if history.strip():
        sections.append(f"--- CHAT HISTORY ---\n{history.strip()}")
    if context.strip():
        sections.append(f"--- TEXT CONTEXT ---\n{context.strip()}")
    sections.append(f"--- USER QUESTION ---\n{question.strip()}")
    return "\n\n".join(sections)


def _build_multimodal_system_message(mode: str, question: str, template: dict = None) -> str:
    parts = []

    if template:
        tone = template.get("tone")
        instr = template.get("instructions")
        parts.append(f"Persona/Tone: {tone}\nCustom System Instructions: {instr}\n")

    if mode == "document":
        parts.extend([
            "You are an expert document and multimodal assistant.",
            "You have access to both text context extracted from uploaded documents and uploaded image(s).",
            "Use the chat history carefully to understand follow-up references like 'this', 'it', 'that description', 'same picture', or 'more detail'.",
            "If the recent upload or question is about an image/photo, answer primarily from the image(s).",
            "If the recent upload or question is about a document/PDF, answer from the provided text context.",
        ])
    else:
        parts.extend([
            "You are a careful multimodal assistant.",
            "Inspect the uploaded image(s) closely before answering.",
            "Use the chat history carefully to understand follow-up references like 'this', 'it', 'that description', 'same picture', or 'more detail'.",
            "Base the answer on the uploaded image(s) and any provided context.",
        ])

    parts.append("Do not invent details that are not visible or supported. If something is unclear or not visible, say so.")
    parts.append("If the user corrects you, acknowledge it briefly and update your findings immediately.")
    parts.append("DO NOT use redundant headers like 'The Individual in the Picture' or 'Key Facts'.")
    parts.append("Use professional Markdown formatting. Use bold text and bullet points to structure your response clearly.")

    if _is_text_comparison(question):
        parts.append(
            "If the user asks to compare paragraphs, descriptions, or answers, prioritize comparing the text provided in the current message or chat history. Do not switch into a fresh image description unless the user explicitly asks for that."
        )

    if _wants_yes_no_answer(question):
        parts.append(
            "If the user explicitly asks for yes or no, start with exactly 'Yes.' or 'No.' and then give a short reason."
        )

    if _is_description_check(question):
        parts.append(
            "If the user provides a description and asks whether it matches the image, start with a clear verdict such as Yes, Mostly yes, Partly, or No. Then compare point by point and explain which details match, which are missing, and which are incorrect."
        )

    if _wants_detailed_answer(question):
        parts.append(
            "The user wants a long, detailed answer. Provide a rich, structured description using Markdown headers and bullet points. Cover the overall scene, each visible person/object, positions, actions, and notable details."
        )
    else:
        parts.append("Answer directly, clearly, and in a professional format.")

    return "\n".join(parts)

def _call_groq(prompt_value):
    messages = [{"role": msg.type, "content": msg.content} for msg in prompt_value.to_messages()]
    for m in messages:
        if m["role"] == "human": m["role"] = "user"
        if m["role"] == "ai": m["role"] = "assistant"

    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,  # type: ignore
        max_tokens=1024,
        temperature=0.3,
        stream=True
    )
    for chunk in resp:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

_llm_runnable = RunnableLambda(_call_groq)

def generate_answer(context: str, question: str, mode: str, history: str = "", images=None, template: dict = None) -> str:
    current_date = datetime.date.today().strftime("%B %d, %Y")
    
    persona_instr = ""
    if template:
        tone = template.get("tone")
        instr = template.get("instructions")
        persona_instr = f"### 🎭 Persona & Tone\n- **Tone**: {tone}\n- **Custom Rules**: {instr}\n\n"

    if images:
        import base64
        content = [{"type": "text", "text": _build_multimodal_user_text(question, history, context)}]  # type: ignore
            
        for img_path in images:
            with open(img_path, "rb") as idx_f:
                b64_img = base64.b64encode(idx_f.read()).decode("utf-8")
                # determine mime type
                ext = str(img_path).split('.')[-1].lower()
                mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
                content.append({  # type: ignore
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_img}"}
                })

        messages = [
            {"role": "system", "content": _build_multimodal_system_message(mode, question, template)},
            {"role": "user", "content": content}
        ]
        
        resp = _client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", # type: ignore
            messages=messages, # type: ignore
            max_tokens=2048,
            temperature=0.3,
            stream=True
        )
        gen = (chunk.choices[0].delta.content for chunk in resp if chunk.choices[0].delta.content is not None)
        return "".join(gen).strip()

    if mode == "document":
        prompt = DOCUMENT_PROMPT
        if persona_instr:
            prompt = ChatPromptTemplate.from_messages([
                ("system", persona_instr + DOCUMENT_PROMPT.messages[0].prompt.template),
                DOCUMENT_PROMPT.messages[1]
            ])
        chain = prompt | _llm_runnable
        gen = chain.invoke({
            "context": context,
            "history": history,
            "question": question,
            "question_guidance": _build_question_guidance(question),
        })
    elif mode == "web":
        prompt = WEB_PROMPT
        if persona_instr:
            prompt = ChatPromptTemplate.from_messages([
                ("system", persona_instr + WEB_PROMPT.messages[0].prompt.template),
                WEB_PROMPT.messages[1]
            ])
        chain = prompt | _llm_runnable
        gen = chain.invoke({"context": context, "history": history, "question": question, "current_date": current_date})
    else:
        prompt = GENERAL_PROMPT
        if persona_instr:
            prompt = ChatPromptTemplate.from_messages([
                ("system", persona_instr + GENERAL_PROMPT.messages[0].prompt.template),
                GENERAL_PROMPT.messages[1]
            ])
        chain = prompt | _llm_runnable
        gen = chain.invoke({
            "history": history,
            "question": question,
            "current_date": current_date,
            "question_guidance": _build_question_guidance(question),
        })
    
    # Returning a joined string for now. Ready to be yielded directly for SSE.
    return "".join(gen).strip()
