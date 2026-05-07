export default function ConfidenceBadge({ confidence }) {
  if (confidence === 'high') return null;

  if (confidence === 'medium') {
    return (
      <span className="ml-2 inline-flex items-center rounded-full bg-amber-100 px-2 py-1 text-xs font-semibold text-amber-800">
        ⚠️ Medium
      </span>
    );
  }

  return (
    <span
      title="This may be inferred from the paper. Verify with the original source."
      className="ml-2 inline-flex cursor-help items-center rounded-full bg-red-100 px-2 py-1 text-xs font-semibold text-red-700"
    >
      🔴 Low
    </span>
  );
}
