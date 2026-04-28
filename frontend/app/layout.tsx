import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "Orlixa — AI-Powered Knowledge Intelligence",
  description: "Intelligent document Q&A with web search and AI, powered by Orlixa",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col bg-[#09090b] text-white font-[family-name:var(--font-inter)]">
        {children}
      </body>
    </html>
  );
}
