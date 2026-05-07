export default function ArchitecturePipeline({ nodes = [] }) {
  if (!nodes.length) return null;

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {nodes.map((node, idx) => (
        <div key={`${node}-${idx}`} className="flex items-center gap-2">
          <span className="rounded bg-brand-100 px-3 py-1 text-sm font-medium text-brand-700">{node}</span>
          {idx < nodes.length - 1 ? <span className="text-slate-400">→</span> : null}
        </div>
      ))}
    </div>
  );
}
