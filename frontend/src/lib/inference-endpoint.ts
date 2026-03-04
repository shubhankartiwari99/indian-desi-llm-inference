const HARDCODED_GENERATE_URL = "https://michal-unboarded-erna.ngrok-free.dev/generate"
const HARDCODED_BASE_URL = HARDCODED_GENERATE_URL.replace(/\/generate$/, "")

function stripTrailingSlashes(url: string): string {
  return url.replace(/\/+$/, "")
}

export function getInferenceBaseUrl(): string {
  return stripTrailingSlashes(HARDCODED_BASE_URL)
}

export function buildInferenceUrl(pathname: string): string {
  const normalizedPath = pathname.startsWith("/") ? pathname : `/${pathname}`
  if (normalizedPath === "/generate") {
    return HARDCODED_GENERATE_URL
  }
  return `${getInferenceBaseUrl()}${normalizedPath}`
}
