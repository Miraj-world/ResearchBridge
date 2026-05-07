import { useEffect, useRef, useState } from 'react';
import { uploadPaper } from '../hooks/useApi';

const STAGES = ['Parsing', 'Chunking', 'Extracting', 'Verifying', 'Done'];

export default function UploadView({ onProcessed }) {
  const [file, setFile] = useState(null);
  const [level, setLevel] = useState('intermediate');
  const [loading, setLoading] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [error, setError] = useState('');
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) {
      setError('Please upload a PDF first.');
      return;
    }

    setError('');
    setLoading(true);
    setStageIndex(0);

    timerRef.current = setInterval(() => {
      setStageIndex((prev) => (prev < STAGES.length - 2 ? prev + 1 : prev));
    }, 1000);

    try {
      const uploadResult = await uploadPaper(file, level);
      setStageIndex(STAGES.length - 1);
      onProcessed(uploadResult.paper_id);
    } catch (err) {
      setError(err.message || 'Upload failed.');
    } finally {
      if (timerRef.current) clearInterval(timerRef.current);
      setLoading(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slate-900">Upload Research Paper</h2>
      <p className="mt-1 text-sm text-slate-600">Upload a PDF and pick your learning level.</p>

      <form onSubmit={handleSubmit} className="mt-5 space-y-4">
        <label className="block cursor-pointer rounded-lg border-2 border-dashed border-slate-300 p-6 text-center text-sm text-slate-600 hover:border-brand-500">
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          {file ? file.name : 'Drag-and-drop or click to upload PDF'}
        </label>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">Learning Level</label>
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {loading ? 'Processing...' : 'Submit'}
        </button>
      </form>

      {loading ? (
        <div className="mt-4 rounded-md bg-slate-50 p-3 text-sm text-slate-700">
          Stage: <span className="font-semibold">{STAGES[stageIndex]}</span>
          <div className="mt-2 h-2 rounded bg-slate-200">
            <div
              className="h-2 rounded bg-brand-500 transition-all"
              style={{ width: `${((stageIndex + 1) / STAGES.length) * 100}%` }}
            />
          </div>
        </div>
      ) : null}

      {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
