import { useMemo, useState } from 'react';
import ConfidenceBadge from '../components/ConfidenceBadge';

function adaptTextByLevel(text, level) {
  if (!text) return text;
  if (level === 'beginner') return `Simple view: ${text}`;
  if (level === 'intermediate') return `Conceptual view: ${text}`;
  return `Advanced view: ${text}`;
}

function PaperColumn({ paper, level, tint }) {
  if (!paper) {
    return <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-500">Select a paper.</div>;
  }

  return (
    <div className={`rounded-lg border p-4 ${tint}`}>
      <h4 className="text-md font-semibold text-slate-900">{paper.title}</h4>
      <p className="mt-2 text-sm text-slate-700">{adaptTextByLevel(paper.core_idea.summary, level)}</p>
      <p className="mt-3 text-sm font-semibold text-slate-800">Problem <ConfidenceBadge confidence={paper.problem.confidence} /></p>
      <p className="text-sm text-slate-700">{adaptTextByLevel(paper.problem.description, level)}</p>
      <p className="mt-3 text-sm font-semibold text-slate-800">Implementation Steps</p>
      <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
        {paper.implementation.steps.slice(0, 4).map((step) => (
          <li key={`${paper.paper_id}-${step.step}`}>{adaptTextByLevel(step.description, level)}</li>
        ))}
      </ul>
      <p className="mt-3 text-sm font-semibold text-slate-800">Architecture</p>
      <p className="text-sm text-slate-700">{adaptTextByLevel(paper.architecture.description, level)}</p>
      <p className="mt-3 text-sm font-semibold text-slate-800">Tools</p>
      <p className="text-sm text-slate-700">{paper.tools.libraries.join(', ') || 'None listed'}</p>
      <p className="mt-3 text-sm font-semibold text-slate-800">Challenges</p>
      <ul className="mt-1 list-disc pl-5 text-sm text-slate-700">
        {paper.challenges.slice(0, 3).map((c, idx) => (
          <li key={idx}>{adaptTextByLevel(c.challenge, level)}</li>
        ))}
      </ul>
    </div>
  );
}

export default function CompareView({ papers, selected, onSelect, comparison }) {
  const [level1, setLevel1] = useState('intermediate');
  const [level2, setLevel2] = useState('intermediate');

  const hasEnough = papers.length >= 2;

  const paperMap = useMemo(() => {
    const map = new Map();
    papers.forEach((p) => map.set(p.paper_id, p));
    return map;
  }, [papers]);

  const left = comparison?.paper_1 || paperMap.get(selected.paper1) || null;
  const right = comparison?.paper_2 || paperMap.get(selected.paper2) || null;

  if (!hasEnough) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Comparison becomes available once at least two papers are processed.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Paper 1</label>
          <select
            value={selected.paper1}
            onChange={(e) => onSelect('paper1', e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Select paper</option>
            {papers.map((paper) => (
              <option key={paper.paper_id} value={paper.paper_id}>
                {paper.title}
              </option>
            ))}
          </select>
          <select
            value={level1}
            onChange={(e) => setLevel1(e.target.value)}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Paper 2</label>
          <select
            value={selected.paper2}
            onChange={(e) => onSelect('paper2', e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Select paper</option>
            {papers.map((paper) => (
              <option key={paper.paper_id} value={paper.paper_id}>
                {paper.title}
              </option>
            ))}
          </select>
          <select
            value={level2}
            onChange={(e) => setLevel2(e.target.value)}
            className="mt-2 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <PaperColumn paper={left} level={level1} tint="bg-blue-50 border-blue-100" />
        <PaperColumn paper={right} level={level2} tint="bg-emerald-50 border-emerald-100" />
      </div>
    </div>
  );
}
