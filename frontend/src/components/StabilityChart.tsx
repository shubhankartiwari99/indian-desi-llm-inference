"use client"

import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
    ResponsiveContainer
} from "recharts"

export default function StabilityChart({ data }: { data: any[] }) {
    if (!data || data.length === 0) {
        return (
            <div className="flex h-[250px] items-center justify-center text-xs text-slate-500">
                No stability data available. Run temperature sweep to populate.
            </div>
        )
    }

    return (
        <div className="w-full h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data}>
                    <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />

                    <XAxis
                        dataKey="temperature"
                        stroke="#94a3b8"
                        fontSize={10}
                        label={{ value: "Temperature", position: "insideBottom", offset: -5, fontSize: 10, fill: "#64748b" }}
                    />

                    <YAxis
                        stroke="#94a3b8"
                        fontSize={10}
                        label={{ value: "Instability", angle: -90, position: "insideLeft", fontSize: 10, fill: "#64748b" }}
                    />

                    <Tooltip
                        contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #1e293b", fontSize: "11px" }}
                        itemStyle={{ color: "#22d3ee" }}
                    />

                    <Line
                        type="monotone"
                        dataKey="instability"
                        stroke="#22d3ee"
                        strokeWidth={2}
                        dot={{ r: 4, fill: "#22d3ee", stroke: "#0f172a", strokeWidth: 1 }}
                        activeDot={{ r: 6, fill: "#0dccf2" }}
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    )
}
