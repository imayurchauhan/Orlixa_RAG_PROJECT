"use client";

import Image from "next/image";

/**
 * Orlixa brand logo with animated letter reveal and pulsing glow.
 * Used in sidebar header and collapsed-sidebar header.
 */
export default function OrlixaLogo({ compact = false }: { compact?: boolean }) {
  return (
    <div className="orlixa-brand-group flex items-center gap-2.5 select-none cursor-default">
      {/* Animated neural-network icon */}
      <div className="orlixa-logo-icon flex-shrink-0">
        <Image
          src="/logo.svg"
          alt="Orlixa logo"
          width={compact ? 28 : 34}
          height={compact ? 28 : 34}
          priority
        />
      </div>

      {/* Brand text */}
      <div className="min-w-0">
        <h1
          className={`font-bold tracking-tight leading-none ${
            compact ? "text-sm" : "text-lg"
          }`}
          style={{
            background: "linear-gradient(135deg, #4F46E5, #06B6D4)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            backgroundClip: "text",
            textShadow: "0 0 20px rgba(79, 70, 229, 0.3)",
          }}
        >
          Orlixa
        </h1>
        <p
          className={`text-white/35 leading-none ${
            compact ? "text-[9px] mt-0.5" : "text-[10px] mt-1"
          }`}
        >
          AI-Powered Knowledge Intelligence
        </p>
      </div>
    </div>
  );
}
