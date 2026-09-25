import React, { useState, useEffect, useRef } from 'react';
import { useStore } from '../store';
import type { QACitation } from '../api';

const SAMPLE_QUESTIONS: Record<string, string[]> = {
  rental: [
    'Can I sublet the property?',
    'What is the lock-in period?',
    'Who pays for maintenance and repairs?',
    'Can the landlord enter the flat without notice?',
    'How and when is the security deposit returned?',
    'Can the landlord arbitrarily increase rent mid-lease?',
  ],
  employment: [
    'Can I work on freelance side projects on weekends?',
    'What is the non-compete duration and scope?',
    'What is the notice period for resignation?',
    'Who owns intellectual property created during employment?',
    'Are there any penalties if I leave before 1 year?',
  ],
  freelance: [
    'When are my invoices paid?',
    'Can the client terminate the contract without paying for work done?',
    'Who owns the copyright before final payment?',
    'Is there an indemnity clause against client lawsuits?',
    'Which city jurisdiction governs disputes?',
  ],
  general: [
    'What are my termination rights?',
    'What are the key financial liabilities?',
    'Who is responsible in case of a breach?',
    'Which court has jurisdiction over disputes?',
  ],
};

export function QADrawer() {
  const {
    currentDoc,
    analysis,
    qaHistory,
    isQALoading,
    qaOpen,
    setQAOpen,
    askQuestion,
    loadQAHistory,
    setActiveClause,
  } = useStore();

  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadQAHistory();
  }, [loadQAHistory]);

  useEffect(() => {
    if (qaOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [qaHistory, qaOpen]);

  if (!currentDoc) return null;

  const docType = analysis?.doc_type || 'general';
  const suggestions = SAMPLE_QUESTIONS[docType] || SAMPLE_QUESTIONS.general;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isQALoading) return;
    const q = input.trim();
    setInput('');
    askQuestion(q);
  };

  const handleChipClick = (q: string) => {
    if (isQALoading) return;
    askQuestion(q);
  };

  const scrollToClause = (ordinal: number) => {
    setActiveClause(ordinal);
    const el = document.getElementById(`clause-${ordinal}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('ring-2', 'ring-[var(--color-turmeric)]');
      setTimeout(() => {
        el.classList.remove('ring-2', 'ring-[var(--color-turmeric)]');
      }, 2500);
    }
  };

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-[var(--color-paper-dark)] shadow-2xl transition-all duration-300 ease-in-out ${
        qaOpen ? 'h-[460px]' : 'h-12'
      }`}
      style={{ fontFamily: 'var(--font-sans)' }}
    >
      {/* Header bar / Toggle */}
      <div
        className="h-12 px-6 flex items-center justify-between cursor-pointer bg-[var(--color-paper)] border-b border-[var(--color-paper-dark)] select-none hover:bg-[var(--color-paper-dark)] transition-colors"
        onClick={() => setQAOpen(!qaOpen)}
      >
        <div className="flex items-center gap-3">
          <span className="text-base">💬</span>
          <span className="font-semibold text-sm tracking-tight text-[var(--color-ink)]" style={{ fontFamily: 'var(--font-serif)' }}>
            Ask This Document
          </span>
          <span className="text-xs text-[var(--color-ink-light)] hidden sm:inline">
            · Evidence-locked · 100% verified quotes · Refuses what isn't written
          </span>
        </div>

        <div className="flex items-center gap-2">
          {qaHistory.length > 0 && (
            <span className="text-xs bg-[var(--color-paper-dark)] px-2 py-0.5 rounded-full text-[var(--color-ink-faded)] font-mono">
              {qaHistory.length} messages
            </span>
          )}
          <button
            type="button"
            className="text-xs font-mono uppercase tracking-wider text-[var(--color-ink-faded)] px-2 py-1 rounded hover:bg-white"
          >
            {qaOpen ? '▼ Minimize' : '▲ Open Copilot'}
          </button>
        </div>
      </div>

      {/* Drawer Body */}
      {qaOpen && (
        <div className="flex flex-col h-[calc(460px-48px)]">
          {/* Suggested Questions Chips */}
          <div className="px-6 py-2 bg-stone-50 border-b border-[var(--color-paper-dark)] flex items-center gap-2 overflow-x-auto">
            <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-ink-light)] flex-shrink-0">
              Suggested:
            </span>
            <div className="flex gap-2">
              {suggestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => handleChipClick(q)}
                  disabled={isQALoading}
                  className="text-xs px-2.5 py-1 rounded-full bg-white border border-[var(--color-paper-dark)] text-[var(--color-ink-faded)] hover:border-[var(--color-ink)] hover:text-[var(--color-ink)] whitespace-nowrap transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
            {qaHistory.length === 0 ? (
              <div className="text-center py-8 text-sm text-[var(--color-ink-light)]">
                <p className="font-serif italic text-base text-[var(--color-ink-faded)] mb-1">
                  "Read the fine print before it reads you."
                </p>
                <p>Ask any question about liabilities, payment terms, notice periods, or rights in English, Hindi, or Hinglish.</p>
                <p className="text-xs mt-2 text-[var(--color-ink-light)]">
                  Every answer must be locked to document clauses. If the document is silent, NyayaLens will explicitly refuse to guess.
                </p>
              </div>
            ) : (
              qaHistory.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  {msg.role === 'user' ? (
                    <div className="bg-[var(--color-ink)] text-[var(--color-paper)] text-sm rounded-lg px-4 py-2.5 max-w-xl">
                      {msg.content}
                    </div>
                  ) : (
                    <div
                      className={`text-sm rounded-lg p-4 max-w-2xl border ${
                        msg.grounded
                          ? 'bg-white border-[var(--color-paper-dark)] shadow-sm'
                          : 'bg-[var(--color-turmeric-bg)] border-[var(--color-turmeric)]'
                      }`}
                    >
                      {/* Honesty Status Banner */}
                      <div className="flex items-center gap-2 mb-2">
                        {msg.grounded ? (
                          <span className="verified-badge">
                            ✓ Evidence-Locked & Verified
                          </span>
                        ) : (
                          <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-vermilion)] bg-white px-2 py-0.5 rounded border border-[var(--color-turmeric)]">
                            ⚠️ Honest Uncertainty (Silent in document)
                          </span>
                        )}
                      </div>

                      {/* Main Answer */}
                      <p className="leading-relaxed text-[var(--color-ink)] whitespace-pre-line mb-3">
                        {msg.content}
                      </p>

                      {/* Citations List */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-[var(--color-paper-dark)] space-y-2">
                          <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-ink-light)] block">
                            Document Evidence ({msg.citations.length}):
                          </span>
                          {msg.citations.map((c: QACitation, i: number) => (
                            <div
                              key={i}
                              className="bg-[var(--color-paper)] p-2.5 rounded border border-[var(--color-paper-dark)] text-xs"
                            >
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-mono font-semibold text-[var(--color-ink)]">
                                  Clause {c.clause_ordinal}: {c.clause_heading || 'Untitled'}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => scrollToClause(c.clause_ordinal)}
                                  className="text-xs underline text-[var(--color-vermilion)] hover:text-black font-mono"
                                >
                                  Jump to C{c.clause_ordinal} →
                                </button>
                              </div>
                              <blockquote className="italic text-[var(--color-ink-faded)] pl-2 border-l-2 border-[var(--color-turmeric)]">
                                "{c.exact_quote}"
                              </blockquote>
                              {c.verified && (
                                <span className="verified-badge mt-1 inline-block">
                                  ✓ Exact document match
                                </span>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}

            {isQALoading && (
              <div className="flex items-center gap-2 text-xs text-[var(--color-ink-light)] py-2 font-mono">
                <span className="inline-block w-3 h-3 border-2 border-[var(--color-ink)] border-t-transparent rounded-full animate-spin" />
                Retrieving clauses & verifying evidence quotes...
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form
            onSubmit={handleSubmit}
            className="p-3 bg-white border-t border-[var(--color-paper-dark)] flex gap-2 items-center"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about this document in English, Hindi, or Hinglish..."
              className="flex-1 px-4 py-2 text-sm bg-[var(--color-paper)] border border-[var(--color-paper-dark)] rounded focus:outline-none focus:border-[var(--color-ink)]"
              disabled={isQALoading}
            />
            <button
              type="submit"
              disabled={isQALoading || !input.trim()}
              className="px-5 py-2 text-sm bg-[var(--color-ink)] text-[var(--color-paper)] rounded hover:opacity-90 disabled:opacity-40 transition-opacity font-medium"
            >
              Ask
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
