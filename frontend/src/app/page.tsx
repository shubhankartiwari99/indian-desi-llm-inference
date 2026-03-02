"use client"

import { useState, useEffect, useMemo } from "react"
import { Switch } from "@/components/ui/switch"
import ReactMarkdown from "react-markdown"

type InferenceConfig = {
  temperature: number
  top_p: number
  max_new_tokens: number
  do_sample: boolean
}

type InferenceResult = {
  response_text: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
}

import {
  containsHindi,
  containsEnglishLetters,
  containsPositiveTone,
  containsHindiEmpathy,
  containsSlang
} from "@/lib/assertions"

const TEST_SUITE = [
  {
    id: "uplifting",
    name: "Uplifting English",
    prompt: "Tell me something uplifting.",
    assertions: [
      (o: string) => containsEnglishLetters(o),
      (o: string) => !containsHindi(o),
      (o: string) => containsPositiveTone(o),
    ]
  },
  {
    id: "hindi_emo",
    name: "Hindi Emotional",
    prompt: "मुझे बहुत निराशा महसूस हो रही है।",
    assertions: [
      (o: string) => containsHindi(o),
      (o: string) => containsHindiEmpathy(o),
    ]
  },
  {
    id: "mixed",
    name: "Mixed Mode",
    prompt: "I feel stuck yaar.",
    assertions: [
      (o: string) => containsEnglishLetters(o),
      (o: string) => containsHindi(o) || containsSlang(o),
    ]
  },
  {
    id: "factual",
    name: "Factual English",
    prompt: "What are the long-term benefits of daily exercise?",
    assertions: [
      (o: string) => !containsHindi(o),
      (o: string) => !containsSlang(o),
      (o: string) => o.length > 300,
    ]
  }
]

const FIXED_CONFIG = {
  temperature: 0,
  top_p: 1,
  max_new_tokens: 512,
  do_sample: false
}

type TestResult = {
  id: string
  name: string
  latency_ms: number
  input_tokens: number
  output_tokens: number
  output_length: number
  response_text: string
  assertions?: boolean[]
  assertionPass?: boolean
}

type Snapshot = {
  timestamp: string
  results: TestResult[]
}

function RegressionBlock({ res }: { res: TestResult }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="bg-black/40 border border-indigo-500/20 rounded-md p-5 space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-indigo-500/10 mb-2">
        <span className="text-[10px] text-indigo-400 uppercase tracking-widest">{res.name}</span>
        <div className="flex gap-4 text-[9px] uppercase tracking-widest text-gray-500">
          <span>{res.latency_ms}ms</span>
          <span>{res.output_tokens} tok</span>
        </div>
      </div>
      {res.assertionPass !== undefined && (
        <div className={`text-[10px] uppercase font-semibold tracking-widest mb-3 ${res.assertionPass ? "text-green-400" : "text-red-400"}`}>
          {res.assertionPass ? "ASSERTIONS: PASS" : "ASSERTIONS: FAIL"}
        </div>
      )}
      <div className="flex justify-between items-center text-xs text-gray-400 font-mono">
        <span>{res.output_length} chars generated</span>
        <button
          className="text-indigo-400/80 hover:text-indigo-300 transition-colors uppercase tracking-widest text-[9px]"
          onClick={() => setOpen(!open)}
        >
          {open ? "- Hide Raw Output" : "+ View Raw Output"}
        </button>
      </div>
      {open && (
        <div className="mt-4 pt-4 border-t border-indigo-500/10 text-xs text-gray-400 whitespace-pre-wrap leading-relaxed font-light">
          {res.response_text}
        </div>
      )}
    </div>
  )
}

