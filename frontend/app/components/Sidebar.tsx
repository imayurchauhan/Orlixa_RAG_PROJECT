"use client";

import { useState, useEffect, useRef } from "react";
import { Chat, deleteChat, renameChat } from "@/lib/api";
import OrlixaLogo from "./OrlixaLogo";

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

interface SidebarProps {
  chats: Chat[];
  activeChatId: string | null;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
  onRenameChat: (id: string, title: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({
  chats,
  activeChatId,
  onSelectChat,
  onNewChat,
  onDeleteChat,
  onRenameChat,
  isOpen,
  onToggle,
}: SidebarProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const editRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editingId && editRef.current) {
      editRef.current.focus();
      editRef.current.select();
    }
  }, [editingId]);

  const handleDeleteClick = (e: React.MouseEvent, chatId: string) => {
    e.stopPropagation();
    if (deletingId === chatId) {
      onDeleteChat(chatId);
      setDeletingId(null);
    } else {
      setDeletingId(chatId);
      // Auto-cancel after 3s
      setTimeout(() => setDeletingId((cur) => (cur === chatId ? null : cur)), 3000);
    }
  };

  const handleDoubleClick = (e: React.MouseEvent, chat: Chat) => {
    e.stopPropagation();
    setEditingId(chat.id);
    setEditTitle(chat.title);
  };

  const commitRename = async (chatId: string) => {
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== chats.find((c) => c.id === chatId)?.title) {
      try {
        await renameChat(chatId, trimmed);
        onRenameChat(chatId, trimmed);
      } catch {}
    }
    setEditingId(null);
  };

  return (
    <>
      {/* Toggle button — always visible */}
      <button
        onClick={onToggle}
        className="fixed top-3 left-3 z-50 p-2 rounded-xl bg-white/[0.06] border border-white/[0.08] text-white/50 hover:text-white/80 hover:bg-white/[0.1] transition-all"
        title={isOpen ? "Close sidebar" : "Open sidebar"}
        id="sidebar-toggle"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          {isOpen ? (
            <>
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </>
          ) : (
            <>
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </>
          )}
        </svg>
      </button>

      {/* Sidebar panel */}
      <aside
        className={`fixed top-0 left-0 h-full z-40 flex flex-col bg-[#111113] border-r border-white/[0.06] transition-all duration-300 ease-in-out overflow-hidden ${
          isOpen ? "w-64 opacity-100" : "w-0 opacity-0"
        }`}
      >
        {/* Header — Orlixa branding */}
        <div className="px-4 pt-4 pb-3 mt-8">
          <OrlixaLogo />
        </div>

        {/* New chat button */}
        <div className="px-3 pb-3">
          <button
            onClick={onNewChat}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600/80 to-violet-600/80 hover:from-indigo-600 hover:to-violet-600 text-white text-sm font-medium transition-all active:scale-[0.98]"
            id="new-chat-button"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New Chat
          </button>
        </div>

        {/* Divider */}
        <div className="mx-3 border-t border-white/[0.06] mb-2" />

        {/* Chat list label */}
        <p className="px-4 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-white/25 select-none">
          History
        </p>

        {/* Chat list */}
        <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-0.5">
          {chats.length === 0 && (
            <div className="flex flex-col items-center justify-center py-10 text-white/20 select-none">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="mb-2 opacity-50">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <p className="text-xs">No chats yet</p>
            </div>
          )}
          {chats.map((chat) => {
            const isActive = chat.id === activeChatId;
            const isDeleting = deletingId === chat.id;
            const isEditing = editingId === chat.id;
            return (
              <div
                key={chat.id}
                onClick={() => !isEditing && onSelectChat(chat.id)}
                onDoubleClick={(e) => handleDoubleClick(e, chat)}
                className={`group relative flex items-center gap-2 px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 ${
                  isActive
                    ? "bg-indigo-600/20 border border-indigo-500/30"
                    : "hover:bg-white/[0.04] border border-transparent"
                }`}
              >
                {/* Chat icon */}
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`flex-shrink-0 ${isActive ? "text-indigo-400" : "text-white/30"}`}>
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>

                {/* Title / edit input */}
                <div className="flex-1 min-w-0">
                  {isEditing ? (
                    <input
                      ref={editRef}
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      onBlur={() => commitRename(chat.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRename(chat.id);
                        if (e.key === "Escape") setEditingId(null);
                        e.stopPropagation();
                      }}
                      onClick={(e) => e.stopPropagation()}
                      className="w-full bg-white/10 text-white text-xs rounded px-1.5 py-0.5 outline-none border border-indigo-500/40 focus:border-indigo-500"
                    />
                  ) : (
                    <>
                      <p className={`text-xs font-medium truncate ${isActive ? "text-white" : "text-white/70"}`}>
                        {chat.title}
                      </p>
                      <p className="text-[10px] text-white/25 mt-0.5">{timeAgo(chat.created_at)}</p>
                    </>
                  )}
                </div>

                {/* Delete button */}
                {!isEditing && (
                  <button
                    onClick={(e) => handleDeleteClick(e, chat.id)}
                    className={`flex-shrink-0 p-1 rounded-lg transition-all ${
                      isDeleting
                        ? "bg-red-500/30 text-red-400"
                        : "opacity-0 group-hover:opacity-100 text-white/30 hover:text-red-400 hover:bg-red-500/10"
                    }`}
                    title={isDeleting ? "Click again to confirm delete" : "Delete chat"}
                  >
                    {isDeleting ? (
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6l-1 14H6L5 6" />
                        <path d="M10 11v6M14 11v6" />
                        <path d="M9 6V4h6v2" />
                      </svg>
                    )}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-white/[0.04]">
          <p className="text-[10px] text-white/15 text-center select-none">Double-click title to rename</p>
        </div>
      </aside>
    </>
  );
}
