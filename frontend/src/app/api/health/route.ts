import { NextResponse } from "next/server"

import { buildInferenceUrl } from "@/lib/inference-endpoint"

export async function GET() {
  try {
    const res = await fetch(buildInferenceUrl("/health"), {
      method: "GET",
      signal: AbortSignal.timeout(3000),
    })

    if (!res.ok) {
      return NextResponse.json({ status: "offline" }, { status: 502 })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    return NextResponse.json({ status: "offline", error: String(error) }, { status: 503 })
  }
}
