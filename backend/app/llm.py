import datetime
from groq import Groq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from app.config import GROQ_API_KEY, LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

DOCUMENT_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are an expert document assistant.\n"
     "If the user asks 'what is this attachment', 'what is in this file', or similar, "
     "refer to the provided Context below as the attachment/file.\n\n"
     "Structure answer:\n"
     "1. Direct Answer\n"
     "2. Explanation\n"
     "3. Supporting Details\n"
     "4. Summary\n\n"
     "If answer not found:\n"
     "Return exactly:\n"
     "NOT_FOUND\n"),
    ("user", "--- DOCUMENT CONTEXT ---\n{context}\n\n--- CHAT HISTORY ---\n{history}\n\nQuestion: {question}\n\nAnswer:")
])

WEB_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Today's date is {current_date}.\n"
     "Answer the user's question USING ONLY the web search results provided below.\n"
     "Give a direct, clear, and informative answer.\n"
     "CRITICAL INSTRUCTIONS:\n"
     "- If the user asks for a match result/winner and the teams are in the context, EXTRACT the winner directly.\n"
     "- NEVER suggest that the user do their own search online.\n"
     "- NEVER say you cannot verify or that results are unclear if the text mentions the outcome.\n"
     "- Provide the final answer definitively based on the text snippets provided."),
    ("user", "{history}Web search results:\n{context}\n\nQuestion: {question}")
])

GENERAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You are a friendly, conversational AI assistant. Today's date is {current_date}.\n"
     "For normal conversation (greetings, thanks, casual chat, follow-ups), respond naturally and warmly.\n"
     "For general knowledge questions, answer confidently and clearly.\n"
     "CRITICAL: If the question requires LIVE real-time data, current events, today's specific information, "
     "or any data that changes daily (e.g., live sports scores, weather, stock prices, match results from today), "
     "you MUST respond with EXACTLY and ONLY the word: NOT_FOUND\n"
     "Do NOT suggest websites, do NOT give historical data as a substitute, and do NOT explain why you cannot answer.\n"
     "Just say: NOT_FOUND"),
    ("user", "{history}Question: {question}")
])

def _call_groq(prompt_value):
    messages = [{"role": msg.type, "content": msg.content} for msg in prompt_value.to_messages()]
    for m in messages:
        if m["role"] == "human": m["role"] = "user"
        if m["role"] == "ai": m["role"] = "assistant"

    resp = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,  # type: ignore
        max_tokens=512,
        temperature=0.3,
        stream=True
    )
    for chunk in resp:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

_llm_runnable = RunnableLambda(_call_groq)

def generate_answer(context: str, question: str, mode: str, history: str = "", images=None) -> str:
    current_date = datetime.date.today().strftime("%B %d, %Y")
    
    if images:
        import base64
        # If images are present, we skip standard chains and make a multimodal call directly.
        # We can use llama-3.2-11b-vision-preview
        content = [{"type": "text", "text": f"{history}Question: {question}"}]  # type: ignore
        if context:
            content[0]["text"] = f"{history}Context:\n{context}\n\nQuestion: {question}"
            
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
        
        if mode == "document":
            sys_msg = (
                "You are an expert document and multimodal assistant.\n"
                "You have access to both text Context (extracted from uploaded documents like PDFs) and uploaded images.\n"
                "CRITICAL INSTRUCTION: If the user asks about 'this attachment' or 'this file', review the Chat History carefully to see the most recently uploaded file.\n"
                "- If the recent upload or question is about an image/photo (e.g., .jpg, .png), answer based ONLY on the images.\n"
                "- If the recent upload or question is about a document/PDF, you MUST answer based on the text Context provided.\n"
                "If answering based on the text Context, provide a clear, structured summary."
            )
        else:
            sys_msg = "You are a helpful AI assistant. Answer the user's question, using the provided images and context if available."

        messages = [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": content}
        ]
        
        resp = _client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct", # type: ignore
            messages=messages, # type: ignore
            max_tokens=1024,
            temperature=0.3,
            stream=True
        )
        gen = (chunk.choices[0].delta.content for chunk in resp if chunk.choices[0].delta.content is not None)
        return "".join(gen).strip()

    if mode == "document":
        chain = DOCUMENT_PROMPT | _llm_runnable
        gen = chain.invoke({"context": context, "history": history, "question": question})
    elif mode == "web":
        chain = WEB_PROMPT | _llm_runnable
        gen = chain.invoke({"context": context, "history": history, "question": question, "current_date": current_date})
    else:
        chain = GENERAL_PROMPT | _llm_runnable
        gen = chain.invoke({"history": history, "question": question, "current_date": current_date})
    
    # Returning a joined string for now. Ready to be yielded directly for SSE.
    return "".join(gen).strip()
