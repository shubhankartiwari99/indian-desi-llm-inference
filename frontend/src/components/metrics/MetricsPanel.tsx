export default function MetricsPanel({ metrics }: any) {
  if (!metrics) return null;

  return (
    <div className="space-y-2">
      <div>Entropy (Raw): {metrics.entropy_raw}</div>
      <div>Entropy (Final): {metrics.entropy_final}</div>
      <div>Collapse Ratio: {metrics.collapse_ratio}</div>
      <div>Stage Change Rate: {metrics.stage_change_rate}</div>
    </div>
  );
}
