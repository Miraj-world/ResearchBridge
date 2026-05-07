import { useState } from 'react';
import { sendChat } from '../hooks/useApi';

export default function ChatView({ paperId }) {
  const [message, setMessage] = useState('');
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  async function handleSend(e) {
    e.preventDefault();
    if (!paperId || !message.trim()) return;

    const userMessage = { role: 'user', content: message.trim() };
    const nextHistory = [...history, userMessage];
    setHistory(nextHistory);
    setMessage('');
    setLoading(true);

    try {
      const data = await sendChat({ paper_id: paperId, message: userMessage.content, history: nextHistory });
      const assistant = {
        role: 'assistant',
        content: `${data.response}\n\nSources: ${(data.referenced_sections || []).join(', ') || 'None'}`
      };
      setHistory((prev) => [...prev, assistant]);
    } catch (err) {
      setHistory((prev) => [...prev, { role: 'assistant', content: err.message || 'Chat failed.' }]);
    } finally {
      setLoading(false);
    }
  }

  if (!paperId) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
        Process a paper to use chat.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6">
      <h3 className="text-lg font-semibold text-slate-900">Chat Over Paper</h3>

      <div className="mt-4 h-80 overflow-y-auto rounded-md border border-slate-200 p-3">
        {history.length === 0 ? (
          <p className="text-sm text-slate-500">Ask anything about this paper...</p>
        ) : (
          <div className="space-y-3">
            {history.map((msg, idx) => (
              <div key={idx} className={msg.role === 'user' ? 'text-right' : 'text-left'}>
                <span
                  className={`inline-block max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                    msg.role === 'user' ? 'bg-brand-500 text-white' : 'bg-slate-100 text-slate-800'
                  }`}
                >
                  {msg.content}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="mt-4 flex gap-2">
        <input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Ask anything about this paper..."
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-brand-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  );
}
