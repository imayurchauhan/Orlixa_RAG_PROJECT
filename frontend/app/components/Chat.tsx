"use client";

import { useState, useRef, useEffect } from "react";
import {
  sendMessageToChat,
  uploadFiles,
  getChatMessages,
  UploadResult,
  ChatMessage,
} from "@/lib/api";

interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  source?: string;
  files?: string[];
}

const SOURCE_BADGE: Record<string, { label: string; color: string }> = {
  document: { label: "Document", color: "bg-violet-500/20 text-violet-300" },
  web: { label: "Web", color: "bg-sky-500/20 text-sky-300" },
  llm: { label: "AI", color: "bg-amber-500/20 text-amber-300" },
};

const FILE_ICON = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
);

function dbMessageToUiMessage(m: ChatMessage): Message {
  return {
    role: m.role as "user" | "assistant",
    content: m.content,
    source: m.source ?? undefined,
  };
}

export default function Chat({
  chatId,
  sessionId,
  onFilesChanged,
}: {
  chatId: string | null;
  sessionId: string;
  onFilesChanged?: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load messages whenever chatId changes
  useEffect(() => {
    if (!chatId) {
      setMessages([]);
      return;
    }
    getChatMessages(chatId)
      .then((msgs) => setMessages(msgs.map(dbMessageToUiMessage)))
      .catch(() => setMessages([]));
  }, [chatId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    if (selected.length > 0) {
      setPendingFiles((prev) => [...prev, ...selected]);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const removePendingFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSend = async () => {
    if (!chatId) return;
    const q = input.trim();
    const filesToUpload = [...pendingFiles];

    if (!q && filesToUpload.length === 0) return;
    if (loading || uploading) return;

    setInput("");
    setPendingFiles([]);
    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }

    // Upload files first if any are attached
    if (filesToUpload.length > 0) {
      setUploading(true);
      const fileNames = filesToUpload.map((f) => f.name);
      const userMsg: Message = { role: "user", content: q || "Uploaded files for review", files: fileNames };
      setMessages((prev) => [...prev, userMsg]);

      try {
        const uploadRes = await uploadFiles(filesToUpload, chatId);
        const indexed = uploadRes.results.filter((r: UploadResult) => r.status === "indexed");
        const failed = uploadRes.results.filter((r: UploadResult) => r.status === "error");

        let systemContent = "";
        if (indexed.length > 0) {
          systemContent += `✓ ${indexed.map((r: UploadResult) => r.filename).join(", ")} indexed successfully.`;
        }
        if (failed.length > 0) {
          systemContent += ` ✗ ${failed.map((r: UploadResult) => `${r.filename}: ${r.error}`).join("; ")}`;
        }

        setMessages((prev) => [...prev, { role: "system", content: systemContent }]);
        onFilesChanged?.();

        // If there's also a text message, send it to chat
        if (q) {
          setUploading(false);
          setLoading(true);
          try {
            const res = await sendMessageToChat(chatId, q);
            setMessages((prev) => [...prev, { role: "assistant", content: res.answer, source: res.source }]);
          } catch {
            setMessages((prev) => [...prev, { role: "assistant", content: "Something went wrong. Please try again." }]);
          } finally {
            setLoading(false);
          }
        }
      } catch {
        setMessages((prev) => [...prev, { role: "system", content: "✗ Upload failed. Please try again." }]);
      } finally {
        setUploading(false);
        inputRef.current?.focus();
      }
      return;
    }

    // Regular text message (no files)
    const userMsg: Message = { role: "user", content: q };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const res = await sendMessageToChat(chatId, q);
      const assistantMsg: Message = { role: "assistant", content: res.answer, source: res.source };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Something went wrong. Please try again." }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scroll-smooth">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-white/30 select-none">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="mb-4 opacity-40">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <p className="text-sm font-medium">Ask anything or attach documents</p>
            <p className="text-xs mt-1 text-white/20">Supports PDF, DOCX, TXT, Images · Multiple files</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "system" ? (
              <div className="w-full flex justify-center">
                <span className="px-3 py-1.5 rounded-full text-xs font-medium bg-white/[0.04] text-white/50 border border-white/[0.06]">
                  {msg.content}
                </span>
              </div>
            ) : (
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed transition-all duration-300 animate-in ${
                  msg.role === "user"
                    ? "bg-gradient-to-br from-indigo-600 to-violet-600 text-white rounded-br-md"
                    : "bg-white/[0.06] text-white/90 border border-white/[0.06] rounded-bl-md backdrop-blur-sm"
                }`}
              >
                {msg.files && msg.files.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {msg.files.map((name, fi) => (
                      <span key={fi} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/10 text-[11px] font-medium text-white/80">
                        {FILE_ICON}
                        {name}
                      </span>
                    ))}
                  </div>
                )}
                <p className="whitespace-pre-wrap">{msg.content}</p>
                {msg.source && SOURCE_BADGE[msg.source] && (
                  <span className={`inline-block mt-2 px-2 py-0.5 rounded-full text-[10px] font-medium ${SOURCE_BADGE[msg.source].color}`}>
                    {SOURCE_BADGE[msg.source].label}
                  </span>
                )}
              </div>
            )}
          </div>
        ))}
        {(loading || uploading) && (
          <div className="flex justify-start">
            <div className="bg-white/[0.06] border border-white/[0.06] px-4 py-3 rounded-2xl rounded-bl-md backdrop-blur-sm">
              <div className="flex items-center gap-2 text-xs text-white/40">
                {uploading ? (
                  <>
                    <span className="inline-block w-3 h-3 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
                    Indexing files...
                  </>
                ) : (
                  <div className="flex gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-white/30 animate-bounce [animation-delay:0ms]" />
                    <span className="w-2 h-2 rounded-full bg-white/30 animate-bounce [animation-delay:150ms]" />
                    <span className="w-2 h-2 rounded-full bg-white/30 animate-bounce [animation-delay:300ms]" />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-white/[0.06] bg-black/20 backdrop-blur-xl px-4 py-3">
        <div className="max-w-3xl mx-auto">
          {/* Pending file chips */}
          {pendingFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {pendingFiles.map((file, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1.5 pl-2 pr-1 py-1 rounded-lg bg-white/[0.06] border border-white/[0.08] text-xs text-white/70"
                >
                  {FILE_ICON}
                  <span className="max-w-[120px] truncate">{file.name}</span>
                  <button
                    onClick={() => removePendingFile(i)}
                    className="ml-0.5 p-0.5 rounded hover:bg-white/10 text-white/30 hover:text-white/60 transition-colors"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </span>
              ))}
            </div>
          )}

          {/* Input row */}
          <div className="flex items-center gap-2">
            {/* Attach button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || uploading || !chatId}
              className="p-2.5 rounded-xl bg-white/[0.06] border border-white/[0.08] text-white/40 hover:text-white/70 hover:bg-white/[0.1] transition-all disabled:opacity-30"
              title="Attach files (PDF, DOCX, TXT, Images)"
              id="attach-button"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.webp,.gif"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />

            {/* Text input */}
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                // Auto-resize
                if (inputRef.current) {
                  inputRef.current.style.height = "auto";
                  inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 150) + "px";
                }
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder={chatId ? "Type a message... (Shift+Enter for new line)" : "Select or create a chat to start"}
              disabled={loading || uploading || !chatId}
              rows={1}
              className="flex-1 bg-white/[0.06] border border-white/[0.08] rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-white/25 outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all disabled:opacity-50 resize-none overflow-y-auto"
              style={{ maxHeight: "150px" }}
              id="chat-input"
            />

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={(loading || uploading || !chatId) || (!input.trim() && pendingFiles.length === 0)}
              className="p-2.5 rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white hover:opacity-90 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              id="send-button"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
