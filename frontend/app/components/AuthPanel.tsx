"use client";

import { useEffect, useRef, useState } from "react";
import Script from "next/script";
import OrlixaLogo from "./OrlixaLogo";
import {
  AuthUser,
  loginWithEmail,
  loginWithGoogle,
  registerWithEmail,
} from "@/lib/api";

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }) => void;
          renderButton: (
            element: HTMLElement,
            options: Record<string, string | number>
          ) => void;
        };
      };
    };
  }
}

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";

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
  const [googleLoaded, setGoogleLoaded] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!googleLoaded || !GOOGLE_CLIENT_ID || !window.google || !googleButtonRef.current) {
      return;
    }

    googleButtonRef.current.innerHTML = "";
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        if (!response.credential) {
          setError("Google login did not return a credential.");
          return;
        }

        setLoading(true);
        setError("");
        try {
          const auth = await loginWithGoogle(response.credential);
          onAuthenticated(auth.user);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Google login failed");
        } finally {
          setLoading(false);
        }
      },
    });

    window.google.accounts.id.renderButton(googleButtonRef.current, {
      theme: "outline",
      size: "large",
      shape: "pill",
      width: 320,
      text: mode === "signup" ? "signup_with" : "signin_with",
    });
  }, [googleLoaded, mode, onAuthenticated]);

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
    <>
      {GOOGLE_CLIENT_ID && (
        <Script
          src="https://accounts.google.com/gsi/client"
          strategy="afterInteractive"
          onLoad={() => setGoogleLoaded(true)}
        />
      )}

      <main className="min-h-screen bg-[#09090b] text-white flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-5xl grid gap-8 lg:grid-cols-[1.1fr_0.9fr] items-stretch">
          <section className="rounded-[32px] border border-white/[0.08] bg-[radial-gradient(circle_at_top,_rgba(99,102,241,0.22),_transparent_45%),linear-gradient(180deg,rgba(255,255,255,0.04),rgba(255,255,255,0.02))] p-8 lg:p-10">
            <OrlixaLogo />
            <div className="mt-10 space-y-5 max-w-xl">
              <h1 className="text-4xl font-semibold tracking-tight">
                Private AI chats for every user.
              </h1>
              <p className="text-white/65 leading-7">
                Sign in to keep your conversations, uploaded files, and retrieval results isolated per account.
                Each user now gets a separate workspace.
              </p>
              <div className="grid gap-3 text-sm text-white/70">
                <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] px-4 py-3">
                  Email and password login for direct account access
                </div>
                <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] px-4 py-3">
                  Google sign-in for faster onboarding when configured
                </div>
                <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] px-4 py-3">
                  Chats, uploads, and answers scoped to the current authenticated user
                </div>
              </div>
            </div>
          </section>

          <section className="rounded-[32px] border border-white/[0.08] bg-white/[0.04] backdrop-blur-xl p-8 lg:p-10">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.2em] text-white/35">
                  Access
                </p>
                <h2 className="mt-2 text-2xl font-semibold">
                  {mode === "signup" ? "Create account" : "Welcome back"}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => {
                  setMode((prev) => (prev === "login" ? "signup" : "login"));
                  setError("");
                }}
                className="text-sm text-indigo-300 hover:text-indigo-200 transition-colors"
              >
                {mode === "signup" ? "Have an account?" : "Create account"}
              </button>
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-4">
              {mode === "signup" && (
                <div>
                  <label className="block text-sm text-white/60 mb-2">Full name</label>
                  <input
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Your name"
                    className="w-full rounded-2xl border border-white/[0.08] bg-black/25 px-4 py-3 text-sm outline-none focus:border-indigo-500/50"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm text-white/60 mb-2">Email</label>
                <input
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  className="w-full rounded-2xl border border-white/[0.08] bg-black/25 px-4 py-3 text-sm outline-none focus:border-indigo-500/50"
                  required
                />
              </div>

              <div>
                <label className="block text-sm text-white/60 mb-2">Password</label>
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  autoComplete={mode === "signup" ? "new-password" : "current-password"}
                  placeholder="Minimum 8 characters"
                  className="w-full rounded-2xl border border-white/[0.08] bg-black/25 px-4 py-3 text-sm outline-none focus:border-indigo-500/50"
                  required
                />
              </div>

              {error && (
                <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3 text-sm font-medium text-white hover:opacity-95 transition-opacity disabled:opacity-60"
              >
                {loading ? "Please wait..." : mode === "signup" ? "Create account" : "Sign in"}
              </button>
            </form>

            <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-[0.2em] text-white/25">
              <div className="h-px flex-1 bg-white/[0.08]" />
              or
              <div className="h-px flex-1 bg-white/[0.08]" />
            </div>

            {GOOGLE_CLIENT_ID ? (
              <div ref={googleButtonRef} className="min-h-[44px]" />
            ) : (
              <div className="rounded-2xl border border-white/[0.08] bg-black/20 px-4 py-3 text-sm text-white/45">
                Google sign-in will appear after you set <code>NEXT_PUBLIC_GOOGLE_CLIENT_ID</code>.
              </div>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
