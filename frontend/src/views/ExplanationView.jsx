import ArchitecturePipeline from '../components/ArchitecturePipeline';
import ConfidenceBadge from '../components/ConfidenceBadge';

export default function ExplanationView({ paper }) {
  if (!paper) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Upload and process a paper to view its explanation.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">
          Core Idea
          <ConfidenceBadge confidence={paper.core_idea.confidence} />
        </h3>
        <p className="mt-2 text-slate-700">{paper.core_idea.summary}</p>
        <p className="mt-2 text-slate-600">{paper.core_idea.intuition}</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">
          The Problem
          <ConfidenceBadge confidence={paper.problem.confidence} />
        </h3>
        <p className="mt-2 text-slate-700">{paper.problem.description}</p>
        <p className="mt-2 text-slate-600">{paper.problem.why_it_matters}</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">Implementation Steps</h3>
        <ol className="mt-3 list-decimal space-y-3 pl-6">
          {paper.implementation.steps.map((step) => (
            <li key={`${step.step}-${step.source_chunk_id}`}>
              <div className="font-medium text-slate-800">
                {step.title}
                <ConfidenceBadge confidence={step.confidence} />
              </div>
              <p className="text-slate-700">{step.description}</p>
            </li>
          ))}
        </ol>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">
          Architecture
          <ConfidenceBadge confidence={paper.architecture.confidence} />
        </h3>
        <ArchitecturePipeline nodes={paper.architecture.pipeline} />
        <p className="mt-3 text-slate-700">{paper.architecture.description}</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">
          Tools & Libraries
          <ConfidenceBadge confidence={paper.tools.confidence} />
        </h3>
        <p className="mt-2 text-slate-700">Libraries: {(paper.tools.libraries || []).join(', ') || 'None listed'}</p>
        <p className="mt-1 text-slate-700">Frameworks: {(paper.tools.frameworks || []).join(', ') || 'None listed'}</p>
        <p className="mt-1 text-slate-600">{paper.tools.notes}</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6">
        <h3 className="text-lg font-semibold text-slate-900">Key Challenges</h3>
        <ul className="mt-2 space-y-2">
          {paper.challenges.map((challenge, idx) => (
            <li key={idx} className="text-slate-700">
              {challenge.challenge}
              <ConfidenceBadge confidence={challenge.confidence} />
            </li>
          ))}
        </ul>
      </div>

      {paper.user_level === 'beginner' ? (
        <div className="rounded-xl border border-brand-100 bg-brand-50 p-6">
          <h3 className="text-lg font-semibold text-brand-700">Analogy</h3>
          <p className="mt-2 text-brand-700">{paper.analogy}</p>
        </div>
      ) : null}
    </div>
  );
}
