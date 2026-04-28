"use client";

import { useState, useCallback, useEffect } from "react";
import Chat from "./components/Chat";
import Sidebar from "./components/Sidebar";
import OrlixaLogo from "./components/OrlixaLogo";
import SplashLoader from "./components/SplashLoader";
import { createChat, listChats, deleteChat, getFiles, Chat as ChatType } from "@/lib/api";

export default function Home() {
  const [chats, setChats] = useState<ChatType[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  // Load all chats on mount, auto-create one if empty
  useEffect(() => {
    listChats()
      .then(async (fetched) => {
        if (fetched.length === 0) {
          const newChat = await createChat("New Chat");
          setChats([newChat]);
          setActiveChatId(newChat.id);
        } else {
          setChats(fetched);
          setActiveChatId(fetched[0].id);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch files for the active chat
  const fetchFiles = useCallback(async () => {
    if (!activeChatId) return;
    try {
      const res = await getFiles(activeChatId);
      setUploadedFiles(res.files);
    } catch {
      setUploadedFiles([]);
    }
  }, [activeChatId]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleNewChat = useCallback(async () => {
    try {
      const newChat = await createChat("New Chat");
      setChats((prev) => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      setUploadedFiles([]);
    } catch {}
  }, []);

  const handleSelectChat = useCallback((id: string) => {
    setActiveChatId(id);
    setUploadedFiles([]);
  }, []);

  const handleDeleteChat = useCallback(
    async (id: string) => {
      try {
        await deleteChat(id);
        setChats((prev) => {
          const remaining = prev.filter((c) => c.id !== id);
          if (id === activeChatId) {
            if (remaining.length > 0) {
              setActiveChatId(remaining[0].id);
            } else {
              // Auto-create a new chat if all are deleted
              createChat("New Chat").then((newChat) => {
                setChats([newChat]);
                setActiveChatId(newChat.id);
              });
              return [];
            }
          }
          return remaining;
        });
      } catch {}
    },
    [activeChatId]
  );

  const handleRenameChat = useCallback((id: string, title: string) => {
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
  }, []);

  return (
    <>
      <SplashLoader />
      <main className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onNewChat={handleNewChat}
        onDeleteChat={handleDeleteChat}
        onRenameChat={handleRenameChat}
        isOpen={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
      />

      {/* Main content area */}
      <div
        className={`flex flex-col flex-1 min-w-0 transition-all duration-300 ${sidebarOpen ? "ml-64" : "ml-0"}`}
      >
        {/* Header */}
        <header className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06] bg-black/30 backdrop-blur-xl">
          {/* Left spacer when sidebar is closed (toggle btn takes 40px) */}
          <div className={`flex items-center gap-3 ${sidebarOpen ? "" : "pl-10"}`}>
            {!sidebarOpen && (
              <OrlixaLogo compact />
            )}
            {/* Active chat title */}
            {activeChatId && (
              <span className="text-sm text-white/50 font-medium truncate max-w-[200px]">
                {chats.find((c) => c.id === activeChatId)?.title ?? ""}
              </span>
            )}
          </div>

          {/* Right side — file badge */}
          <div className="flex items-center gap-3">
            {uploadedFiles.length > 0 && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-violet-500/10 border border-violet-500/20">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                </svg>
                <span className="text-xs text-violet-300 font-medium">
                  {uploadedFiles.length} file{uploadedFiles.length > 1 ? "s" : ""}
                </span>
              </div>
            )}
          </div>
        </header>

        {/* Chat panel */}
        <div className="flex-1 overflow-hidden">
          <div className="max-w-3xl mx-auto h-full">
            <Chat
              key={activeChatId ?? "no-chat"}
              chatId={activeChatId}
              sessionId={activeChatId ?? ""}
              onFilesChanged={fetchFiles}
            />
          </div>
        </div>
      </div>
      </main>
    </>
  );
}
