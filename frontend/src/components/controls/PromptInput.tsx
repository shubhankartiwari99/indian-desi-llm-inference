export default function PromptInput({ value, onChange }: any) {
  return (
    <textarea
      className="w-full p-2 border rounded"
      placeholder="Enter prompt..."
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  );
}
