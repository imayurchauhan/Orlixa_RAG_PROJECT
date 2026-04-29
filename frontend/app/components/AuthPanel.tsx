"use client";

import { useEffect, useState } from "react";
import OrlixaLogo from "./OrlixaLogo";
import {
  AuthUser,
  loginWithEmail,
  registerWithEmail,
} from "@/lib/api";

export default function AuthPanel({
  onAuthenticated,
}: {
  onAuthenticated: (user: AuthUser) => void;
}) {
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleModeChange = () => {
    setIsTransitioning(true);
    setTimeout(() => {
      setMode((prev) => (prev === "login" ? "signup" : "login"));
      setError("");
      setFullName("");
      setEmail("");
      setPassword("");
      setIsTransitioning(false);
    }, 200);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const auth =
        mode === "signup"
          ? await registerWithEmail(email, password, fullName)
          : await loginWithEmail(email, password);
      onAuthenticated(auth.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#09090b] text-white flex items-center justify-center px-4 sm:px-6 py-8 sm:py-10 animate-fade-in">
        <div className="w-full max-w-5xl grid gap-6 sm:gap-8 md:grid-cols-[1.1fr_0.9fr] items-stretch">
          <section className="rounded-2xl sm:rounded-[32px] border border-white/[0.08] bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.22),_transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-6 sm:p-8 md:p-10 animate-slide-in-left">
            <OrlixaLogo />
            <div className="mt-8 sm:mt-10 space-y-4 sm:space-y-5 max-w-xl">
              <h1 className="text-2xl sm:text-3xl md:text-4xl font-semibold tracking-tight">
                Private AI chats for every user.
              </h1>
              <p className="text-sm sm:text-base text-white/65 leading-6 sm:leading-7">
                Sign in to keep your conversations, uploaded files, and retrieval results isolated per account.
                Each user now gets a separate workspace.
              </p>
              <div className="grid gap-2 sm:gap-3 text-xs sm:text-sm text-white/70">
                <div className="rounded-lg sm:rounded-2xl border border-white/[0.07] bg-white/[0.03] px-3 sm:px-4 py-2 sm:py-3 animate-in" style={{ animationDelay: "0.1s" }}>
                  Email and password login for direct account access
                </div>
                <div className="rounded-lg sm:rounded-2xl border border-white/[0.07] bg-white/[0.03] px-3 sm:px-4 py-2 sm:py-3 animate-in" style={{ animationDelay: "0.2s" }}>
                  🔜 Google sign-in coming soon
                </div>
                <div className="rounded-lg sm:rounded-2xl border border-white/[0.07] bg-white/[0.03] px-3 sm:px-4 py-2 sm:py-3 animate-in" style={{ animationDelay: "0.3s" }}>
                  Chats, uploads, and answers scoped to the current authenticated user
                </div>
              </div>
            </div>
          </section>

          <section className={`rounded-2xl sm:rounded-[32px] border border-white/[0.08] bg-white/[0.04] backdrop-blur-xl p-6 sm:p-8 md:p-10 transition-smooth ${isTransitioning ? "opacity-50" : "opacity-100 animate-slide-in-right"}`}>
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 sm:gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.2em] text-white/35">
                  Access
                </p>
                <h2 className="mt-2 text-xl sm:text-2xl font-semibold transition-smooth">
                  {mode === "signup" ? "Create account" : "Welcome back"}
                </h2>
              </div>
              <button
                type="button"
                onClick={handleModeChange}
                disabled={isTransitioning}
                className="text-xs sm:text-sm text-indigo-300 hover:text-indigo-200 transition-colors disabled:opacity-50 whitespace-nowrap"
              >
                {mode === "signup" ? "Have an account?" : "Create account"}
              </button>
            </div>

            {!isTransitioning && (
              <form onSubmit={handleSubmit} className="mt-6 sm:mt-8 space-y-4 animate-scale-in">
                {mode === "signup" && (
                  <div className="animate-slide-in-bottom">
                    <label className="block text-xs sm:text-sm text-white/60 mb-2">Full name</label>
                    <input
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="Your name"
                      className="w-full rounded-lg sm:rounded-2xl border border-white/[0.08] bg-black/25 px-3 sm:px-4 py-2 sm:py-3 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/35 transition-colors"
                      disabled={loading}
                    />
                  </div>
                )}

                <div>
                  <label className="block text-xs sm:text-sm text-white/60 mb-2">Email</label>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    className="w-full rounded-lg sm:rounded-2xl border border-white/[0.08] bg-black/25 px-3 sm:px-4 py-2 sm:py-3 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/35 transition-colors"
                    required
                    disabled={loading}
                  />
                </div>

                <div>
                  <label className="block text-xs sm:text-sm text-white/60 mb-2">Password</label>
                  <input
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    type="password"
                    autoComplete={mode === "signup" ? "new-password" : "current-password"}
                    placeholder="Minimum 8 characters"
                    className="w-full rounded-lg sm:rounded-2xl border border-white/[0.08] bg-black/25 px-3 sm:px-4 py-2 sm:py-3 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/35 transition-colors"
                    required
                    disabled={loading}
                  />
                </div>

                {error && (
                  <div className="rounded-lg sm:rounded-2xl border border-red-500/20 bg-red-500/10 px-3 sm:px-4 py-2 sm:py-3 text-xs sm:text-sm text-red-200 animate-slide-in-bottom">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-lg sm:rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-medium text-white hover:opacity-95 hover:shadow-lg transition-all disabled:opacity-60 disabled:hover:shadow-none transform hover:scale-[1.02] active:scale-95"
                >
                  {loading ? "Please wait..." : mode === "signup" ? "Create account" : "Sign in"}
                </button>
              </form>
            )}
          </section>
        </div>
      </main>
    );
  }