function ConfigControls({ config, setConfig, disabled, label, colorClass, borderClass }: { config: InferenceConfig, setConfig: (c: InferenceConfig) => void, disabled: boolean, label: string, colorClass: string, borderClass: string }) {
  return (
    <div className={`space-y-6 ${label.includes("B") ? `pt-6 border-t ${borderClass} transition-all` : ""}`}>
      <div className={`text-[10px] uppercase tracking-widest ${colorClass}/80 mb-4 border-b ${borderClass}/10 pb-2`}>
        {label}
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center text-[10px] uppercase tracking-wider text-gray-400">
          <span>Temperature</span>
          <span className={`${colorClass} font-mono`}>{config.temperature}</span>
        </div>
        <input
          type="range" min="0" max="2" step="0.1"
          value={config.temperature}
          onChange={(e) => setConfig({ ...config, temperature: parseFloat(e.target.value) })}
          disabled={disabled}
          className={`w-full ${label.includes("A") ? "accent-indigo-500" : "accent-purple-500"} disabled:opacity-30 disabled:cursor-not-allowed transition-opacity`}
        />
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center text-[10px] uppercase tracking-wider text-gray-400">
          <span>Top P</span>
          <span className={`${colorClass} font-mono`}>{config.top_p}</span>
        </div>
        <input
          type="range" min="0" max="1" step="0.05"
          value={config.top_p}
          onChange={(e) => setConfig({ ...config, top_p: parseFloat(e.target.value) })}
          disabled={disabled}
          className={`w-full ${label.includes("A") ? "accent-indigo-500" : "accent-purple-500"} disabled:opacity-30 disabled:cursor-not-allowed transition-opacity`}
        />
      </div>

      <div className="space-y-3">
        <div className="flex justify-between items-center text-[10px] uppercase tracking-wider text-gray-400">
          <span>Max Tokens</span>
          <span className={`${colorClass} font-mono`}>{config.max_new_tokens}</span>
        </div>
        <input
          type="range" min="64" max="2048" step="64"
          value={config.max_new_tokens}
          onChange={(e) => setConfig({ ...config, max_new_tokens: parseInt(e.target.value) })}
          disabled={disabled}
          className={`w-full ${label.includes("A") ? "accent-indigo-500" : "accent-purple-500"} disabled:opacity-30 disabled:cursor-not-allowed transition-opacity`}
        />
      </div>
    </div>
  )
}

