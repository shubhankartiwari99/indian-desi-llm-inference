export interface InferenceResponse {
  raw_output: string;
  final_output: string;

  metrics: {
    entropy_raw: number;
    entropy_final: number;
    collapse_ratio: number;
    stage_change_rate: number;
  };

  metadata: {
    latency_ms: number;
    tokens: number;
    source: string;
  };
}
