"use client";

import { useEffect, useState } from "react";
import OrlixaLogo from "./OrlixaLogo";
import {
  AuthUser,
  loginWithEmail,
  registerWithEmail,
  requestOtp,
  verifyOtp,
} from "@/lib/api";
import ThemeToggle from "./ThemeToggle";

const ICON_SHIELD = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-400">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const ICON_WORKSPACE = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-violet-400">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="9" y1="3" x2="9" y2="21" />
  </svg>
);

const ICON_GOOGLE = (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-400">
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v8" />
    <path d="M8 12h8" />
  </svg>
);

const ICON_EMAIL = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" />
    <polyline points="22,6 12,13 2,6" />
  </svg>
);

const ICON_LOCK = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

const ICON_USER = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

export default function AuthPanel({
  onAuthenticated,
}: {
  onAuthenticated: (user: AuthUser) => void;
}) {
  const [mode, setMode] = useState<"login" | "signup" | "otp">("login");
  const [otpStep, setOtpStep] = useState<"request" | "verify">("request");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);

  const handleModeChange = (newMode: "login" | "signup" | "otp") => {
    setIsTransitioning(true);
    setTimeout(() => {
      setMode(newMode);
      setOtpStep("request");
      setError("");
      setFullName("");
      setEmail("");
      setPassword("");
      setOtpCode("");
      setIsTransitioning(false);
    }, 200);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (mode === "otp") {
        if (otpStep === "request") {
          await requestOtp(email);
          setOtpStep("verify");
        } else {
          const auth = await verifyOtp(email, otpCode);
          if (auth.user) onAuthenticated(auth.user);
        }
      } else {
        const auth =
          mode === "signup"
            ? await registerWithEmail(email, password, fullName)
            : await loginWithEmail(email, password);
            
        if (auth.requires_otp) {
          setIsTransitioning(true);
          setTimeout(() => {
            setMode("otp");
            setOtpStep("verify");
            setError("Please enter the OTP sent to your email to continue.");
            setIsTransitioning(false);
          }, 200);
        } else if (auth.user) {
          onAuthenticated(auth.user);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#09090b] bg-mesh text-white flex items-center justify-center px-4 sm:px-6 py-8 sm:py-12 animate-fade-in overflow-x-hidden relative">
      <div className="absolute top-4 right-4 sm:top-8 sm:right-8 z-50">
        <ThemeToggle />
      </div>
      <div className="w-full max-w-5xl grid gap-8 md:grid-cols-[1.2fr_0.8fr] items-center">
        
        {/* Left Section: Value Proposition */}
        <section className="space-y-8 sm:space-y-12 animate-slide-in-left p-2 sm:p-0">
          <div className="space-y-4">
            <OrlixaLogo />
            <h1 className="text-3xl sm:text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight leading-[1.1] text-header-gradient">
              Private AI chats <br className="hidden sm:block" />
              for every user.
            </h1>
            <p className="text-base sm:text-lg text-white/50 max-w-lg leading-relaxed">
              Experience the power of Hybrid RAG with complete privacy. Your data, your conversations, 
              isolated and secure in your own workspace.
            </p>
          </div>

          <div className="grid gap-4 sm:gap-6 max-w-xl">
            {[
              { 
                icon: ICON_SHIELD, 
                title: "Complete Isolation", 
                desc: "Uploaded files and chat history are isolated per account." 
              },
              { 
                icon: ICON_WORKSPACE, 
                title: "Personal Workspace", 
                desc: "Each user gets a dedicated retrieval environment." 
              },
              { 
                icon: ICON_GOOGLE, 
                title: "Modern Access", 
                desc: "Secure login and upcoming Google OAuth support." 
              }
            ].map((feature, i) => (
              <div 
                key={i} 
                className="group glass-card rounded-2xl p-4 sm:p-5 flex items-start gap-4 transition-all hover:bg-white/[0.06] hover:translate-x-2 animate-in"
                style={{ animationDelay: `${0.1 * (i + 1)}s` }}
              >
                <div className="p-2 sm:p-2.5 rounded-xl bg-white/[0.05] border border-white/[0.08] transition-colors group-hover:border-white/20">
                  {feature.icon}
                </div>
                <div className="space-y-1">
                  <h3 className="text-sm sm:text-base font-semibold text-white/90">{feature.title}</h3>
                  <p className="text-xs sm:text-sm text-white/40 leading-normal">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right Section: Auth Form */}
        <section className={`relative transition-smooth ${isTransitioning ? "opacity-50 scale-95" : "opacity-100 animate-slide-in-right"}`}>
          {/* Subtle Glow Background */}
          <div className="absolute -inset-4 bg-indigo-500/10 blur-[60px] rounded-full -z-10 animate-pulse-subtle" />
          
          <div className="glass-card rounded-[32px] sm:rounded-[40px] p-6 sm:p-8 md:p-10 shadow-2xl relative overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between gap-4 mb-8 sm:mb-10">
              <div>
                <p className="text-[10px] sm:text-xs uppercase tracking-[0.2em] text-white/30 font-bold mb-1 sm:mb-2">
                  Access Portal
                </p>
                <h2 className="text-2xl sm:text-3xl font-bold transition-smooth">
                  {mode === "signup" ? "Create Account" : mode === "otp" ? "Login via OTP" : "Welcome Back"}
                </h2>
              </div>
              <div className="flex flex-col items-end gap-1">
                <button
                  type="button"
                  onClick={() => handleModeChange(mode === "signup" ? "login" : "signup")}
                  disabled={isTransitioning}
                  className="text-xs sm:text-sm text-indigo-400 hover:text-indigo-300 font-medium transition-colors disabled:opacity-50 underline-offset-4 hover:underline"
                >
                  {mode === "signup" ? "Login" : "Sign Up"}
                </button>
                <button
                  type="button"
                  onClick={() => handleModeChange(mode === "otp" ? "login" : "otp")}
                  disabled={isTransitioning}
                  className="text-[10px] sm:text-xs text-white/40 hover:text-white/60 transition-colors disabled:opacity-50"
                >
                  {mode === "otp" ? "Use Password" : "Use OTP"}
                </button>
              </div>
            </div>

            {!isTransitioning && (
              <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5 animate-scale-in">
                {mode === "signup" && (
                  <div className="space-y-1.5 sm:space-y-2 animate-slide-in-bottom">
                    <label className="text-xs sm:text-sm font-medium text-white/60 ml-1">Full Name</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30">{ICON_USER}</span>
                      <input
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="Mayur Chauhan"
                        className="w-full rounded-xl sm:rounded-2xl border border-white/[0.08] bg-black/30 pl-11 pr-4 py-3 sm:py-3.5 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/50 transition-all focus:ring-1 focus:ring-indigo-500/20"
                        disabled={loading}
                      />
                    </div>
                  </div>
                )}

                  <div className="space-y-1.5 sm:space-y-2">
                    <label className="text-xs sm:text-sm font-medium text-white/60 ml-1">Email Address</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30">{ICON_EMAIL}</span>
                      <input
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        type="email"
                        autoComplete="email"
                        placeholder="name@example.com"
                        className="w-full rounded-xl sm:rounded-2xl border border-white/[0.08] bg-black/30 pl-11 pr-4 py-3 sm:py-3.5 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/50 transition-all focus:ring-1 focus:ring-indigo-500/20"
                        required
                        disabled={loading || (mode === "otp" && otpStep === "verify")}
                      />
                    </div>
                  </div>

                {mode !== "otp" ? (
                  <div className="space-y-1.5 sm:space-y-2">
                    <label className="text-xs sm:text-sm font-medium text-white/60 ml-1">Password</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30">{ICON_LOCK}</span>
                      <input
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        type="password"
                        autoComplete={mode === "signup" ? "new-password" : "current-password"}
                        placeholder="••••••••"
                        className="w-full rounded-xl sm:rounded-2xl border border-white/[0.08] bg-black/30 pl-11 pr-4 py-3 sm:py-3.5 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/50 transition-all focus:ring-1 focus:ring-indigo-500/20"
                        required
                        disabled={loading}
                      />
                    </div>
                  </div>
                ) : (
                  otpStep === "verify" && (
                    <div className="space-y-1.5 sm:space-y-2 animate-slide-in-bottom">
                      <label className="text-xs sm:text-sm font-medium text-white/60 ml-1">OTP Code</label>
                      <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30">{ICON_SHIELD}</span>
                        <input
                          value={otpCode}
                          onChange={(e) => setOtpCode(e.target.value)}
                          placeholder="000000"
                          maxLength={6}
                          className="w-full rounded-xl sm:rounded-2xl border border-white/[0.08] bg-black/30 pl-11 pr-4 py-3 sm:py-3.5 text-sm outline-none focus:border-indigo-500/50 focus:bg-black/50 transition-all focus:ring-1 focus:ring-indigo-500/20 tracking-[0.5em] font-mono text-center"
                          required
                          disabled={loading}
                        />
                      </div>
                    </div>
                  )
                )}

                {error && (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-xs sm:text-sm text-red-400 animate-slide-in-bottom flex items-center gap-2">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full rounded-xl sm:rounded-2xl bg-gradient-to-r from-indigo-600 to-violet-600 px-4 py-3.5 text-sm font-bold text-white-force hover:opacity-95 hover:shadow-xl hover:shadow-indigo-500/30 transition-all disabled:opacity-60 disabled:hover:shadow-none transform hover:scale-[1.01] active:scale-[0.99] mt-2 sm:mt-4 shadow-lg shadow-indigo-600/10"
                >
                   {loading ? (
                    <div className="flex items-center justify-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      <span>{mode === "otp" && otpStep === "request" ? "Sending OTP..." : "Authenticating..."}</span>
                    </div>
                  ) : (
                    mode === "signup" ? "Create Account" : mode === "otp" ? (otpStep === "request" ? "Send OTP" : "Verify & Sign In") : "Sign In"
                  )}
                </button>

                <p className="text-[10px] sm:text-xs text-center text-white/30 mt-6 sm:mt-8">
                  By continuing, you agree to our <span className="text-white/50 cursor-pointer hover:text-white/80 transition-colors">Terms of Service</span> and <span className="text-white/50 cursor-pointer hover:text-white/80 transition-colors">Privacy Policy</span>.
                </p>
              </form>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
