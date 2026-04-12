export default function OutputComparison({ raw, final }: any) {
  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="p-3 border rounded bg-gray-900">
        <h3 className="text-sm text-gray-400">Raw Output</h3>
        <p>{raw}</p>
      </div>

      <div className="p-3 border rounded bg-gray-800">
        <h3 className="text-sm text-gray-400">Final Output</h3>
        <p>{final}</p>
      </div>
    </div>
  );
}
