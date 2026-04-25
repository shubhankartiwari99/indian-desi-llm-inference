"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Activity, FlaskConical, LayoutDashboard, Zap } from "lucide-react"

export default function TopNav() {
  const pathname = usePathname()

  const links = [
    { href: "/", label: "Dashboard", icon: LayoutDashboard },
    { href: "/playground", label: "Playground", icon: FlaskConical },
  ]

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/60 bg-slate-950/70 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="relative p-2 bg-cyan-500/10 rounded-lg border border-cyan-500/20">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 status-dot" />
          </div>
          <div className="hidden sm:block">
            <h1 className="text-[11px] font-bold tracking-[0.2em] text-slate-200 uppercase leading-none">
              LLM Reliability <span className="gradient-text">Platform</span>
            </h1>
            <p className="text-[9px] text-slate-500 tracking-widest uppercase mt-0.5">Distribution Shaping Pipeline</p>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex items-center gap-1">
          {links.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={`nav-link flex items-center gap-2 ${pathname === href ? "active" : ""}`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          ))}
        </nav>

        {/* Status Strip */}
        <div className="hidden md:flex items-center gap-4 text-[10px] font-mono text-slate-500 uppercase tracking-wider">
          <span className="flex items-center gap-2">
            <Zap className="w-3 h-3 text-cyan-500" />
            v2.4.1
          </span>
          <span className="flex items-center gap-2">
            <div className="status-dot" />
            Online
          </span>
        </div>
      </div>
    </header>
  )
}
