export async function GET() {
  const endpoint = process.env.NEXT_PUBLIC_INFERENCE_URL

  if (!endpoint) {
    return Response.json(
      { error: "Endpoint not configured" },
      { status: 500 },
    )
  }

  return Response.json({ endpoint })
}