export default function Home() {
  const [isClient, setIsClient] = useState(false)
  const [prompt, setPrompt] = useState("")
  const [compareMode, setCompareMode] = useState(false)
  const [appMode, setAppMode] = useState<"experiment" | "stability">("experiment")

  const [configA, setConfigA] = useState<InferenceConfig>({ temperature: 0.7, top_p: 0.9, max_new_tokens: 256, do_sample: true })
  const [configB, setConfigB] = useState<InferenceConfig>({ temperature: 0.2, top_p: 1.0, max_new_tokens: 256, do_sample: false })

  const [resultA, setResultA] = useState<InferenceResult | null>(null)
  const [resultB, setResultB] = useState<InferenceResult | null>(null)

  const [driftFlag, setDriftFlag] = useState<"stable" | "warning" | "critical">("stable")

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [showHistory, setShowHistory] = useState(false)

  const stabilityDriftFlag = useMemo(() => {
    if (snapshots.length < 2) {
      if (snapshots.length === 1 && snapshots[0].results.some(r => r.assertionPass === false)) return "critical"
      return "stable"
    }
    const latest = snapshots[snapshots.length - 1]
    const previous = snapshots[snapshots.length - 2]

    let flag: "stable" | "warning" | "critical" = "stable"
    for (let i = 0; i < latest.results.length; i++) {
      const curr = latest.results[i]

      if (curr.assertionPass === false) {
        return "critical"
      }

      const prev = previous.results[i]
      if (!prev) continue

      const tokenDelta = Math.abs(curr.output_tokens - prev.output_tokens)
      const lengthDelta = Math.abs(curr.output_length - prev.output_length)

      if (tokenDelta > 100 || lengthDelta > 500) {
        return "critical"
      }
      if (tokenDelta > 40) {
        flag = "warning"
      }
    }
    return flag
  }, [snapshots])

  useEffect(() => {
    setIsClient(true)
    const saved = localStorage.getItem("lastResearchState")
    const savedSnapshots = localStorage.getItem("stability_snapshots")
    if (saved) {
      try {
        const s = JSON.parse(saved)
        if (s.prompt !== undefined) setPrompt(s.prompt)
        if (s.compareMode !== undefined) setCompareMode(s.compareMode)
        if (s.configA) setConfigA(s.configA)
        if (s.configB) setConfigB(s.configB)
      } catch (e) {
        console.error("Failed to parse local storage", e)
      }
    }
    if (savedSnapshots) {
      try {
        setSnapshots(JSON.parse(savedSnapshots))
      } catch (e) {
        console.error("Failed to parse local snapshots", e)
      }
    }
  }, [])

  useEffect(() => {
    if (isClient) {
      localStorage.setItem("lastResearchState", JSON.stringify({
        prompt, compareMode, configA, configB, appMode
      }))
    }
  }, [prompt, compareMode, configA, configB, appMode, isClient])

  const fetchInference = async (config: InferenceConfig): Promise<InferenceResult> => {
    try {
      const start = performance.now()
      const res = await fetch("https://michal-unboarded-erna.ngrok-free.dev/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          temperature: config.temperature,
          top_p: config.top_p,
          max_new_tokens: config.max_new_tokens,
          do_sample: config.do_sample
        }),
      })

      if (!res.ok) throw new Error(`Backend error ${res.status}`)

      const data = await res.json()
      return {
        ...data,
        latency_ms: data.latency_ms ?? Math.round(performance.now() - start)
      } as InferenceResult
    } catch (err) {
      console.error(err)
      throw err
    }
  }

  const runAll = async () => {
    if (!prompt.trim()) return
    setLoading(true)
    setError(null)

    try {
      if (compareMode) {
        const [resA, resB] = await Promise.all([
          fetchInference(configA),
          fetchInference(configB)
        ])

        setResultA(resA)
        setResultB(resB)

        const latencyDelta = Math.abs(resA.latency_ms - resB.latency_ms)
        const tokenDelta = Math.abs(resA.output_tokens - resB.output_tokens)

        if (tokenDelta > 120) {
          setDriftFlag("critical")
        } else if (latencyDelta > 500 || tokenDelta > 60) {
          setDriftFlag("warning")
        } else {
          setDriftFlag("stable")
        }

      } else {
        const resA = await fetchInference(configA)
        setResultA(resA)
        setResultB(null)
        setDriftFlag("stable")
      }
    } catch (err) {
      console.error("Execution failed:", err)
      setError(err instanceof Error ? err.message : "Execution error occurred.")
    } finally {
      setLoading(false)
    }
  }

  const runStabilitySuite = async () => {
    setLoading(true)
    setError(null)
    setResultA(null)
    setResultB(null)

    const newSnapshot: Snapshot = {
      timestamp: new Date().toISOString(),
      results: []
    }

    try {
      const results = await Promise.all(
        TEST_SUITE.map(async (test) => {
          const start = performance.now()
          const res = await fetch("https://michal-unboarded-erna.ngrok-free.dev/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              prompt: test.prompt,
              mode: test.id,
              ...FIXED_CONFIG
            })
          })

          if (!res.ok) throw new Error("Backend error")

          const data = await res.json()

          const assertionResults = test.assertions.map(fn => fn(data.response_text))
          const assertionPass = assertionResults.every(Boolean)

          return {
            id: test.id,
            name: test.name,
            latency_ms: data.latency_ms ?? Math.round(performance.now() - start),
            input_tokens: data.input_tokens,
            output_tokens: data.output_tokens,
            output_length: data.response_text.length,
            response_text: data.response_text,
            assertions: assertionResults,
            assertionPass
          }
        })
      )

      newSnapshot.results = results
      const updated = [...snapshots, newSnapshot]
      setSnapshots(updated)
      localStorage.setItem("stability_snapshots", JSON.stringify(updated))

    } catch (err) {
      console.error(err)
      setError("Stability Suite Execution Failed.")
    } finally {
      setLoading(false)
    }
  }

  if (!isClient) return <div className="h-screen w-screen bg-[#050816]" />

  return (
    <main className="relative w-screen h-screen overflow-hidden bg-[#050816] text-gray-200">

      {/* Top System Strip */}
      <div className="absolute top-0 left-0 right-0 h-16 bg-black/40 backdrop-blur-xl border-b border-indigo-500/20 flex items-center justify-between px-10 z-[100]">
        <div className="text-indigo-400 tracking-widest text-[10px] uppercase font-semibold">
          AI RESEARCH OPERATIONS DECK
        </div>

        <div className="flex items-center gap-8 text-xs text-gray-400 font-medium">
          <div className="flex items-center gap-3">
            <span className={`text-[10px] uppercase tracking-widest ${appMode === "experiment" ? "text-indigo-400" : "text-gray-600"}`}>EXP</span>
            <Switch
              checked={appMode === "stability"}
              onCheckedChange={(c) => setAppMode(c ? "stability" : "experiment")}
              className="scale-75 data-[state=checked]:bg-purple-500 data-[state=unchecked]:bg-indigo-500"
            />
            <span className={`text-[10px] uppercase tracking-widest ${appMode === "stability" ? "text-purple-400" : "text-gray-600"}`}>STB</span>
          </div>

          <div className="w-px h-4 bg-gray-800" />

          <div>Node: Kaggle-GPU</div>
          <div>Mode: {compareMode ? "Dual Core" : "Single Core"}</div>
          <div className={`flex items-center gap-2 ${driftFlag === "critical" ? "text-red-400" : driftFlag === "warning" ? "text-yellow-400" : "text-green-400"}`}>
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${driftFlag === "critical" ? "bg-red-400" : driftFlag === "warning" ? "bg-yellow-400" : "bg-green-400"}`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${driftFlag === "critical" ? "bg-red-500" : driftFlag === "warning" ? "bg-yellow-500" : "bg-green-500"}`}></span>
            </span>
            <span className="uppercase tracking-wider text-[10px]">
              {driftFlag === "stable" ? "Stable" : driftFlag === "warning" ? "Warning" : "Critical"}
            </span>
          </div>
        </div>
      </div>

      {/* Config Cluster (Left) */}
      <div className="absolute left-12 top-1/2 -translate-y-1/2 w-80 bg-black/30 backdrop-blur-xl border border-indigo-500/20 rounded-xl p-8 space-y-10 z-[60] shadow-[0_0_30px_rgba(0,0,0,0.5)]">

        {/* Core A Controls */}
        <ConfigControls
          config={configA}
          setConfig={setConfigA}
          disabled={appMode === "stability"}
          label={`Control Cluster ${compareMode ? "A" : ""}`}
          colorClass="text-indigo-400"
          borderClass="border-indigo-500"
        />

        {/* Core B Controls */}
        {compareMode && (
          <ConfigControls
            config={configB}
            setConfig={setConfigB}
            disabled={appMode === "stability"}
            label="Control Cluster B"
            colorClass="text-purple-400"
            borderClass="border-purple-500"
          />
        )}

      </div>

      {/* AI CORE (Centerpiece) */}
      <div
        className={`absolute left-[40%] top-1/2 -translate-x-1/2 -translate-y-1/2 w-[520px] h-[520px] rounded-full border border-indigo-500/30 backdrop-blur-2xl flex flex-col items-center justify-center p-12 transition-all duration-700 z-[50] ${appMode === "experiment"
          ? "shadow-[0_0_160px_rgba(139,92,246,0.35)] pulse-fast"
          : "shadow-[0_0_80px_rgba(59,130,246,0.25)]"
          }`}
        style={{
          background: appMode === "experiment"
            ? "radial-gradient(circle at center, rgba(139,92,246,0.25), transparent 70%)"
            : "radial-gradient(circle at center, rgba(59,130,246,0.18), transparent 65%)"
        }}
      >
        {appMode === "stability" && (
          <div className="absolute inset-0 rounded-full border border-blue-500/20 pointer-events-none" />
        )}

        <div key={appMode} className="text-[10px] uppercase tracking-widest text-indigo-300/80 mb-2 drop-shadow-[0_0_10px_rgba(99,102,241,0.5)] animate-in fade-in zoom-in-95 duration-200 z-10">
          {appMode === "experiment" ? "Reactor Core" : "Regression Core"}
        </div>

        <div className="w-full h-px bg-indigo-500/20 my-4" />

        {appMode === "experiment" ? (
          <>
            <textarea
              className="w-full h-40 bg-black/40 border border-indigo-500/20 rounded-md p-5 text-sm focus:outline-none focus:border-indigo-400 focus:shadow-[0_0_20px_rgba(99,102,241,0.2)] resize-none text-indigo-50 leading-relaxed placeholder:text-indigo-300/30 transition-all z-20"
              placeholder="Enter master prompt..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
            />

            <div className="flex items-center space-x-3 mt-5 z-20">
              <span className="text-[9px] text-indigo-300/70 tracking-widest uppercase">Dual Core (Compare)</span>
              <Switch checked={compareMode} onCheckedChange={setCompareMode} className="data-[state=checked]:bg-indigo-500 scale-75 origin-right" />
            </div>
          </>
        ) : (
          <div className="w-full text-left text-xs space-y-3 mb-2 z-20 px-2 mt-2">
            {TEST_SUITE.map((test) => (
              <div key={test.id} className="flex justify-between border-b border-indigo-500/10 pb-2">
                <span className="text-gray-300 font-medium tracking-wide">{test.name}</span>
                <span className="text-gray-600 uppercase tracking-widest text-[9px]">Locked</span>
              </div>
            ))}
          </div>
        )}

        <button
          onClick={appMode === "experiment" ? runAll : runStabilitySuite}
          disabled={loading}
          className="mt-6 px-10 py-3 rounded-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-[0_0_30px_rgba(139,92,246,0.3)] hover:shadow-[0_0_40px_rgba(139,92,246,0.5)] text-xs tracking-wider font-semibold z-20 text-white transition-all disabled:opacity-50 uppercase border border-indigo-400/30 w-[60%]">
          {loading ? "Executing..." : appMode === "experiment" ? "Execute Core" : "Run Stability Suite"}
        </button>
      </div>

      {/* Output Panel (Right Edge) */}
      <div className="absolute right-0 top-16 bottom-16 w-[35%] bg-black/50 backdrop-blur-2xl border-l border-indigo-500/20 p-10 overflow-y-auto z-[60] shadow-[-20px_0_40px_rgba(0,0,0,0.5)] scrollbar-hide">
        <div className="mb-8 pb-4 border-b border-indigo-500/10 sticky top-0 bg-transparent backdrop-blur-md z-[70] flex justify-between items-end">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-gray-500">
              {appMode === "experiment" ? "Output Feed" : "REGRESSION REPORT"}
            </div>
            {appMode === "stability" && snapshots.length > 0 && (
              <div className="text-[9px] text-gray-600 mt-1.5 uppercase tracking-widest font-mono">
                Snapshots: {snapshots.length} <span className="mx-2 opacity-50">|</span> {new Date(snapshots[snapshots.length - 1].timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>

          {appMode === "stability" && snapshots.length > 1 && (
            <div className={`flex items-center gap-2 ${stabilityDriftFlag === "critical" ? "text-red-400" : stabilityDriftFlag === "warning" ? "text-yellow-400" : "text-green-400"}`}>
              <span className="relative flex h-1.5 w-1.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${stabilityDriftFlag === "critical" ? "bg-red-400" : stabilityDriftFlag === "warning" ? "bg-yellow-400" : "bg-green-400"}`}></span>
                <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${stabilityDriftFlag === "critical" ? "bg-red-500" : stabilityDriftFlag === "warning" ? "bg-yellow-500" : "bg-green-500"}`}></span>
              </span>
              <span className="uppercase tracking-widest text-[9px]">
                {stabilityDriftFlag === "stable" ? "Global: Stable" : stabilityDriftFlag === "warning" ? "Global: Warning" : "Major Drift"}
              </span>
            </div>
          )}
        </div>

        {error && (
          <div className="text-red-400 text-xs tracking-wide bg-red-900/20 p-4 border border-red-500/30 rounded-lg mb-6">
            {error}
          </div>
        )}

        {appMode === "experiment" ? (
          <>
            {!resultA && !resultB && !loading && (
              <div className="text-gray-600 text-sm italic py-20 text-center tracking-wide">Awaiting payload execution...</div>
            )}

            <div className="space-y-12">
              {resultA && (
                <div className="animate-in fade-in slide-in-from-right-4 duration-500">
                  <div className="text-[9px] text-indigo-400 uppercase tracking-widest mb-4">Core A (Control)</div>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-300 font-light leading-relaxed tracking-wide">
                    <ReactMarkdown>{resultA.response_text}</ReactMarkdown>
                  </div>
                </div>
              )}

              {compareMode && resultB && (
                <div className="animate-in fade-in slide-in-from-right-4 duration-500 border-t border-indigo-500/20 pt-8 mt-8">
                  <div className="text-[9px] text-purple-400 uppercase tracking-widest mb-4">Core B (Challenger)</div>
                  <div className="prose prose-invert prose-sm max-w-none text-gray-300 font-light leading-relaxed tracking-wide">
                    <ReactMarkdown>{resultB.response_text}</ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <>
            {snapshots.length === 0 && !loading && (
              <div className="text-gray-600 text-sm italic py-20 text-center tracking-wide">Awaiting suite execution...</div>
            )}

            <div className="space-y-4">
              {snapshots.length > 0 && snapshots[snapshots.length - 1].results.map((res) => (
                <div key={res.id} className="animate-in fade-in slide-in-from-right-4 duration-500">
                  <RegressionBlock res={res} />
                </div>
              ))}
            </div>

            {snapshots.length > 1 && (
              <div className="mt-6 border-t border-indigo-500/20 pt-4">
                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className="text-[10px] uppercase tracking-widest text-indigo-400/80 hover:text-indigo-300 transition-colors"
                >
                  {showHistory ? "- Hide History" : "+ View Snapshot History"}
                </button>

                {showHistory && (
                  <div className="mt-4 space-y-4 animate-in slide-in-from-top-2 duration-300">
                    {snapshots.slice(0, -1).reverse().map((snap, idx) => (
                      <div
                        key={idx}
                        className="bg-black/30 border border-indigo-500/10 p-4 rounded-md"
                      >
                        <div className="text-[10px] uppercase tracking-widest text-gray-500 border-b border-indigo-500/10 pb-2 mb-3">
                          Run at {new Date(snap.timestamp).toLocaleTimeString()}
                        </div>

                        <div className="grid grid-cols-2 gap-3 text-[10px] uppercase tracking-widest text-gray-400">
                          {snap.results.map((r) => (
                            <div key={r.id} className="flex justify-between">
                              <span className="truncate mr-2 text-indigo-300/60">{r.name}</span>
                              <span className="font-mono text-indigo-300/80">{r.output_tokens}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>

      {/* Bottom Telemetry Drawer */}
      <div className="absolute bottom-0 left-0 right-0 h-16 bg-black/50 backdrop-blur-xl border-t border-indigo-500/20 flex items-center justify-between px-10 z-[100] shadow-[0_-20px_40px_rgba(0,0,0,0.3)]">
        <div className="text-[10px] tracking-widest text-indigo-400/80 uppercase">
          TELEMETRY {compareMode ? "(DUAL)" : ""}
        </div>

        {(resultA || resultB) ? (
          <div className="flex gap-16">
            <div className="flex flex-col items-center">
              <span className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">Latency</span>
              <div className="flex items-center gap-3 text-xs font-mono">
                {resultA && <span className="text-indigo-300">{resultA.latency_ms}ms</span>}
                {compareMode && resultB && <span className="text-purple-300 border-l border-gray-700 pl-3">{resultB.latency_ms}ms</span>}
              </div>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">In Tokens</span>
              <div className="flex items-center gap-3 text-xs font-mono">
                {resultA && <span className="text-indigo-300">{resultA.input_tokens}</span>}
                {compareMode && resultB && <span className="text-purple-300 border-l border-gray-700 pl-3">{resultB.input_tokens}</span>}
              </div>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-[8px] text-gray-500 uppercase tracking-widest mb-1">Out Tokens</span>
              <div className="flex items-center gap-3 text-xs font-mono">
                {resultA && <span className="text-indigo-300">{resultA.output_tokens}</span>}
                {compareMode && resultB && <span className="text-purple-300 border-l border-gray-700 pl-3">{resultB.output_tokens}</span>}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-[9px] text-gray-500 tracking-widest uppercase">Standing By</div>
        )}
      </div>

    </main>
  )
}
