import { useState } from "react";
import { runInference } from "@/lib/api";
import type { InferenceResponse, InferencePayload } from "@/types/inference";

export function useInference() {
  const [data, setData] = useState<InferenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const execute = async (payload: InferencePayload) => {
    setLoading(true);
    setError(null);
    try {
      const res = await runInference(payload);
      setData(res);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Inference failed";
      setError(message);
      console.error(e);
    }
    setLoading(false);
  };

  return { data, loading, error, execute };
}
