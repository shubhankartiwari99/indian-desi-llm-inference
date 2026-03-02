import { Card } from "@/components/ui/card"

type Props = {
    latency: number
    inputTokens: number
    outputTokens: number
    temperature: number
    delta?: {
        latency?: number
        tokens?: number
    }
}

export default function TelemetryHUD({
    latency,
    inputTokens,
    outputTokens,
    temperature,
    delta
}: Props) {
    return (
        <div className="grid grid-cols-4 gap-4">
            <Card className="p-4 bg-black/40 border-indigo-500/20">
                <div className="text-xs text-gray-400">Latency</div>
                <div className="text-indigo-400 font-semibold">
                    {latency} ms
                    {delta?.latency !== undefined && (
                        <span className={`ml-2 text-xs ${delta.latency > 0 ? "text-yellow-400" : "text-green-400"}`}>
                            {delta.latency > 0 ? "+" : ""}
                            {delta.latency}
                        </span>
                    )}
                </div>
            </Card>

            <Card className="p-4 bg-black/40 border-indigo-500/20">
                <div className="text-xs text-gray-400">Input</div>
                <div className="text-indigo-400 font-semibold">
                    {inputTokens}
                </div>
            </Card>

            <Card className="p-4 bg-black/40 border-indigo-500/20">
                <div className="text-xs text-gray-400">Output</div>
                <div className="text-indigo-400 font-semibold">
                    {outputTokens}
                    {delta?.tokens !== undefined && (
                        <span className={`ml-2 text-xs ${delta.tokens > 0 ? "text-yellow-400" : "text-green-400"}`}>
                            {delta.tokens > 0 ? "+" : ""}
                            {delta.tokens}
                        </span>
                    )}
                </div>
            </Card>

            <Card className="p-4 bg-black/40 border-indigo-500/20">
                <div className="text-xs text-gray-400">Temp</div>
                <div className="text-indigo-400 font-semibold">
                    {temperature}
                </div>
            </Card>
        </div>
    )
}
