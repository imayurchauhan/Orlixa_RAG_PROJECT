"use client";

import { useState, useEffect } from "react";
import {
  Template,
  listTemplates,
  createTemplate,
  updateTemplate,
  deleteTemplate
} from "@/lib/api";

export default function TemplateManager({ onClose }: { onClose: () => void }) {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingTemplate, setEditingTemplate] = useState<Partial<Template> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch (err) {
      setError("Failed to load templates");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingTemplate?.name || !editingTemplate?.instructions) return;

    setLoading(true);
    try {
      if (editingTemplate.id) {
        await updateTemplate(editingTemplate.id, editingTemplate);
      } else {
        await createTemplate(editingTemplate);
      }
      await loadTemplates();
      setEditingTemplate(null);
    } catch (err) {
      setError("Failed to save template");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this template?")) return;
    try {
      await deleteTemplate(id);
      await loadTemplates();
    } catch (err) {
      setError("Failed to delete template");
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#111113] border border-white/10 rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden animate-scale-in">

        {/* Header */}
        <div className="px-6 py-5 border-b border-white/5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">AI Personas</h2>
            <p className="text-xs text-white/40 mt-0.5">Customize how Orlixa responds to you</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl hover:bg-white/5 text-white/40 hover:text-white transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
              {error}
            </div>
          )}

          {editingTemplate ? (
            <form onSubmit={handleSave} className="space-y-4 animate-in">
              <div className="grid sm:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-white/50 ml-1">Template Name</label>
                  <input
                    value={editingTemplate.name || ""}
                    onChange={e => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                    placeholder="e.g. Creative Assistant"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-indigo-500/50 transition-colors"
                    required
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-white/50 ml-1">Tone / Style</label>
                  <input
                    value={editingTemplate.tone || ""}
                    onChange={e => setEditingTemplate({ ...editingTemplate, tone: e.target.value })}
                    placeholder="e.g. Professional & Detailed"
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-indigo-500/50 transition-colors"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-white/50 ml-1">Custom Instructions</label>
                <textarea
                  value={editingTemplate.instructions || ""}
                  onChange={e => setEditingTemplate({ ...editingTemplate, instructions: e.target.value })}
                  placeholder="Tell the AI how to behave, what to prioritize, or any special rules..."
                  rows={6}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm outline-none focus:border-indigo-500/50 transition-colors resize-none"
                  required
                />
              </div>

              <div className="flex items-center gap-3 py-2">
                <input
                  type="checkbox"
                  id="is_default"
                  checked={editingTemplate.is_default || false}
                  onChange={e => setEditingTemplate({ ...editingTemplate, is_default: e.target.checked })}
                  className="w-4 h-4 rounded border-white/10 bg-white/5 text-indigo-600 focus:ring-indigo-500/20"
                />
                <label htmlFor="is_default" className="text-sm text-white/70 select-none">Set as default for new chats</label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingTemplate(null)}
                  className="px-4 py-2 text-sm font-medium text-white/40 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-6 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-bold transition-all transform active:scale-95 disabled:opacity-50"
                >
                  {loading ? "Saving..." : "Save Persona"}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-semibold text-Black/80">Your Templates</h3>
                <button
                  onClick={() => setEditingTemplate({ name: "", tone: "", instructions: "", is_default: false })}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-indigo-400 text-xs font-bold transition-colors"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  New Template
                </button>
              </div>

              {loading && templates.length === 0 ? (
                <div className="py-20 flex justify-center">
                  <div className="w-6 h-6 border-2 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
                </div>
              ) : (
                <div className="grid gap-3">
                  {templates.map(t => (
                    <div
                      key={t.id}
                      className="group p-4 rounded-2xl bg-white/[0.03] border border-white/5 hover:bg-white/[0.05] hover:border-white/10 transition-all animate-in"
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-bold text-white/90 truncate">{t.name}</span>
                            {t.is_default && (
                              <span className="px-1.5 py-0.5 rounded-md bg-indigo-500/10 text-indigo-400 text-[9px] font-bold uppercase tracking-wider">Default</span>
                            )}
                          </div>
                          <p className="text-xs text-white/50 mb-2 font-medium">{t.tone}</p>
                          <p className="text-xs text-white/30 line-clamp-2 italic">"{t.instructions}"</p>
                        </div>
                        <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => setEditingTemplate(t)}
                            className="p-2 rounded-lg hover:bg-white/5 text-white/40 hover:text-white transition-colors"
                          >
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                            </svg>
                          </button>
                          {!t.is_default && (
                            <button
                              onClick={() => handleDelete(t.id)}
                              className="p-2 rounded-lg hover:bg-red-500/10 text-white/40 hover:text-red-400 transition-colors"
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" /><path d="M10 11v6" /><path d="M14 11v6" /><path d="M9 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-white/[0.02] border-t border-white/5 text-center">
          <p className="text-[10px] text-white/20 uppercase tracking-widest font-bold">Personalized AI Intelligence · Orlixa</p>
        </div>
      </div>
    </div>
  );
}
