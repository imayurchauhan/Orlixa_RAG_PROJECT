const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Types ────────────────────────────────────────────────────────────────────

export interface Chat {
  id: string;
  title: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  source?: string;
  created_at: string;
}

export interface UploadResult {
  filename: string;
  status: string;
  error?: string;
}

// ── Chat history API ─────────────────────────────────────────────────────────

export async function createChat(title = "New Chat"): Promise<Chat> {
  const res = await fetch(`${API_BASE}/chats`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to create chat");
  return res.json();
}

export async function listChats(): Promise<Chat[]> {
  const res = await fetch(`${API_BASE}/chats`);
  if (!res.ok) throw new Error("Failed to list chats");
  const data = await res.json();
  return data.chats;
}

export async function getChatMessages(chatId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_BASE}/chats/${encodeURIComponent(chatId)}`);
  if (!res.ok) throw new Error("Failed to load messages");
  const data = await res.json();
  return data.messages;
}

export async function deleteChat(chatId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete chat");
}

export async function renameChat(chatId: string, title: string): Promise<void> {
  const res = await fetch(`${API_BASE}/chats/${encodeURIComponent(chatId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to rename chat");
}

// ── RAG chat (scoped to a chat_id) ──────────────────────────────────────────

export async function sendMessageToChat(
  chatId: string,
  message: string
): Promise<{ answer: string; source: string }> {
  const res = await fetch(`${API_BASE}/chat/${encodeURIComponent(chatId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

// ── Legacy / file endpoints (kept) ──────────────────────────────────────────

export async function sendMessage(
  message: string,
  sessionId: string
): Promise<{ answer: string; source: string }> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json();
}

export async function uploadFiles(
  files: File[],
  sessionId: string
): Promise<{ results: UploadResult[] }> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("session_id", sessionId);
  const res = await fetch(`${API_BASE}/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

export async function getFiles(sessionId: string): Promise<{ files: string[] }> {
  const res = await fetch(`${API_BASE}/files?session_id=${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error("Failed to list files");
  return res.json();
}

export async function clearSession(sessionId: string): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/clear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  if (!res.ok) throw new Error("Clear failed");
  return res.json();
}
