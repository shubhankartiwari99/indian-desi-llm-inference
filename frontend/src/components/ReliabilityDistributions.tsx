"use client"

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Cell
} from "recharts"

interface ReliabilityDistributionsProps {
    confidence: number[]
    instability: number[]
}

export default function ReliabilityDistributions({ confidence = [], instability = [] }: ReliabilityDistributionsProps) {
    const binData = (data: number[]) => {
        const bins = Array.from({ length: 10 }, (_, i) => ({
            name: `${(i / 10).toFixed(1)}-${((i + 1) / 10).toFixed(1)}`,
            count: 0
        }))
        if (!data || !Array.isArray(data)) return bins
        data.forEach(val => {
            const index = Math.min(Math.floor(val * 10), 9)
            if (index >= 0) bins[index].count++
        })
        return bins
    }

    const confBins = binData(confidence)
    const instBins = binData(instability)

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            <div className="rounded-lg border border-[#0dccf2]/10 bg-black/20 p-4">
                <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-[#0dccf2]">Confidence Distribution</p>
                <div className="h-32 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={confBins}>
                            <XAxis dataKey="name" fontSize={8} stroke="#64748b" />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", fontSize: "10px" }}
                                itemStyle={{ color: "#22d3ee" }}
                            />
                            <Bar dataKey="count" fill="#0dccf2" radius={[2, 2, 0, 0]} opacity={0.8} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="rounded-lg border border-amber-500/10 bg-black/20 p-4">
                <p className="mb-3 text-[10px] font-bold uppercase tracking-widest text-amber-300">Instability Distribution</p>
                <div className="h-32 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={instBins}>
                            <XAxis dataKey="name" fontSize={8} stroke="#64748b" />
                            <Tooltip
                                contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", fontSize: "10px" }}
                                itemStyle={{ color: "#fbbf24" }}
                            />
                            <Bar dataKey="count" fill="#fbbf24" radius={[2, 2, 0, 0]} opacity={0.8} />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>
        </div>
    )
}
