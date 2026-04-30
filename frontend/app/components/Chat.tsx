"use client";

import { useState, useRef, useEffect } from "react";
import {
  sendMessageToChat,
  uploadFiles,
  getChatMessages,
  clearChatMessages,
  UploadResult,
  ChatMessage,
} from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

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
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

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
          abortControllerRef.current = new AbortController();
          try {
            const res = await sendMessageToChat(chatId, q, abortControllerRef.current.signal);
            setMessages((prev) => [...prev, { role: "assistant", content: res.answer, source: res.source }]);
          } catch (error: any) {
            if (error.name === "AbortError") {
              setMessages((prev) => [...prev, { role: "assistant", content: "Chat paused by user." }]);
            } else {
              setMessages((prev) => [...prev, { role: "assistant", content: "Something went wrong. Please try again." }]);
            }
          } finally {
            setLoading(false);
            abortControllerRef.current = null;
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
    abortControllerRef.current = new AbortController();
    try {
      const res = await sendMessageToChat(chatId, q, abortControllerRef.current.signal);
      const assistantMsg: Message = { role: "assistant", content: res.answer, source: res.source };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      if (error.name === "AbortError") {
        setMessages((prev) => [...prev, { role: "assistant", content: "Chat paused by user." }]);
      } else {
        setMessages((prev) => [...prev, { role: "assistant", content: "Something went wrong. Please try again." }]);
      }
    } finally {
      setLoading(false);
      abortControllerRef.current = null;
      inputRef.current?.focus();
    }
  };

  const handleClear = async () => {
    if (!chatId || messages.length === 0) return;
    if (!confirm("Are you sure you want to clear all messages from this chat? This action cannot be undone.")) return;

    try {
      await clearChatMessages(chatId);
      setMessages([]);
      inputRef.current?.focus();
    } catch {
      alert("Failed to clear chat. Please try again.");
    }
  };

  return (
    <div className="flex flex-col h-full relative w-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto scroll-smooth pb-28">
        <div className="max-w-3xl mx-auto px-3 sm:px-4 py-4 sm:py-6 space-y-3 sm:space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-white/30 select-none animate-fade-in px-4">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="mb-3 sm:mb-4 opacity-40 animate-pulse">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <p className="text-xs sm:text-sm font-medium">Ask anything or attach documents</p>
            <p className="text-[10px] sm:text-xs mt-1 text-white/20 text-center">Supports PDF, DOCX, TXT, Images · Multiple files</p>
          </div>
        )}
        {messages.map((msg, i) => {
          return (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} animate-slide-in-bottom`} style={{ animationDelay: `${Math.min(i * 15, 250)}ms` }}>
            {msg.role === "system" ? (
              <div className="w-full flex justify-center px-2">
                <span className="px-2.5 sm:px-3 py-1 sm:py-1.5 rounded-full text-[10px] sm:text-xs font-medium bg-white/[0.04] text-white/50 border border-white/[0.06] animate-scale-in">
                  {msg.content}
                </span>
              </div>
            ) : (
              <div
                className={`max-w-[85%] sm:max-w-[80%] px-3 sm:px-4 py-2 sm:py-3 rounded-lg sm:rounded-2xl text-xs sm:text-sm leading-relaxed transition-all duration-300 animate-in ${
                  msg.role === "user"
                    ? "bg-gradient-to-br from-indigo-600 to-violet-600 text-white-force rounded-br-md hover:shadow-lg hover:shadow-indigo-500/20 transform hover:scale-[1.02]"
                    : "bg-white/[0.06] text-white/90 border border-white/[0.06] rounded-bl-md backdrop-blur-sm hover:bg-white/[0.08]"
                }`}
              >
                {msg.files && msg.files.length > 0 && (
                  <div className="flex flex-wrap gap-1 mb-1.5 sm:mb-2">
                    {msg.files.map((name, fi) => (
                      <span key={fi} className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-0.5 rounded-md bg-white/10 text-[9px] sm:text-[11px] font-medium text-white/80 animate-scale-in">
                        {FILE_ICON}
                        <span className="max-w-[100px] sm:max-w-none truncate">{name}</span>
                      </span>
                    ))}
                  </div>
                )}
                <div className={`markdown-content ${msg.role === "user" ? "user-message-markdown" : ""}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
                {msg.source && SOURCE_BADGE[msg.source] && (
                  <span className={`inline-block mt-1.5 sm:mt-2 px-2 py-0.5 rounded-full text-[9px] sm:text-[10px] font-medium ${SOURCE_BADGE[msg.source].color} animate-fade-in`}>
                    {SOURCE_BADGE[msg.source].label}
                  </span>
                )}
              </div>
            )}
          </div>
          );
        })}
        {(loading || uploading) && (
          <div className="flex justify-start animate-slide-in-bottom">
            <div className="bg-white/[0.06] border border-white/[0.06] px-3 sm:px-4 py-2 sm:py-3 rounded-lg sm:rounded-2xl rounded-bl-md backdrop-blur-sm">
              <div className="flex items-center gap-2 text-[10px] sm:text-xs text-white/40">
                {uploading ? (
                  <>
                    <span className="inline-block w-2.5 sm:w-3 h-2.5 sm:h-3 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
                    <span className="hidden sm:inline">Indexing files...</span>
                    <span className="sm:hidden">Indexing...</span>
                  </>
                ) : (
                  <div className="flex gap-1">
                    <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-white/30 animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-white/30 animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 sm:w-2 h-1.5 sm:h-2 rounded-full bg-white/30 animate-bounce [animation-delay:300ms]" />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
        </div>
      </div>

      {/* Input area */}
      <div className="sticky bottom-0 border-t border-white/[0.06] bg-black/20 backdrop-blur-xl px-2 sm:px-4 py-2 sm:py-3 animate-slide-in-bottom">
        <div className="max-w-3xl mx-auto">
          {/* Pending file chips */}
          {pendingFiles.length > 0 && (
            <div className="flex flex-wrap gap-1 sm:gap-1.5 mb-2">
              {pendingFiles.map((file, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 pl-1.5 sm:pl-2 pr-0.5 sm:pr-1 py-0.5 sm:py-1 rounded-md sm:rounded-lg bg-white/[0.06] border border-white/[0.08] text-[9px] sm:text-xs text-white/70 animate-scale-in hover:bg-white/[0.1] transition-colors"
                  style={{ animationDelay: `${i * 50}ms` }}
                >
                  {FILE_ICON}
                  <span className="max-w-[80px] sm:max-w-[120px] truncate">{file.name}</span>
                  <button
                    onClick={() => removePendingFile(i)}
                    className="ml-0.5 p-0.5 rounded hover:bg-white/10 text-white/30 hover:text-white/60 transition-colors transform hover:scale-110"
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
          <div className="flex items-end gap-1.5 sm:gap-2">
            {/* Attach button */}
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || uploading || !chatId}
              className="p-2 sm:p-2.5 rounded-lg sm:rounded-xl bg-white/[0.06] border border-white/[0.08] text-white/40 hover:text-white/70 hover:bg-white/[0.1] transition-all disabled:opacity-30 transform hover:scale-110 active:scale-95 flex-shrink-0"
              title="Attach files (PDF, DOCX, TXT, Images)"
              id="attach-button"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sm:w-[18px] sm:h-[18px]">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
            </button>

            {/* Clear button */}
            <button
              onClick={handleClear}
              disabled={loading || uploading || !chatId || messages.length === 0}
              className="p-2 sm:p-2.5 rounded-lg sm:rounded-xl bg-white/[0.06] border border-white/[0.08] text-white/40 hover:text-red-400 hover:bg-red-500/5 transition-all disabled:opacity-30 transform hover:scale-110 active:scale-95 flex-shrink-0"
              title="Clear chat history"
              id="clear-button"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sm:w-[18px] sm:h-[18px]">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <line x1="10" y1="11" x2="10" y2="17" />
                <line x1="14" y1="11" x2="14" y2="17" />
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
              placeholder={chatId ? "Message... (Shift+Enter)" : "Select chat"}
              disabled={loading || uploading || !chatId}
              rows={1}
              className="flex-1 bg-white/[0.06] border border-white/[0.08] rounded-lg sm:rounded-xl px-3 sm:px-4 py-2 sm:py-2.5 text-sm text-white placeholder:text-white/25 outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all disabled:opacity-50 resize-none overflow-y-auto"
              style={{ maxHeight: "150px" }}
              id="chat-input"
            />

            {/* Send / Stop button */}
            {loading ? (
              <button
                onClick={handleStop}
                className="p-2 sm:p-2.5 rounded-lg sm:rounded-xl bg-white/[0.06] border border-white/[0.08] text-white hover:bg-white/[0.1] hover:text-red-400 transition-all transform hover:scale-110 active:scale-95 flex-shrink-0"
                id="stop-button"
                title="Pause/Stop generation"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="sm:w-[18px] sm:h-[18px]">
                  <rect x="6" y="6" width="12" height="12" rx="2" ry="2" />
                </svg>
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={(uploading || !chatId) || (!input.trim() && pendingFiles.length === 0)}
                className="p-2 sm:p-2.5 rounded-lg sm:rounded-xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white-force hover:opacity-90 hover:shadow-lg hover:shadow-indigo-500/30 transition-all disabled:opacity-30 disabled:cursor-not-allowed transform hover:scale-110 active:scale-95 flex-shrink-0"
                id="send-button"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="sm:w-[18px] sm:h-[18px]">
                  <line x1="22" y1="2" x2="11" y2="13" />
                  <polygon points="22 2 15 22 11 13 2 9 22 2" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
