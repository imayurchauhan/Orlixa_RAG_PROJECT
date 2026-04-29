const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const AUTH_TOKEN_KEY = "orlixa_auth_token";

export interface Chat {
  id: string;
  title: string;
  created_at: string;
  user_id?: string;
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

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string;
  auth_provider: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function getStoredAuthToken(): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
}

export function hasStoredSession(): boolean {
  return Boolean(getStoredAuthToken());
}

function setStoredAuthToken(token: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearStoredSession() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(AUTH_TOKEN_KEY);
}

async function buildError(res: Response): Promise<ApiError> {
  let message = `Request failed with status ${res.status}`;
  try {
    const data = await res.json();
    if (typeof data?.detail === "string") {
      message = data.detail;
    }
  } catch {}
  return new ApiError(message, res.status);
}

async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {});
  const token = getStoredAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    throw await buildError(res);
  }

  return res;
}

function storeAuth(response: AuthResponse): AuthResponse {
  setStoredAuthToken(response.access_token);
  return response;
}

export async function registerWithEmail(
  email: string,
  password: string,
  fullName = ""
): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
    }),
  });
  if (!res.ok) throw await buildError(res);
  return storeAuth(await res.json());
}

export async function loginWithEmail(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw await buildError(res);
  return storeAuth(await res.json());
}

export async function loginWithGoogle(credential: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ credential }),
  });
  if (!res.ok) throw await buildError(res);
  return storeAuth(await res.json());
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const res = await apiFetch("/auth/me");
  const data = await res.json();
  return data.user;
}

export async function createChat(title = "New Chat"): Promise<Chat> {
  const res = await apiFetch("/chats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  return res.json();
}

export async function listChats(): Promise<Chat[]> {
  const res = await apiFetch("/chats");
  const data = await res.json();
  return data.chats;
}

export async function getChatMessages(chatId: string): Promise<ChatMessage[]> {
  const res = await apiFetch(`/chats/${encodeURIComponent(chatId)}`);
  const data = await res.json();
  return data.messages;
}

export async function deleteChat(chatId: string): Promise<void> {
  await apiFetch(`/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE",
  });
}

export async function renameChat(chatId: string, title: string): Promise<void> {
  await apiFetch(`/chats/${encodeURIComponent(chatId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function sendMessageToChat(
  chatId: string,
  message: string
): Promise<{ answer: string; source: string }> {
  const res = await apiFetch(`/chat/${encodeURIComponent(chatId)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  return res.json();
}

export async function sendMessage(
  message: string,
  sessionId: string
): Promise<{ answer: string; source: string }> {
  const res = await apiFetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId }),
  });
  return res.json();
}

export async function uploadFiles(
  files: File[],
  sessionId: string
): Promise<{ results: UploadResult[] }> {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  formData.append("session_id", sessionId);
  const res = await apiFetch("/upload", {
    method: "POST",
    body: formData,
  });
  return res.json();
}

export async function getFiles(sessionId: string): Promise<{ files: string[] }> {
  const res = await apiFetch(`/files?session_id=${encodeURIComponent(sessionId)}`);
  return res.json();
}

export async function clearSession(sessionId: string): Promise<{ status: string }> {
  const res = await apiFetch("/clear", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });
  return res.json();
}
