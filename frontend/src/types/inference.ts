/** Metrics returned by the inference pipeline */
export interface InferenceMetrics {
  collapse_ratio: number;
  kl_divergence: number;
  entropy_raw: number;
  entropy_final: number;
}

/** Source metadata for an inference run */
export interface InferenceMetadata {
  source: string;
  latency_ms: number;
}

/** Full inference response from the backend */
export interface InferenceResponse {
  raw_output: string;
  final_output: string;
  metrics: InferenceMetrics;
  intervention_type: string;
  metadata: InferenceMetadata;
}

/** Payload sent to the inference endpoint */
export interface InferencePayload {
  prompt: string;
  use_mock: boolean;
}
