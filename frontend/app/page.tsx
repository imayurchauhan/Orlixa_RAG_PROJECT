"use client";

import { useState, useCallback, useEffect } from "react";
import Chat from "./components/Chat";
import Sidebar from "./components/Sidebar";
import OrlixaLogo from "./components/OrlixaLogo";
import SplashLoader from "./components/SplashLoader";
import AuthPanel from "./components/AuthPanel";
import {
  ApiError,
  AuthUser,
  Chat as ChatType,
  clearStoredSession,
  createChat,
  deleteChat,
  fetchCurrentUser,
  getFiles,
  hasStoredSession,
  listChats,
} from "@/lib/api";

export default function Home() {
  const [authReady, setAuthReady] = useState(false);
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [chats, setChats] = useState<ChatType[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

  useEffect(() => {
    if (!hasStoredSession()) {
      setAuthReady(true);
      return;
    }

    fetchCurrentUser()
      .then((user) => setCurrentUser(user))
      .catch(() => {
        clearStoredSession();
        setCurrentUser(null);
      })
      .finally(() => setAuthReady(true));
  }, []);

  const handleLogout = useCallback(() => {
    clearStoredSession();
    setCurrentUser(null);
    setChats([]);
    setActiveChatId(null);
    setUploadedFiles([]);
    setAuthReady(true);
  }, []);

  const loadChats = useCallback(async () => {
    if (!currentUser) return;
    try {
      const fetched = await listChats();
      if (fetched.length === 0) {
        const newChat = await createChat("New Chat");
        setChats([newChat]);
        setActiveChatId(newChat.id);
      } else {
        setChats(fetched);
        setActiveChatId((prev) => (
          prev && fetched.some((chat) => chat.id === prev) ? prev : fetched[0].id
        ));
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleLogout();
      }
    }
  }, [currentUser, handleLogout]);

  useEffect(() => {
    if (!authReady) return;
    if (!currentUser) {
      setChats([]);
      setActiveChatId(null);
      setUploadedFiles([]);
      return;
    }
    loadChats();
  }, [authReady, currentUser, loadChats]);

  const fetchFiles = useCallback(async () => {
    if (!activeChatId) return;
    try {
      const res = await getFiles(activeChatId);
      setUploadedFiles(res.files);
    } catch (err) {
      setUploadedFiles([]);
      if (err instanceof ApiError && err.status === 401) {
        handleLogout();
      }
    }
  }, [activeChatId, handleLogout]);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleNewChat = useCallback(async () => {
    try {
      const newChat = await createChat("New Chat");
      setChats((prev) => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      setUploadedFiles([]);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleLogout();
      }
    }
  }, [handleLogout]);

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
              createChat("New Chat").then((newChat) => {
                setChats([newChat]);
                setActiveChatId(newChat.id);
              });
              return [];
            }
          }
          return remaining;
        });
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) {
          handleLogout();
        }
      }
    },
    [activeChatId, handleLogout]
  );

  const handleRenameChat = useCallback((id: string, title: string) => {
    setChats((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
  }, []);

  if (!authReady) {
    return <SplashLoader />;
  }

  if (!currentUser) {
    return (
      <AuthPanel
        onAuthenticated={(user) => {
          setCurrentUser(user);
          setChats([]);
          setActiveChatId(null);
          setUploadedFiles([]);
          setAuthReady(true);
        }}
      />
    );
  }

  return (
    <>
      <SplashLoader />
      <main className="flex h-screen overflow-hidden">
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

        <div
          className={`flex flex-col flex-1 min-w-0 transition-all duration-300 ${sidebarOpen ? "ml-64" : "ml-0"}`}
        >
          <header className="flex items-center justify-between px-5 py-3 border-b border-white/[0.06] bg-black/30 backdrop-blur-xl">
            <div className={`flex items-center gap-3 ${sidebarOpen ? "" : "pl-10"}`}>
              {!sidebarOpen && <OrlixaLogo compact />}
              {activeChatId && (
                <span className="text-sm text-white/50 font-medium truncate max-w-[200px]">
                  {chats.find((c) => c.id === activeChatId)?.title ?? ""}
                </span>
              )}
            </div>

            <div className="flex items-center gap-3">
              <div className="hidden sm:flex items-center gap-3 px-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.06]">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500/80 to-violet-500/80 flex items-center justify-center text-xs font-semibold">
                  {(currentUser.full_name || currentUser.email).slice(0, 1).toUpperCase()}
                </div>
                <div className="leading-tight">
                  <p className="text-sm text-white/85">
                    {currentUser.full_name || currentUser.email}
                  </p>
                  <p className="text-[11px] text-white/35">{currentUser.email}</p>
                </div>
              </div>

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

              <button
                onClick={handleLogout}
                className="px-3 py-2 rounded-xl bg-white/[0.05] border border-white/[0.07] text-sm text-white/70 hover:text-white hover:bg-white/[0.08] transition-all"
              >
                Sign out
              </button>
            </div>
          </header>

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
