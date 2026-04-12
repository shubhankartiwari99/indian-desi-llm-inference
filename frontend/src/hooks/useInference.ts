import { useState } from "react";
import { runInference } from "@/lib/api";

export function useInference() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const execute = async (payload: any) => {
    setLoading(true);
    try {
      const res = await runInference(payload);
      setData(res);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  return { data, loading, execute };
}
