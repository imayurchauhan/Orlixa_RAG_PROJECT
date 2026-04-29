"use client";

import { useState, useEffect } from "react";
import { Template, listTemplates, setChatTemplate } from "@/lib/api";

export default function PersonaSelector({ 
  chatId, 
  currentTemplateId,
  onTemplateChanged
}: { 
  chatId: string; 
  currentTemplateId?: string;
  onTemplateChanged: () => void;
}) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (isOpen) {
      listTemplates().then(setTemplates).catch(() => {});
    }
  }, [isOpen]);

  const handleSelect = async (templateId: string) => {
    try {
      await setChatTemplate(chatId, templateId);
      onTemplateChanged();
      setIsOpen(false);
    } catch (err) {
      console.error("Failed to set template", err);
      alert("Failed to change persona. Please try again.");
    }
  };

  const activeTemplate = templates.find(t => t.id === currentTemplateId) || 
                         templates.find(t => t.is_default);

  return (
    <div className="relative">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 hover:bg-indigo-500/20 transition-all group shadow-sm shadow-indigo-500/10"
        title="Change AI Persona"
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-400">
          <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="8.5" cy="7" r="4" /><polyline points="17 11 19 13 23 9" />
        </svg>
        <span className="text-[10px] sm:text-[11px] font-bold text-indigo-300 uppercase tracking-wide">
          {activeTemplate?.name || "Select Persona"}
        </span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className={`text-indigo-400/50 transition-transform ${isOpen ? "rotate-180" : ""}`}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-[90]" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full mt-2 left-0 w-64 border rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.3)] overflow-hidden z-[100] animate-slide-in-top persona-dropdown">
            <div className="px-3 py-2 border-b border-white/5 bg-white/[0.02]">
              <span className="text-[9px] font-bold text-white/30 uppercase tracking-widest">Active Persona</span>
            </div>
            <div className="max-h-60 overflow-y-auto p-1.5 space-y-0.5">
              {templates.map(t => (
                <button
                  key={t.id}
                  onClick={() => handleSelect(t.id)}
                  className={`w-full flex flex-col items-start px-3 py-2 rounded-xl transition-all ${
                    t.id === currentTemplateId 
                      ? "bg-indigo-500/10 border border-indigo-500/20" 
                      : "hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className={`text-xs font-bold ${t.id === currentTemplateId ? "text-indigo-400" : "text-white/80"}`}>{t.name}</span>
                    {t.is_default && <span className="text-[8px] font-bold text-white/20 uppercase tracking-tighter">Default</span>}
                  </div>
                  <span className="text-[10px] text-white/30 truncate w-full text-left">{t.tone}</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
