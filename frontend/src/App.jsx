import { useEffect, useMemo, useState } from 'react';
import ChatView from './views/ChatView';
import CompareView from './views/CompareView';
import ExplanationView from './views/ExplanationView';
import UploadView from './views/UploadView';
import { comparePapers, getPaper, listPapers } from './hooks/useApi';

const TABS = ['Upload', 'Explanation', 'Chat', 'Compare'];

export default function App() {
  const [activeTab, setActiveTab] = useState('Upload');
  const [currentPaperId, setCurrentPaperId] = useState('');
  const [currentPaper, setCurrentPaper] = useState(null);
  const [papers, setPapers] = useState([]);
  const [compareSelection, setCompareSelection] = useState({ paper1: '', paper2: '' });
  const [comparison, setComparison] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    refreshPapers();
  }, []);

  async function refreshPapers() {
    try {
      const items = await listPapers();
      setPapers(items);
    } catch (err) {
      setError(err.message || 'Failed to load papers');
    }
  }

  async function handleProcessed(paperId) {
    setCurrentPaperId(paperId);
    try {
      const paper = await getPaper(paperId);
      setCurrentPaper(paper);
      setActiveTab('Explanation');
      await refreshPapers();
    } catch (err) {
      setError(err.message || 'Failed to fetch processed paper');
    }
  }

  function handleCompareSelect(key, value) {
    setCompareSelection((prev) => ({ ...prev, [key]: value }));
  }

  async function handleLoadComparison() {
    if (!compareSelection.paper1 || !compareSelection.paper2) {
      setError('Select both papers for comparison.');
      return;
    }

    try {
      setError('');
      const data = await comparePapers(compareSelection.paper1, compareSelection.paper2);
      setComparison(data);
    } catch (err) {
      setError(err.message || 'Failed to compare papers');
    }
  }

  const canCompare = useMemo(() => papers.length >= 2, [papers.length]);

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <h1 className="text-2xl font-bold text-slate-900">AI Research Paper Learning & Implementation Explainer</h1>
          <p className="text-sm text-slate-600">Implementation-first explanations for AI/ML papers.</p>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-6 flex flex-wrap gap-2">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`rounded-full px-4 py-2 text-sm font-semibold ${
                activeTab === tab ? 'bg-brand-500 text-white' : 'bg-white text-slate-700 border border-slate-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {error ? <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div> : null}

        {activeTab === 'Upload' ? <UploadView onProcessed={handleProcessed} /> : null}
        {activeTab === 'Explanation' ? <ExplanationView paper={currentPaper} /> : null}
        {activeTab === 'Chat' ? <ChatView paperId={currentPaperId} /> : null}
        {activeTab === 'Compare' ? (
          <div className="space-y-4">
            <div>
              <button
                onClick={handleLoadComparison}
                disabled={!canCompare}
                className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                Load Comparison
              </button>
            </div>
            <CompareView
              papers={papers}
              selected={compareSelection}
              onSelect={handleCompareSelect}
              comparison={comparison}
            />
          </div>
        ) : null}
      </main>
    </div>
  );
}
