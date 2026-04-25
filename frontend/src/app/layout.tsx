import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "./cinematic.css";
import TopNav from "@/components/layout/TopNav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LLM Reliability Platform — Inference-Time Evaluation",
  description: "Production-grade behavioral evaluation dashboard for LLM inference-time distribution shaping, entropy analysis, and adversarial stress testing.",
  openGraph: {
    title: "LLM Reliability Evaluation Platform",
    description: "Real-time behavioral analysis and distribution shaping for language model inference pipelines.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen overflow-x-hidden bg-[#030712] text-slate-200`}
      >
        <div className="hollywood-grid" />
        <div className="hollywood-scanlines" />
        <div className="ambient-glow" />
        <div className="relative z-10 flex flex-col min-h-screen">
          <TopNav />
          <div className="flex-1 overflow-y-auto">
            {children}
          </div>
        </div>
      </body>
    </html>
  );
}
