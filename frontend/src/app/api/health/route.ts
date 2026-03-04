import { NextResponse } from "next/server"

import { getHealthEndpoint } from "@/lib/inference-endpoint"

export async function GET() {
  try {
    const endpoint = getHealthEndpoint()

    const response = await fetch(endpoint, {
      method: "GET",
      cache: "no-store",
    })

    const text = await response.text()

    return new Response(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch (err) {
    return NextResponse.json(
      { status: "offline", detail: String(err) },
      { status: 503 },
    )
  }
}
