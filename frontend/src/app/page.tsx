"use client"

import { useState, useEffect, useMemo } from "react"

/* ═════════ ICONS (Lucide mapped to Material) ═════════ */
import {
  Box, FileText, Activity, Server, Database,
  Terminal, Shield, Zap,
  Layers, Map, CloudRain, ShieldAlert, AlertTriangle
} from "lucide-react"

/* ═════════ CONFIG TYPES ═════════ */
type InferenceConfig = {
  mode: InferenceMode
  temperature: number
  top_p: number
  top_k: number
  presence_penalty: number
  max_new_tokens: number
}

type InferenceMode = "factual" | "mixed" | "emotional"

type InferenceResult = {
  response_text: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
  escalate: boolean
  confidence: number
  instability: number
}

type ReviewPacket = {
  entropy_samples?: string[]
  embedding_similarity?: number
  ambiguity?: number
}

type InferenceApiResponse = InferenceResult & {
  trace?: Record<string, unknown>
  review_packet?: ReviewPacket
}

type PromptHistoryEntry = {
  prompt: string
  response_text: string
  confidence: number
  instability: number
  timestamp: number
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null
}

function parseInferenceResponse(payload: unknown): InferenceApiResponse {
  if (!isRecord(payload)) {
    throw new Error("Invalid inference response payload.")
  }

  const requiredString = payload.response_text
  if (typeof requiredString !== "string") {
    throw new Error("Missing response_text in inference response.")
  }

  const numberFields: (keyof InferenceResult)[] = [
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "confidence",
    "instability",
  ]
  for (const field of numberFields) {
    if (typeof payload[field] !== "number" || Number.isNaN(payload[field])) {
      throw new Error(`Missing ${field} in inference response.`)
    }
  }

  if (typeof payload.escalate !== "boolean") {
    throw new Error("Missing escalate in inference response.")
  }

  if ("trace" in payload && payload.trace !== undefined && !isRecord(payload.trace)) {
    throw new Error("Invalid trace in inference response.")
  }

  if ("review_packet" in payload && payload.review_packet !== undefined && !isRecord(payload.review_packet)) {
    throw new Error("Invalid review_packet in inference response.")
  }

  return payload as InferenceApiResponse
}

