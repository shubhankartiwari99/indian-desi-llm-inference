export async function resolveEndpoint() {
  const res = await fetch("/api/runtime-endpoint", {
    cache: "no-store",
  })

  if (!res.ok) {
    throw new Error("Could not resolve backend endpoint")
  }

  const data = await res.json()
  return data.endpoint
}
