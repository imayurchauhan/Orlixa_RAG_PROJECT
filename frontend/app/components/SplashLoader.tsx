"use client";

import { useState, useEffect } from "react";
import Image from "next/image";

/**
 * Animated splash screen that shows the Orlixa branding
 * while the app initializes. Auto-hides after 2 seconds.
 */
export default function SplashLoader() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(false), 2400);
    return () => clearTimeout(timer);
  }, []);

  if (!visible) return null;

  const letters = "Orlixa".split("");

  return (
    <div className="orlixa-splash" aria-label="Loading Orlixa">
      {/* Rotating outer ring */}
      <div className="relative w-24 h-24 mb-6">
        <svg
          className="orlixa-splash-ring absolute inset-0 w-full h-full"
          viewBox="0 0 96 96"
          fill="none"
        >
          <circle
            cx="48"
            cy="48"
            r="44"
            stroke="url(#splash-ring-grad)"
            strokeWidth="1.5"
            strokeDasharray="8 6"
            opacity="0.5"
          />
          <defs>
            <linearGradient id="splash-ring-grad" x1="0" y1="0" x2="96" y2="96">
              <stop offset="0%" stopColor="#4F46E5" />
              <stop offset="50%" stopColor="#06B6D4" />
              <stop offset="100%" stopColor="#22C55E" />
            </linearGradient>
          </defs>
        </svg>
        {/* Floating logo */}
        <div className="orlixa-splash-logo absolute inset-0 flex items-center justify-center">
          <Image src="/logo.svg" alt="Orlixa" width={56} height={56} priority />
        </div>
      </div>

      {/* Brand name with letter animation */}
      <h1 className="text-3xl font-bold tracking-tight mb-3">
        {letters.map((char, i) => (
          <span key={i} className="orlixa-letter orlixa-brand-text">
            {char}
          </span>
        ))}
      </h1>

      {/* Status text */}
      <p className="orlixa-splash-status text-xs font-medium tracking-wide">
        Initializing Knowledge Engine...
      </p>
    </div>
  );
}