export default function Home() {
  const [isClient, setIsClient] = useState(false)
  const [activeTab, setActiveTab] = useState("Dashboard")
  const [uiMode, setUiMode] = useState<"OPS" | "DIAG">("OPS")

  // Reactor State
  const [prompt, setPrompt] = useState("")
  const [loading, setLoading] = useState(false)
  const [config, setConfig] = useState<InferenceConfig>({
    mode: "factual",
    temperature: 0.75,
    top_p: 0.90,
    top_k: 40,
    presence_penalty: 0.6,
    max_new_tokens: 4096,
  })
  const [result, setResult] = useState<InferenceResult | null>(null)
  const [reviewPacket, setReviewPacket] = useState<ReviewPacket | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [trace, setTrace] = useState<Record<string, unknown> | null>(null)
  const [history, setHistory] = useState<PromptHistoryEntry[]>([])
  const [systemStatus, setSystemStatus] = useState<"Online" | "Offline">("Offline")

  // Dashboard Metrics
  const [metrics, setMetrics] = useState({
    efficiency: "+0.2",
    latencyDelta: "-0.1",
    activeNodes: 1024,
    uptime: "99.99"
  })

  // Network stats (stabilized)
  const [netStats, setNetStats] = useState({ tx: "3.2", rx: "12.4" })

  // Logs
  const [logs, setLogs] = useState<{ tag: string, msg: string, time: string, isJson?: boolean, color?: string }[]>([
    { tag: "[SYSTEM]", msg: "Session initialized.", time: "0.001ms", color: "text-cyan-400" },
    { tag: "[SYSTEM]", msg: "All nodes reporting nominal status.", time: "0.004ms", color: "text-emerald-400" },
    { tag: "[NETWORK]", msg: "Established handshake with KG-01-CORE.", time: "0.012ms", color: "text-amber-400" },
    { tag: "[SYSTEM]", msg: "Synchronizing neural buffers...", time: "", color: "text-cyan-400" }
  ])

  // Stable heatmap values
  const heatmapValues = useMemo(() => Array.from({ length: 25 }, () => [10, 20, 30, 40, 60, 80, 90][Math.floor(Math.random() * 7)]), [])

  useEffect(() => {
    setIsClient(true)

    // Simulate network stats update
    const netInterval = setInterval(() => {
      setNetStats({ tx: (Math.random() * 4 + 2).toFixed(1), rx: (Math.random() * 8 + 10).toFixed(1) })
    }, 3000)

    // System Status Polling
    const checkHealth = async () => {
      try {
        const res = await fetch("/api/health")
        if (res.ok) {
          setSystemStatus("Online")
        } else {
          setSystemStatus("Offline")
        }
      } catch {
        setSystemStatus("Offline")
      }
    }

    checkHealth()
    const healthInterval = setInterval(checkHealth, 10000)

    return () => {
      clearInterval(netInterval)
      clearInterval(healthInterval)
    }
  }, [])

  const runAll = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setErrorMessage(null)
    setReviewPacket(null)

    setLogs(prev => [...prev.slice(-10), { tag: "[USER]", msg: "Dispatching neural sequence...", time: "", color: "text-cyan-200" }])

    const start = performance.now()
    try {
      const allowedConfig = {
        mode: config.mode,
        temperature: config.temperature,
        top_p: config.top_p,
        max_new_tokens: config.max_new_tokens,
      }

      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, ...allowedConfig }),
      })
      if (!res.ok) {
        const payload = await res.json().catch(() => null)
        const message = isRecord(payload) && typeof payload.error === "string"
          ? payload.error
          : `HTTP ${res.status}`
        throw new Error(message)
      }
      const data = parseInferenceResponse(await res.json())

      const realLatency = Math.round(performance.now() - start)
      setResult({
        response_text: data.response_text,
        latency_ms: data.latency_ms,
        input_tokens: data.input_tokens,
        output_tokens: data.output_tokens,
        escalate: data.escalate,
        confidence: data.confidence,
        instability: data.instability,
      })

      setTrace(data.trace ?? null)
      setReviewPacket(data.review_packet ?? null)
      setHistory(prev => [
        {
          prompt,
          response_text: data.response_text,
          confidence: data.confidence,
          instability: data.instability,
          timestamp: Date.now(),
        },
        ...prev,
      ].slice(0, 10))

      setLogs(prev => [...prev.slice(-10), {
        tag: "[COMPUTE]",
        msg: `Sequence executed. Latency: ${data.latency_ms}ms | Instability: ${data.instability.toFixed(2)} (local RTT ${realLatency}ms)`,
        time: "",
        color: data.escalate ? "text-red-400" : "text-emerald-400"
      }])

      // Randomly update dashboard metrics slightly for "live" feel
      setMetrics(prev => ({
        ...prev,
        activeNodes: prev.activeNodes + Math.floor(Math.random() * 5),
        latencyDelta: (Math.random() > 0.5 ? "-" : "+") + (Math.random() * 0.2).toFixed(1)
      }))

    } catch (err) {
      const message = err instanceof Error ? err.message : "Inference server unavailable."
      setErrorMessage(message)
      setLogs(prev => [...prev.slice(-10), {
        tag: "[ERROR]",
        msg: `Sequence failed: ${message}`,
        time: "",
        color: "text-red-500",
      }])
    } finally {
      setLoading(false)
    }
  }

  if (!isClient) return <div className="bg-[#080e10] min-h-screen" />

  return (
    <div className="bg-[#080e10] font-sans text-slate-100 min-h-screen flex overflow-hidden selection:bg-[#0dccf2]/30">

      {/* ── LEFT SIDEBAR (Base Navigation) ── */}
      <aside className="w-20 lg:w-64 border-r border-[#0dccf2]/10 flex flex-col bg-[#101f22]/70 backdrop-blur-xl z-20">
        <div className="p-6 flex items-center gap-3">
          <div className="w-10 h-10 bg-[#0dccf2]/20 rounded-lg flex items-center justify-center border border-[#0dccf2]/40 shadow-[0_0_15px_rgba(13,204,242,0.3)]">
            <Box className="w-5 h-5 text-[#0dccf2]" />
          </div>
          <div className="hidden lg:block">
            <h2 className="text-white text-lg font-bold leading-tight tracking-tight">KG-01</h2>
            <p className="text-[#0dccf2] text-[10px] uppercase tracking-[0.2em] font-bold">Kaggle Core</p>
          </div>
        </div>

        <nav className="flex-1 px-4 space-y-2 py-6">
          {[
            { id: "Dashboard", icon: <Layers className="w-5 h-5" /> },
            { id: "Neural Map", icon: <Map className="w-5 h-5" /> },
            { id: "Logs", icon: <Terminal className="w-5 h-5" /> },
            { id: "Storage", icon: <Database className="w-5 h-5" /> },
            { id: "Security", icon: <Shield className="w-5 h-5" /> },
          ].map(tab => (
            <div
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer transition-colors ${activeTab === tab.id
                ? "bg-[#0dccf2]/10 text-[#0dccf2] border border-[#0dccf2]/20 shadow-[0_0_10px_rgba(13,204,242,0.1)]"
                : "text-slate-400 hover:bg-white/5 border border-transparent"
                }`}
            >
              {tab.icon}
              <p className="hidden lg:block text-sm font-medium">{tab.id}</p>
            </div>
          ))}
        </nav>


      </aside>

      {/* ── MAIN CONTENT AREA ── */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_50%,rgba(13,204,242,0.08)_0%,transparent_60%)] pointer-events-none" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(40,54,57,0.15)_1px,transparent_1px),linear-gradient(90deg,rgba(40,54,57,0.15)_1px,transparent_1px)] bg-[size:40px_40px] pointer-events-none" />

        {/* ── TOP HEADER ── */}
        <header className="h-16 border-b border-[#0dccf2]/10 flex items-center justify-between px-8 bg-[#101f22]/70 backdrop-blur-xl z-20">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div
                className={`w-2 h-2 rounded-full animate-pulse ${
                  systemStatus === "Online"
                    ? "bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]"
                    : "bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.8)]"
                }`}
              />
              <span
                className={`text-xs font-medium tracking-widest uppercase ${
                  systemStatus === "Online" ? "text-emerald-400" : "text-red-400"
                }`}
              >
                System {systemStatus}
              </span>
            </div>
            <div className="h-4 w-px bg-[#0dccf2]/20" />
            <div className="text-xs text-slate-400 font-mono">NODE_UPTIME: 452:12:08:44</div>
          </div>

          <div className="flex items-center gap-6 text-slate-400">
            <div className="flex bg-[#283639]/40 rounded-lg p-1">
              <button onClick={() => setUiMode("OPS")} className={`px-4 py-1 text-xs font-bold rounded transition-colors ${uiMode === "OPS" ? "bg-[#0dccf2] text-[#080e10]" : "hover:text-white"}`}>OPS</button>
              <button onClick={() => setUiMode("DIAG")} className={`px-4 py-1 text-xs font-bold rounded transition-colors ${uiMode === "DIAG" ? "bg-[#0dccf2] text-[#080e10]" : "hover:text-white"}`}>DIAG</button>
            </div>
            <div className="text-sm font-mono text-slate-300 bg-[#283639] px-3 py-1 rounded-lg shadow-inner">
              {new Date().toISOString().substring(11, 19)} UTC
            </div>
          </div>
        </header>

        {/* ── DYNAMIC PAGES ── */}
        <div className="flex-1 overflow-y-auto z-10 p-8">

          {/* ---- DASHBOARD TAB ---- */}
          {activeTab === "Dashboard" && (
            <div className="space-y-6 max-w-7xl mx-auto">

              {/* Top Metric Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {[
                  { title: "Core Status", val: "STABLE", sub: `${metrics.efficiency}% efficiency`, icon: <Server className="w-12 h-12" />, color: "text-[#0dccf2]" },
                  { title: "Neural Health", val: "98.4%", sub: `${metrics.latencyDelta}% latency`, icon: <Activity className="w-12 h-12" />, color: "text-red-400" },
                  { title: "Active Nodes", val: metrics.activeNodes.toLocaleString(), sub: "+12 auto-scaled", icon: <Database className="w-12 h-12" />, color: "text-[#0dccf2]" },
                  { title: "Global Uptime", val: `${metrics.uptime}%`, sub: "Verified SLA", icon: <CloudRain className="w-12 h-12" />, color: "text-[#0dccf2]" },
                ].map((card, i) => (
                  <div key={i} className="bg-[#101f22]/70 backdrop-blur-md p-6 rounded-xl border border-[#0dccf2]/15 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-[#0dccf2]">
                      {card.icon}
                    </div>
                    <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">{card.title}</p>
                    <p className="text-3xl font-bold text-white tracking-tight mt-2">{card.val}</p>
                    <div className={`flex items-center gap-2 mt-2 ${card.color}`}>
                      <span className="text-sm font-medium">{card.sub}</span>
                    </div>
                  </div>
                ))}
              </div>

              {/* ══════ OPS MODE: Reactor Console ══════ */}
              {uiMode === "OPS" && (
                <div className="flex flex-col lg:flex-row gap-6 mt-8">
                  {/* Left: Input Console */}
                  <div className="flex-1 bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 p-6 shadow-[0_0_30px_rgba(13,204,242,0.05)]">
                    <div className="flex justify-between items-center mb-6">
                      <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#0dccf2]/30 bg-[#0dccf2]/5 text-[#0dccf2] text-[10px] font-bold uppercase tracking-widest">
                        Reactor Core Active
                      </div>
                      <h2 className="text-xl font-bold text-white tracking-tight">Initialize Synthesis</h2>
                    </div>

                    <div className="relative group">
                      <div className="absolute -inset-1 bg-gradient-to-r from-[#0dccf2]/20 via-[#0dccf2]/40 to-[#0dccf2]/20 rounded-2xl blur-lg opacity-20 group-focus-within:opacity-40 transition-opacity"></div>
                      <div className="relative bg-[#162224] border border-[#283639] rounded-2xl p-6 shadow-2xl focus-within:shadow-[0_0_40px_rgba(13,204,242,0.1)] focus-within:border-[#0dccf2]/50 transition-all">
                        <textarea
                          value={prompt}
                          onChange={(e) => setPrompt(e.target.value)}
                          className="w-full bg-transparent border-none focus:ring-0 text-lg font-light text-slate-200 placeholder-slate-600 resize-none min-h-[160px] outline-none"
                          placeholder="Type neural prompt here..."
                          disabled={loading}
                        ></textarea>

                        <div className="flex items-center justify-end mt-4 pt-4 border-t border-[#283639]/50">
                          <button
                            onClick={runAll}
                            disabled={loading || !prompt.trim()}
                            className="flex items-center gap-2 px-8 py-3 rounded-xl bg-[#0dccf2] text-[#0a0f10] font-bold text-sm hover:brightness-110 shadow-[0_0_20px_rgba(13,204,242,0.3)] active:scale-95 transition-all disabled:opacity-50 disabled:animate-none"
                          >
                            <span>{loading ? "PROCESSING..." : "EXECUTE"}</span>
                            <Zap className={`w-4 h-4 ${loading ? "animate-pulse" : ""}`} />
                          </button>
                        </div>
                      </div>
                    </div>

                    {/* Result or Telemetry */}
                    <div className="mt-6">
                      {result ? (
                        <div className="space-y-3">
                          <div className={`p-4 rounded-xl border bg-black/40 font-mono text-sm leading-relaxed ${result.escalate ? "border-red-500/30 text-red-200" : "border-[#0dccf2]/30 text-[#0dccf2]"}`}>
                            <p className="opacity-50 mb-2 uppercase text-[10px] tracking-widest">{result.escalate ? "⚠ ESCALATION PROTOCOL ACTIVATED" : "▸ SYNTHESIS COMPLETE"}</p>
                            {result.response_text}
                          </div>
                          {result.escalate && reviewPacket && (
                            <div className="p-3 rounded-xl border border-red-500/30 bg-red-500/10 font-mono text-xs text-red-200 space-y-1">
                              <p className="uppercase tracking-widest text-[10px] opacity-70">Uncertainty Diagnostics</p>
                              <p>Embedding Similarity: {typeof reviewPacket.embedding_similarity === "number" ? reviewPacket.embedding_similarity.toFixed(3) : "n/a"}</p>
                              <p>Ambiguity: {typeof reviewPacket.ambiguity === "number" ? reviewPacket.ambiguity.toFixed(3) : "n/a"}</p>
                              <p>Entropy Samples: {reviewPacket.entropy_samples?.length ?? 0}</p>
                            </div>
                          )}
                        </div>
                      ) : (
                        <div className="grid grid-cols-3 gap-4">
                          <div className="p-4 rounded-xl border border-[#283639] bg-white/5 flex flex-col gap-1">
                            <span className="text-[10px] font-bold text-[#0dccf2] uppercase">Latency</span>
                            <span className="text-xl font-mono">-- ms</span>
                          </div>
                          <div className="p-4 rounded-xl border border-[#283639] bg-white/5 flex flex-col gap-1">
                            <span className="text-[10px] font-bold text-[#0dccf2] uppercase">Input Tokens</span>
                            <span className="text-xl font-mono">--</span>
                          </div>
                          <div className="p-4 rounded-xl border border-[#283639] bg-white/5 flex flex-col gap-1">
                            <span className="text-[10px] font-bold text-[#0dccf2] uppercase">Output Tokens</span>
                            <span className="text-xl font-mono">--</span>
                          </div>
                        </div>
                      )}
                      {errorMessage && (
                        <div className="mt-3 p-3 rounded-xl border border-red-500/30 bg-red-500/10 text-red-200 text-xs font-medium">
                          {errorMessage}
                        </div>
                      )}
                      {history.length > 0 && (
                        <div className="mt-3 p-3 rounded-xl border border-[#0dccf2]/20 bg-[#0dccf2]/5 space-y-2">
                          <p className="text-[10px] uppercase tracking-widest font-bold text-[#0dccf2]">Recent Runs</p>
                          {history.slice(0, 3).map((entry) => (
                            <div key={entry.timestamp} className="text-xs font-mono text-slate-300">
                              <p className="truncate text-slate-200">{entry.prompt}</p>
                              <p className="text-slate-500">
                                C {(entry.confidence * 100).toFixed(1)}% · I {entry.instability.toFixed(3)}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right: Output Feed & Parameters */}
                  <div className="w-full lg:w-96 flex flex-col gap-6">
                    {/* Output Feed console */}
                    <div className="flex-1 bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 flex flex-col overflow-hidden min-h-[250px]">
                      <div className="p-4 border-b border-[#0dccf2]/10 bg-[#162224]/50 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Terminal className="w-4 h-4 text-[#0dccf2]" />
                          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">Output Feed</h3>
                        </div>
                        <div className="flex gap-1">
                          <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                          <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                          <div className="w-2 h-2 rounded-full bg-slate-700"></div>
                        </div>
                      </div>
                      <div className="flex-1 p-6 font-mono text-xs overflow-y-auto space-y-3">
                        {logs.map((log, i) => (
                          <div key={i} className={log.color || "text-slate-400"}>
                            <span className="opacity-50">{log.tag}</span> {log.msg} <span className="text-slate-600 ml-1">{log.time}</span>
                          </div>
                        ))}
                        {loading && (
                          <div className="flex items-center gap-3 py-4 mt-4 border-t border-[#283639]/30">
                            <div className="w-4 h-4 rounded-full border-2 border-[#0dccf2] border-t-transparent animate-spin"></div>
                            <span className="text-[#0dccf2] animate-pulse uppercase tracking-widest text-[10px] font-bold">Awaiting Execution...</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Parameters Overview */}
                    <div className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 p-6">
                      <h3 className="text-white text-sm font-bold uppercase tracking-widest mb-6">Execution Parameters</h3>

                      <div className="space-y-5">
                        <div className="space-y-3">
                          <label className="text-xs font-medium text-slate-300">Mode</label>
                          <select
                            value={config.mode}
                            onChange={(e) => setConfig({ ...config, mode: e.target.value as InferenceMode })}
                            className="w-full bg-[#162224] border border-[#283639] rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-[#0dccf2]/50"
                          >
                            <option value="factual">factual</option>
                            <option value="mixed">mixed</option>
                            <option value="emotional">emotional</option>
                          </select>
                        </div>
                        {[
                          { label: "Temperature", val: config.temperature, key: "temperature", min: 0, max: 2, step: 0.1 },
                          { label: "Top P", val: config.top_p, key: "top_p", min: 0, max: 1, step: 0.05 },
                          { label: "Top K", val: config.top_k, key: "top_k", min: 1, max: 100, step: 1 },
                          { label: "Max Tokens", val: config.max_new_tokens, key: "max_new_tokens", min: 64, max: 8192, step: 64 }
                        ].map(c => (
                          <div key={c.label} className="space-y-3 mt-4">
                            <div className="flex justify-between items-end">
                              <label className="text-xs font-medium text-slate-300">{c.label}</label>
                              <span className="text-xs font-mono text-[#0dccf2]">{c.val}</span>
                            </div>
                            <div className="relative h-1.5 w-full bg-[#283639] rounded-full">
                              <div className="absolute top-0 left-0 h-full bg-[#0dccf2] rounded-full shadow-[0_0_10px_rgba(13,204,242,0.5)]"
                                style={{ width: `${((Number(c.val) - c.min) / (c.max - c.min)) * 100}%` }}></div>
                              <input
                                type="range"
                                min={c.min}
                                max={c.max}
                                step={c.step}
                                value={c.val}
                                onChange={e => setConfig({ ...config, [c.key]: Number(e.target.value) })}
                                className="absolute inset-0 w-full opacity-0 cursor-pointer"
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* ══════ DIAG MODE: Advanced Diagnostic Grid ══════ */}
              {uiMode === "DIAG" && (
                <div className="space-y-8 mt-8">
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Latency Tracking Chart */}
                    <div className="lg:col-span-2 bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 p-6">
                      <div className="flex items-center justify-between mb-8">
                        <div>
                          <h3 className="text-white text-lg font-bold">Latency Tracking</h3>
                          <p className="text-slate-400 text-xs mt-1">Real-time inference response times (ms)</p>
                        </div>

                      </div>
                      {/* Simulated Bars */}
                      <div className="h-64 flex items-end gap-1 mb-4">
                        {[12, 45, 55, 40, 80, 35, 50, 20, 45, 65, 30, 40, 75, 50, 45, 35].map((h, i) => (
                          <div key={i} className="flex-1 bg-[#0dccf2]/20 rounded-t border-t border-[#0dccf2]/40 group relative" style={{ height: `${h}%` }}>
                            {i === 4 && <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-[#080e10] border border-[#0dccf2] text-[#0dccf2] text-[10px] px-2 py-1 rounded hidden group-hover:block z-10">{h * 2}ms</div>}
                          </div>
                        ))}
                      </div>
                      <div className="flex justify-between text-[10px] text-slate-500 uppercase tracking-widest font-bold">
                        <span>00:00:00</span>
                        <span>00:15:00</span>
                        <span>00:30:00</span>
                        <span>00:45:00</span>
                        <span>01:00:00</span>
                      </div>
                    </div>

                    {/* Neural Symmetry Circular Health */}
                    <div className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 p-6 flex flex-col items-center justify-center text-center">
                      <h3 className="text-white text-lg font-bold mb-6">Neural Symmetry</h3>
                      <div className="relative w-48 h-48 flex items-center justify-center mb-6">
                        <svg className="w-full h-full -rotate-90">
                          <circle className="text-[#0dccf2]/10" cx="96" cy="96" fill="transparent" r="88" stroke="currentColor" strokeWidth="8"></circle>
                          <circle className="text-[#0dccf2] drop-shadow-[0_0_15px_rgba(13,204,242,0.3)] transition-all duration-1000" cx="96" cy="96" fill="transparent" r="88" stroke="currentColor" strokeDasharray="552.92" strokeDashoffset={552.92 - (552.92 * 0.85)} strokeLinecap="round" strokeWidth="8"></circle>
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                          <span className="text-4xl font-bold text-white">85%</span>
                          <span className="text-[10px] text-[#0dccf2] uppercase font-bold tracking-widest mt-1">Optimal Sync</span>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 w-full gap-4">
                        <div className="p-3 bg-white/5 rounded-lg border border-[#0dccf2]/10">
                          <p className="text-slate-400 text-[10px] uppercase font-bold">Synapse Load</p>
                          <p className="text-white font-bold mt-1">0.821</p>
                        </div>
                        <div className="p-3 bg-white/5 rounded-lg border border-[#0dccf2]/10">
                          <p className="text-slate-400 text-[10px] uppercase font-bold">Weight Flux</p>
                          <p className="text-white font-bold mt-1">±0.04</p>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Bottom Functional Panels */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
                    {/* Regression Report Terminal */}
                    <div className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 overflow-hidden">
                      <div className="bg-[#0dccf2]/10 px-4 py-3 border-b border-[#0dccf2]/20 flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-[#0dccf2]" />
                          <span className="text-xs font-bold text-white uppercase tracking-widest">Regression Report // KG-01</span>
                        </div>
                        <div className="flex gap-1.5">
                          <div className="w-2 h-2 rounded-full bg-red-500/50"></div>
                          <div className="w-2 h-2 rounded-full bg-yellow-500/50"></div>
                          <div className="w-2 h-2 rounded-full bg-green-500/50"></div>
                        </div>
                      </div>
                      <div className="p-6 font-mono text-xs leading-relaxed overflow-x-auto space-y-1">
                        <div className="text-[#0dccf2]/70">[14:22:01] <span className="text-white">INIT_CORE_DIAGNOSTICS</span>... OK</div>
                        <div className="text-slate-500">[14:22:03] CHECKING_REGRESSION_MODEL_V2.0...</div>
                        <div className="text-slate-300 ml-4">&gt; MSE: 0.0024</div>
                        <div className="text-slate-300 ml-4">&gt; MAE: 0.0019</div>
                        <div className="text-slate-300 ml-4">&gt; R-SQUARED: 0.9982</div>
                        <div className="text-yellow-400 mt-2">[14:22:10] WARN: NODE_72_LATENCY_SPIKE detected (24ms)</div>
                        <div className="text-[#0dccf2]/70 mt-2">[14:22:15] <span className="text-white">AUTO_OPTIMIZING_NODE_WEIGHTS</span>...</div>
                        <div className="text-green-400">[14:22:18] SUCCESS: OPTIMIZATION_COMPLETE in 3.2s</div>
                        <div className="text-slate-500 mt-2">[14:22:20] BROADCASTING_METRICS_TO_HIVE...</div>
                        <div className="flex items-center gap-1 mt-4">
                          <span className="text-[#0dccf2]">root@kg-01:~$</span>
                          <span className="w-1.5 h-4 bg-[#0dccf2] animate-pulse inline-block"></span>
                        </div>
                      </div>
                    </div>

                    {/* Resource Allocation Grid */}
                    <div className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 p-6">
                      <h3 className="text-white text-lg font-bold mb-6">Resource Allocation</h3>
                      <div className="space-y-6">
                        <div className="space-y-2">
                          <div className="flex justify-between text-xs font-bold uppercase tracking-widest">
                            <span className="text-slate-400">Compute Threads (X86_64)</span>
                            <span className="text-white">724 / 1024</span>
                          </div>
                          <div className="h-2 w-full bg-[#0dccf2]/10 rounded-full overflow-hidden border border-[#0dccf2]/20">
                            <div className="h-full bg-[#0dccf2] shadow-[0_0_10px_rgba(13,204,242,0.5)] rounded-full transition-all duration-1000" style={{ width: "70%" }}></div>
                          </div>
                        </div>
                        <div className="space-y-2 mt-4">
                          <div className="flex justify-between text-xs font-bold uppercase tracking-widest">
                            <span className="text-slate-400">Memory (HBM3)</span>
                            <span className="text-white">42.8GB / 64GB</span>
                          </div>
                          <div className="h-2 w-full bg-[#0dccf2]/10 rounded-full overflow-hidden border border-[#0dccf2]/20">
                            <div className="h-full bg-[#0dccf2] shadow-[0_0_10px_rgba(13,204,242,0.5)] rounded-full transition-all duration-1000" style={{ width: "66%" }}></div>
                          </div>
                        </div>
                        <div className="space-y-2 mt-4">
                          <div className="flex justify-between text-xs font-bold uppercase tracking-widest">
                            <span className="text-slate-400">Quantum Interlink</span>
                            <span className="text-white">1.2 TBps / 2.0 TBps</span>
                          </div>
                          <div className="h-2 w-full bg-[#0dccf2]/10 rounded-full overflow-hidden border border-[#0dccf2]/20">
                            <div className="h-full bg-[#0dccf2] shadow-[0_0_10px_rgba(13,204,242,0.5)] rounded-full transition-all duration-1000" style={{ width: "60%" }}></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* ---- NEURAL MAP TAB ---- */}
          {activeTab === "Neural Map" && (
            <div className="max-w-4xl mx-auto space-y-6">
              <h2 className="text-xl font-bold text-white tracking-tight">Neural Map — Last Inference Telemetry</h2>
              {result ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[
                    { label: "Latency", value: `${result.latency_ms} ms`, color: "text-[#0dccf2]" },
                    { label: "Input Tokens", value: result.input_tokens.toLocaleString(), color: "text-[#0dccf2]" },
                    { label: "Output Tokens", value: result.output_tokens.toLocaleString(), color: "text-[#0dccf2]" },
                    { label: "Confidence", value: `${(result.confidence * 100).toFixed(1)}%`, color: result.confidence > 0.7 ? "text-emerald-400" : "text-amber-400" },
                    { label: "Instability", value: result.instability.toFixed(4), color: result.escalate ? "text-red-400" : "text-emerald-400" },
                    { label: "Escalation", value: result.escalate ? "TRIGGERED" : "NONE", color: result.escalate ? "text-red-400" : "text-emerald-400" },
                  ].map((m) => (
                    <div key={m.label} className="bg-[#101f22]/70 backdrop-blur-md p-6 rounded-xl border border-[#0dccf2]/15">
                      <p className="text-slate-400 text-xs font-bold uppercase tracking-widest">{m.label}</p>
                      <p className={`text-2xl font-bold mt-2 ${m.color}`}>{m.value}</p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                  <Map className="w-16 h-16 opacity-20 mb-4" />
                  <p className="uppercase tracking-widest font-bold text-sm">Run an inference to populate telemetry</p>
                </div>
              )}
            </div>
          )}

          {/* ---- LOGS TAB ---- */}
          {activeTab === "Logs" && (
            <div className="max-w-4xl mx-auto space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold text-white tracking-tight">Session Logs</h2>
                <button
                  onClick={() => setLogs([])}
                  className="px-4 py-2 text-xs font-bold uppercase tracking-widest rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-colors"
                >Clear Logs</button>
              </div>
              <div className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 overflow-hidden">
                <div className="p-4 border-b border-[#0dccf2]/10 bg-[#162224]/50 flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-[#0dccf2]" />
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-200">System Output — {logs.length} entries</span>
                </div>
                <div className="p-6 font-mono text-xs space-y-2 max-h-[60vh] overflow-y-auto">
                  {logs.length === 0 ? (
                    <p className="text-slate-500 italic">No log entries recorded.</p>
                  ) : (
                    logs.map((log, i) => (
                      <div key={i} className={log.color || "text-slate-400"}>
                        <span className="opacity-50">{log.tag}</span> {log.msg} <span className="text-slate-600 ml-1">{log.time}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ---- STORAGE TAB ---- */}
          {activeTab === "Storage" && (
            <div className="max-w-4xl mx-auto space-y-4">
              <h2 className="text-xl font-bold text-white tracking-tight">Storage — Stability Snapshots</h2>
              {(() => {
                let snapshots: { timestamp: string; results: { name: string; latency_ms: number; output_tokens: number }[] }[] = []
                try {
                  const raw = localStorage.getItem("stability_snapshots")
                  if (raw) snapshots = JSON.parse(raw)
                } catch { }
                if (snapshots.length === 0) return (
                  <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                    <Database className="w-16 h-16 opacity-20 mb-4" />
                    <p className="uppercase tracking-widest font-bold text-sm">No stability snapshots stored</p>
                    <p className="text-xs text-slate-600 mt-2">Run the stability suite to generate snapshots</p>
                  </div>
                )
                return (
                  <div className="space-y-4">
                    {snapshots.map((snap, idx) => (
                      <div key={snap.timestamp} className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 p-6">
                        <div className="flex justify-between items-center mb-4">
                          <h3 className="text-sm font-bold text-white">Snapshot {idx + 1}</h3>
                          <span className="text-[10px] text-slate-500 font-mono">{new Date(snap.timestamp).toLocaleString()}</span>
                        </div>
                        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                          {snap.results.map((r) => (
                            <div key={r.name} className="p-3 bg-white/5 rounded-lg border border-[#0dccf2]/10">
                              <p className="text-[10px] text-slate-400 uppercase font-bold truncate">{r.name}</p>
                              <p className="text-sm text-[#0dccf2] font-bold mt-1">{r.latency_ms}ms · {r.output_tokens} tok</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )
              })()}
            </div>
          )}

          {/* ---- SECURITY TAB ---- */}
          {activeTab === "Security" && (
            <div className="max-w-4xl mx-auto space-y-4">
              <h2 className="text-xl font-bold text-white tracking-tight">Security — Guardrail & Trace Analysis</h2>
              {trace ? (
                <div className="space-y-6">
                  {Object.entries(trace).map(([section, data]) => (
                    <div key={section} className="bg-[#101f22]/70 backdrop-blur-md rounded-xl border border-[#0dccf2]/15 overflow-hidden">
                      <div className="px-4 py-3 bg-[#0dccf2]/10 border-b border-[#0dccf2]/20 flex items-center gap-2">
                        <Shield className="w-4 h-4 text-[#0dccf2]" />
                        <span className="text-xs font-bold text-white uppercase tracking-widest">{section}</span>
                      </div>
                      <div className="p-6 font-mono text-xs space-y-1">
                        {typeof data === "object" && data !== null ? (
                          Object.entries(data as Record<string, unknown>).map(([k, v]) => (
                            <div key={k} className="flex gap-4">
                              <span className="text-slate-500 min-w-[180px]">{k}:</span>
                              <span className="text-[#0dccf2]">{typeof v === "object" ? JSON.stringify(v) : String(v)}</span>
                            </div>
                          ))
                        ) : (
                          <span className="text-[#0dccf2]">{String(data)}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 text-slate-500">
                  <ShieldAlert className="w-16 h-16 opacity-20 mb-4" />
                  <p className="uppercase tracking-widest font-bold text-sm">Run an inference to view security trace</p>
                  <p className="text-xs text-slate-600 mt-2">Guardrail classifications and trace data appear here</p>
                </div>
              )}
            </div>
          )}

        </div>
      </main>

      {/* ── RIGHT SYSTEM PANEL (Live Activity - Desktop Only) ── */}
      <aside className="hidden xl:flex w-72 border-l border-[#0dccf2]/10 flex-col bg-[#101f22]/70 backdrop-blur-xl z-20">
        <div className="p-6 border-b border-[#0dccf2]/10">
          <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4">Live Activity</h3>
          <div className="space-y-4">
            <div className="flex gap-3">
              <div className="w-2 h-2 bg-emerald-500 rounded-full mt-1.5 shadow-[0_0_5px_rgba(16,185,129,0.5)]"></div>
              <div className="flex-1">
                <p className="text-xs text-white font-medium">Model Deployment</p>
                <p className="text-[10px] text-slate-500">v2.0.4 stable on Node-A12</p>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">2m ago</span>
            </div>
            <div className="flex gap-3">
              <div className="w-2 h-2 bg-[#0dccf2] rounded-full mt-1.5 shadow-[0_0_5px_rgba(13,204,242,0.5)]"></div>
              <div className="flex-1">
                <p className="text-xs text-white font-medium">Auto-Scaling Triggered</p>
                <p className="text-[10px] text-slate-500">Requested 12 additional nodes</p>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">15m ago</span>
            </div>
            <div className="flex gap-3">
              <div className="w-2 h-2 bg-amber-500 rounded-full mt-1.5 shadow-[0_0_5px_rgba(245,158,11,0.5)]"></div>
              <div className="flex-1">
                <p className="text-xs text-white font-medium">Backup Initiated</p>
                <p className="text-[10px] text-slate-500">Regional snapshot - EU_WEST_1</p>
              </div>
              <span className="text-[10px] text-slate-500 font-mono">1h ago</span>
            </div>
            {result && (
              <div className="flex gap-3">
                <div className="w-2 h-2 bg-purple-500 rounded-full mt-1.5 shadow-[0_0_5px_#a855f7]"></div>
                <div className="flex-1">
                  <p className="text-xs text-white font-medium">Synthesis Executed</p>
                  <p className="text-[10px] text-slate-500">User prompt dispatched</p>
                </div>
                <span className="text-[10px] text-slate-500 font-mono">Just now</span>
              </div>
            )}
            {result?.escalate && (
              <div className="flex gap-3 mt-2 bg-red-500/10 p-2 rounded border border-red-500/20">
                <AlertTriangle className="w-3 h-3 text-red-500 mt-1" />
                <div className="flex-1">
                  <p className="text-xs text-red-400 font-bold uppercase">Escalation</p>
                  <p className="text-[10px] text-slate-400">Instability metric breached thresholds: {result!.instability.toFixed(2)}</p>
                  {reviewPacket && (
                    <p className="text-[10px] text-slate-500 mt-1">
                      Similarity {typeof reviewPacket.embedding_similarity === "number" ? reviewPacket.embedding_similarity.toFixed(3) : "n/a"}
                      {" · "}
                      Ambiguity {typeof reviewPacket.ambiguity === "number" ? reviewPacket.ambiguity.toFixed(3) : "n/a"}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-6 flex-1 flex flex-col pt-8">
          {/* Abstract Heatmap block replacing map from html */}
          <h3 className="text-white font-bold text-sm uppercase tracking-widest mb-4">Node Distribution</h3>
          <div className="bg-[#0dccf2]/5 border border-[#0dccf2]/20 rounded-xl p-4 aspect-square flex flex-col items-center justify-center relative shadow-inner">
            <div className="grid grid-cols-5 grid-rows-5 gap-2 w-full h-full opacity-70">
              {heatmapValues.map((rand, i) => {
                const isHot = rand > 60
                return (
                  <div key={i} className={`rounded-sm border ${isHot ? 'border-[#0dccf2] shadow-[0_0_10px_rgba(13,204,242,0.8)]' : 'border-[#0dccf2]/30'}`} style={{ backgroundColor: `rgba(13, 204, 242, ${rand / 100})` }}></div>
                )
              })}
            </div>
            <div className="absolute bg-[#080e10]/90 px-2 py-1 border border-[#0dccf2]/40 rounded text-[9px] text-white font-mono pointer-events-none tracking-widest">
              GLOBAL_MAP_V2
            </div>
          </div>
          <div className="mt-4 flex justify-between text-[10px] text-slate-500 font-bold uppercase">
            <span>Low density</span>
            <span>Critical Load</span>
          </div>


        </div>
      </aside>

      {/* ── BOTTOM STATUS BAR ── */}
      <footer className="fixed bottom-0 left-0 right-0 h-10 border-t border-[#283639] bg-[#101f22]/90 backdrop-blur-xl z-50 flex items-center justify-between px-6 text-[10px] font-medium text-slate-400">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                systemStatus === "Online"
                  ? "bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]"
                  : "bg-red-500 shadow-[0_0_5px_rgba(239,68,68,0.5)]"
              }`}
            />
            <span className="text-slate-300">BACKEND:</span>
            <span className={`font-bold tracking-widest ${systemStatus === "Online" ? "text-emerald-400" : "text-red-400"}`}>
              {systemStatus.toUpperCase()}
            </span>
          </div>
          <div className="h-3 w-[1px] bg-[#283639]"></div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_5px_rgba(16,185,129,0.5)]"></span>
            <span className="text-slate-300">STABILITY:</span> <span className="text-emerald-500 font-bold tracking-widest">{((1 - (result?.instability || 0)) * 100).toFixed(1)}%</span>
          </div>
          <div className="h-3 w-[1px] bg-[#283639]"></div>
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
            <span className="text-slate-300">TEMP:</span> <span className="text-amber-500 font-bold tracking-widest">42.4°C</span>
          </div>
        </div>

        <div className="flex items-center gap-8">
          <div className="flex gap-6 font-mono">
            <div className="flex gap-2"><span className="text-slate-500 italic">TX:</span> <span className="text-slate-200">{netStats.tx} MB/s</span></div>
            <div className="flex gap-2"><span className="text-slate-500 italic">RX:</span> <span className="text-slate-200">{netStats.rx} MB/s</span></div>
          </div>
          <div className="flex items-center gap-2 bg-[#0dccf2]/10 text-[#0dccf2] px-3 py-1 rounded border border-[#0dccf2]/20">
            <Shield className="w-3 h-3" />
            <span className="font-bold tracking-widest">ENCRYPTION: AES-256-GCM</span>
          </div>
        </div>
      </footer>
    </div>
  )
}
