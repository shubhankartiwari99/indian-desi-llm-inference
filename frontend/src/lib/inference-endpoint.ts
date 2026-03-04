export function getGenerateEndpoint() {
  const base = process.env.NEXT_PUBLIC_INFERENCE_URL

  if (!base) {
    throw new Error("NEXT_PUBLIC_INFERENCE_URL is not set")
  }

  return base
}

export function getHealthEndpoint() {
  const base = process.env.NEXT_PUBLIC_INFERENCE_URL

  if (!base) {
    throw new Error("NEXT_PUBLIC_INFERENCE_URL is not set")
  }

  return base.replace("/generate", "/health")
}
