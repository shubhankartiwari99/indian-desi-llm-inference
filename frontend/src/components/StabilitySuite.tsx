"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, Download, Trash2 } from "lucide-react"

type TestResult = {
    id: string
    name: string
    latency_ms: number
    input_tokens: number
    output_tokens: number
    output_length: number
}

type Snapshot = {
    timestamp: string
    results: TestResult[]
}

const TEST_SUITE = [
    { id: "uplifting", name: "Uplifting English", prompt: "Tell me something uplifting." },
    { id: "hindi_emo", name: "Hindi Emotional", prompt: "मुझे बहुत निराशा महसूस हो रही है।" },
    { id: "mixed", name: "Mixed Mode", prompt: "I feel stuck yaar." },
    { id: "factual", name: "Factual English", prompt: "What are the long-term benefits of daily exercise?" }
]

const FIXED_CONFIG = {
    temperature: 0,
    top_p: 1,
    max_new_tokens: 512,
    do_sample: false
}

export default function StabilitySuite() {
    const [snapshots, setSnapshots] = useState<Snapshot[]>([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        const saved = localStorage.getItem("stability_snapshots")
        if (saved) {
            try {
                setSnapshots(JSON.parse(saved))
            } catch (e) {
                console.error("Failed to parse local snapshots", e)
            }
        }
    }, [])

    const runSuite = async () => {
        setLoading(true)

        const newSnapshot: Snapshot = {
            timestamp: new Date().toISOString(),
            results: []
        }

        try {
            const results = await Promise.all(
                TEST_SUITE.map(async (test) => {
                    const res = await fetch("https://michal-unboarded-erna.ngrok-free.dev/generate", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            prompt: test.prompt,
                            ...FIXED_CONFIG
                        })
                    })

                    if (!res.ok) throw new Error("Backend error")

                    const data = await res.json()

                    return {
                        id: test.id,
                        name: test.name,
                        latency_ms: data.latency_ms,
                        input_tokens: data.input_tokens,
                        output_tokens: data.output_tokens,
                        output_length: data.response_text.length
                    }
                })
            )

            newSnapshot.results = results

            const updated = [...snapshots, newSnapshot]
            setSnapshots(updated)
            localStorage.setItem("stability_snapshots", JSON.stringify(updated))

        } catch (err) {
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    // Calculate Global Severity
    let globalSeverity: "stable" | "warning" | "critical" = "stable"

    const latest = snapshots.at(-1)
    const previous = snapshots.at(-2)

    if (latest && previous) {
        for (let i = 0; i < latest.results.length; i++) {
            const curr = latest.results[i]
            const prev = previous.results[i]

            // Handle structural mismatch safely
            if (!curr || !prev) continue;

            const tokenDelta = Math.abs(curr.output_tokens - prev.output_tokens)
            const lengthDelta = Math.abs(curr.output_length - prev.output_length)

            if (tokenDelta > 100 || lengthDelta > 500) {
                globalSeverity = "critical"
                break
            }

            if (tokenDelta > 40) {
                globalSeverity = "warning"
            }
        }
    }

    return (
        <div className="space-y-6">

            {/* Header Panel */}
            <Card className="p-6 bg-white/5 backdrop-blur-2xl border border-indigo-500/20 rounded-xl shadow-[0_0_60px_rgba(99,102,241,0.15)] flex flex-col md:flex-row gap-6 justify-between items-start md:items-center">
                <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-indigo-100 flex items-center gap-3">
                        Stability Regression Suite
                        {snapshots.length > 1 && (
                            <Badge
                                className={`py-1 px-3 ${globalSeverity === "critical"
                                    ? "bg-red-600 hover:bg-red-600"
                                    : globalSeverity === "warning"
                                        ? "bg-yellow-600 hover:bg-yellow-600"
                                        : "bg-green-600 hover:bg-green-600"
                                    }`}
                            >
                                {globalSeverity === "stable"
                                    ? "🟢 Stable Baseline"
                                    : globalSeverity === "warning"
                                        ? "🟡 Drift Warning"
                                        : "🔴 Major Drift Detected"}
                            </Badge>
                        )}
                    </h2>
                    <p className="text-[11px] uppercase tracking-widest text-gray-500 mt-3 font-medium">
                        Executes {TEST_SUITE.length} parallel benchmark payloads for deterministic latency and output tracking.
                    </p>
                </div>

                <div className="flex gap-3">
                    <Button
                        variant="outline"
                        className="bg-black/30 border-indigo-500/30 hover:bg-black/50 hover:text-indigo-300"
                        onClick={() => {
                            const blob = new Blob(
                                [JSON.stringify(snapshots, null, 2)],
                                { type: "application/json" }
                            )
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement("a")
                            a.href = url
                            a.download = `stability_snapshots_${new Date().toISOString()}.json`
                            a.click()
                        }}
                    >
                        <Download className="w-4 h-4 mr-2" />
                        Export Data
                    </Button>

                    <Button
                        variant="destructive"
                        className="bg-red-950/40 border border-red-500/30 hover:bg-red-900/40 text-red-200"
                        onClick={() => {
                            if (confirm("Clear all snapshot archives?")) {
                                localStorage.removeItem("stability_snapshots")
                                setSnapshots([])
                            }
                        }}
                    >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Reset
                    </Button>

                    <Button
                        onClick={runSuite}
                        disabled={loading}
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 border-none px-6"
                    >
                        {loading ? <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Running...</> : "🚀 Run Suite"}
                    </Button>
                </div>
            </Card>

            {/* Snapshot History UI */}
            {snapshots.length === 0 ? (
                <Card className="p-10 border-indigo-500/20 bg-black/40 text-center flex flex-col items-center justify-center">
                    <p className="text-gray-400 text-lg">No snapshots recorded.</p>
                    <p className="text-sm text-gray-500 mt-2">Run the stability suite to establish a baseline.</p>
                </Card>
            ) : (
                <div className="space-y-6">
                    {snapshots.map((snap, index) => {
                        const isLatest = index === snapshots.length - 1;
                        const prevSnap = index > 0 ? snapshots[index - 1] : null;

                        return (
                            <Card key={snap.timestamp} className={`p-6 border-indigo-500/20 bg-black/40 ${isLatest ? 'ring-1 ring-indigo-500/50' : 'opacity-75'}`}>
                                <div className="flex justify-between items-center mb-6">
                                    <h3 className="text-md font-medium text-indigo-200">
                                        Snapshot {index + 1}
                                        {isLatest && <Badge variant="outline" className="ml-3 border-indigo-500/30 text-indigo-300">Latest</Badge>}
                                    </h3>
                                    <span className="text-xs text-gray-500">{new Date(snap.timestamp).toLocaleString()}</span>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                                    {snap.results.map((test, tIdx) => {
                                        const prevTest = prevSnap?.results[tIdx];

                                        const latDelta = prevTest ? test.latency_ms - prevTest.latency_ms : 0;
                                        const tokDelta = prevTest ? test.output_tokens - prevTest.output_tokens : 0;

                                        return (
                                            <Card key={test.id} className="p-4 border-indigo-500/10 bg-white/5 space-y-3">
                                                <div className="text-sm font-medium text-gray-300 truncate" title={test.name}>{test.name}</div>

                                                <div className="flex justify-between items-end">
                                                    <div>
                                                        <div className="text-xs text-gray-500">Latency</div>
                                                        <div className="text-indigo-400 font-semibold text-sm mt-1 flex items-center gap-2">
                                                            {test.latency_ms} ms
                                                            {prevTest && latDelta !== 0 && (
                                                                <span className={`text-[10px] ${latDelta > 0 ? 'text-yellow-400' : 'text-green-400'}`}>
                                                                    {latDelta > 0 ? '+' : ''}{latDelta}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>

                                                    <div className="text-right">
                                                        <div className="text-xs text-gray-500">Tokens</div>
                                                        <div className="text-indigo-400 font-semibold text-sm mt-1 flex items-center justify-end gap-2">
                                                            {test.output_tokens}
                                                            {prevTest && tokDelta !== 0 && (
                                                                <span className={`text-[10px] ${Math.abs(tokDelta) > 50 ? 'text-red-400' : (tokDelta > 0 ? 'text-yellow-400' : 'text-green-400')}`}>
                                                                    {tokDelta > 0 ? '+' : ''}{tokDelta}
                                                                </span>
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>
                                            </Card>
                                        )
                                    })}
                                </div>
                            </Card>
                        )
                    })}
                </div>
            )}

        </div>
    )
}
