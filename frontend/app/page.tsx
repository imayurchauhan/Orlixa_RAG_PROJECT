"use client";

import { useState, useCallback, useEffect } from "react";
import Chat from "./components/Chat";
import Sidebar from "./components/Sidebar";
import ThemeToggle from "./components/ThemeToggle";
import SplashLoader from "./components/SplashLoader";
import AuthPanel from "./components/AuthPanel";
import TemplateManager from "./components/TemplateManager";
import PersonaSelector from "./components/PersonaSelector";
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
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [showTemplateManager, setShowTemplateManager] = useState(false);
  const [chatRefreshKey, setChatRefreshKey] = useState(0);

  useEffect(() => {
    (window as any).toggleTemplateManager = () => setShowTemplateManager(true);
  }, []);

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
    setIsLoggingOut(true);
    setTimeout(() => {
      clearStoredSession();
      setCurrentUser(null);
      setChats([]);
      setActiveChatId(null);
      setUploadedFiles([]);
      setAuthReady(true);
      setIsLoggingOut(false);
    }, 300);
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
      <main className={`flex h-screen w-full overflow-hidden transition-smooth ${isLoggingOut ? "animate-fade-out opacity-0" : "opacity-100"}`}>
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

        {/* small fixed logo button shown when sidebar is closed so users can open it */}
        {!sidebarOpen && (
          <div className="fixed top-3 sm:top-4 left-3 z-[60]">
            <button onClick={() => setSidebarOpen(true)} aria-label="Open sidebar">
              <div className="p-1 rounded-lg bg-white/[0.04] border border-white/[0.06]">
                <img src="/logo.svg" alt="Orlixa" width={28} height={28} />
              </div>
            </button>
          </div>
        )}

        <div className={`flex flex-col flex-1 w-full min-w-0 transition-all duration-300` }>
          <header className={`flex items-center justify-between px-3 sm:px-5 py-2.5 sm:py-3 border-b border-white/[0.06] bg-black/30 backdrop-blur-xl animate-slide-in-top gap-2 sm:gap-0 z-50 ${!sidebarOpen ? 'pl-12 sm:pl-14' : ''}`}>
            <div className={`flex items-center gap-2 sm:gap-3 min-w-0 flex-1` }>
              {activeChatId && (
                <>
                  <span className="text-xs sm:text-sm text-white/50 font-medium truncate max-w-[120px] sm:max-w-[180px]">
                    {chats.find((c) => c.id === activeChatId)?.title ?? ""}
                  </span>
                  <div className="w-px h-3 bg-white/10 mx-1" />
                  <PersonaSelector 
                    chatId={activeChatId}
                    currentTemplateId={chats.find(c => c.id === activeChatId)?.template_id}
                    onTemplateChanged={() => {
                      loadChats();
                      setChatRefreshKey(k => k + 1);
                    }}
                  />
                </>
              )}
            </div>

            <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
              <div className="hidden sm:flex items-center gap-2 sm:gap-3 px-2 sm:px-3 py-1.5 rounded-lg sm:rounded-xl bg-white/[0.04] border border-white/[0.06] animate-fade-in min-w-0" style={{ animationDelay: "0.1s" }}>
                <div className="w-6 sm:w-8 h-6 sm:h-8 rounded-full bg-gradient-to-br from-indigo-500/80 to-violet-500/80 flex items-center justify-center text-xs font-semibold flex-shrink-0 text-white-force">
                  {(currentUser.full_name || currentUser.email).slice(0, 1).toUpperCase()}
                </div>
                <div className="leading-tight hidden sm:block">
                  <p className="text-xs sm:text-sm text-white/85 truncate">
                    {currentUser.full_name || currentUser.email}
                  </p>
                  <p className="text-[10px] text-white/35 truncate">{currentUser.email}</p>
                </div>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 rounded-lg sm:rounded-xl bg-violet-500/10 border border-violet-500/20 animate-pulse-subtle flex-shrink-0">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400 flex-shrink-0">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span className="text-xs text-violet-300 font-medium hidden sm:inline">
                    {uploadedFiles.length} file{uploadedFiles.length > 1 ? "s" : ""}
                  </span>
                  <span className="text-[10px] text-violet-300 font-medium sm:hidden">
                    {uploadedFiles.length}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <ThemeToggle />
                <button
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                  className="px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg sm:rounded-xl bg-white/[0.05] border border-white/[0.07] text-xs sm:text-sm text-white/70 hover:text-white hover:bg-white/[0.08] transition-all hover:scale-[1.05] disabled:opacity-50 transform flex-shrink-0"
                >
                  <span className="hidden sm:inline">Sign out</span>
                  <span className="sm:hidden">Sign out</span>
                </button>
              </div>
            </div>
          </header>

          <div className="flex-1 h-full overflow-hidden">
            <Chat
              key={(activeChatId ?? "no-chat") + chatRefreshKey}
              chatId={activeChatId}
              sessionId={activeChatId ?? ""}
              onFilesChanged={fetchFiles}
            />
          </div>
        </div>
      </main>

      {showTemplateManager && (
        <TemplateManager onClose={() => setShowTemplateManager(false)} />
      )}
    </>
  );
}
