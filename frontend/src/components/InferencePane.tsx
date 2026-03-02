"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import TelemetryHUD from "./TelemetryHUD"
import ReactMarkdown from "react-markdown"

export type InferenceConfig = {
    temperature: number
    top_p: number
    max_new_tokens: number
    do_sample: boolean
}

export type InferenceResult = {
    response_text: string
    latency_ms: number
    input_tokens: number
    output_tokens: number
}

interface InferencePaneProps {
    title: string
    config: InferenceConfig
    onConfigChange: (config: InferenceConfig) => void
    result: InferenceResult | null
}

export default function InferencePane({ title, config, onConfigChange, result }: InferencePaneProps) {
    const [prompt, setPrompt] = useState("")
    const [isLoading, setIsLoading] = useState(false)

    const runInference = async () => {
        setIsLoading(true)

        const res = await fetch("https://michal-unboarded-erna.ngrok-free.dev/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                prompt,
                temperature: config.temperature,
                top_p: config.top_p,
                max_new_tokens: config.max_new_tokens,
            }),
        })

        // Inference resolution logic handled by parent in page.tsx now, InferencePane acts mainly as a UI block
        // If the user meant for it to be self-evaluating in single mode but promise-all in compare, we follow page.tsx fetch
        console.warn("runInference on pane disabled entirely, controlled by page.tsx global master prompt")

        setIsLoading(false)
    }

    return (
        <Card className="p-6 bg-white/5 backdrop-blur-2xl border border-indigo-500/20 rounded-xl shadow-[0_0_60px_rgba(99,102,241,0.15)] space-y-6">

            <h2 className="text-xl font-semibold tracking-tight text-indigo-100">{title} Parameters</h2>

            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="text-[10px] uppercase tracking-wider text-gray-400">Temperature</label>
                    <Input
                        type="number" step="0.1" value={config.temperature}
                        onChange={(e) => onConfigChange({ ...config, temperature: parseFloat(e.target.value) })}
                    />
                </div>
                <div>
                    <label className="text-[10px] uppercase tracking-wider text-gray-400">Top P</label>
                    <Input
                        type="number" step="0.1" value={config.top_p}
                        onChange={(e) => onConfigChange({ ...config, top_p: parseFloat(e.target.value) })}
                    />
                </div>
                <div>
                    <label className="text-[10px] uppercase tracking-wider text-gray-400">Max Tokens</label>
                    <Input
                        type="number" value={config.max_new_tokens}
                        onChange={(e) => onConfigChange({ ...config, max_new_tokens: parseInt(e.target.value) })}
                    />
                </div>
                <div className="flex items-center space-x-2 mt-6">
                    <Switch
                        id={`sampling-${title.replace(/\s+/g, '-')}`}
                        checked={config.do_sample}
                        onCheckedChange={(c) => onConfigChange({ ...config, do_sample: c })}
                    />
                    <label htmlFor={`sampling-${title.replace(/\s+/g, '-')}`} className="text-[10px] uppercase tracking-wider text-gray-400">
                        Sampling
                    </label>
                </div>
            </div>

            <div className="bg-black/40 border border-indigo-500/20 rounded-lg p-5 min-h-[300px] max-h-[500px] overflow-auto prose prose-invert prose-sm max-w-none">
                {result ? (
                    <ReactMarkdown>{result.response_text}</ReactMarkdown>
                ) : (
                    <span className="text-gray-500 italic">Waiting for top-level inference...</span>
                )}
            </div>

            {result && (
                <TelemetryHUD
                    latency={result.latency_ms}
                    inputTokens={result.input_tokens}
                    outputTokens={result.output_tokens}
                    temperature={config.temperature}
                />
            )}

        </Card>
    )
}
