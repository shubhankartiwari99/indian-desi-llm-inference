import { NextResponse } from "next/server"

export async function POST(req: Request) {
  try {
    const body = await req.json()
    const endpoint = process.env.NEXT_PUBLIC_INFERENCE_URL

    if (!endpoint) {
      return NextResponse.json(
        { error: "Backend endpoint not configured" },
        { status: 503 },
      )
    }

    const send = (payload: unknown) =>
      fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
        cache: "no-store",
      })

    let response = await send(body)
    let text = await response.text()

    const hasMonteCarloField =
      typeof body === "object" &&
      body !== null &&
      "monte_carlo_samples" in (body as Record<string, unknown>)

    if (
      !response.ok &&
      response.status === 400 &&
      hasMonteCarloField &&
      text.includes("Unexpected fields in request.")
    ) {
      const legacyBody = { ...(body as Record<string, unknown>) }
      delete legacyBody.monte_carlo_samples
      response = await send(legacyBody)
      text = await response.text()
    }

    return new Response(text, {
      status: response.status,
      headers: { "Content-Type": "application/json" },
    })
  } catch (err) {
    return NextResponse.json(
      { error: "Backend unreachable", detail: String(err) },
      { status: 503 },
    )
  }
}
