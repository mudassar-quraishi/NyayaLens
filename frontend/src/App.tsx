import React from 'react';
import { useStore, type AppView } from './store';
import { Landing } from './components/Landing';
import { Workspace } from './components/Workspace';
import { CompareView } from './components/CompareView';
import { ChecklistCalendar } from './components/ChecklistCalendar';
import { BriefView } from './components/BriefView';
import { NavigatorView } from './components/NavigatorView';
import './index.css';

export default function App() {
  const view = useStore((s) => s.view);
  const setView = useStore((s) => s.setView);
  const error = useStore((s) => s.error);
  const currentDoc = useStore((s) => s.currentDoc);
  const deleteSession = useStore((s) => s.deleteSession);

  return (
    <div className="min-h-screen bg-[var(--color-paper)]">
      {/* Global Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--color-paper)] border-b border-[var(--color-paper-dark)] backdrop-blur-sm bg-opacity-95">
        <div className="max-w-7xl mx-auto px-6 py-2.5 flex items-center justify-between">
          {/* Logo & Disclaimer */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setView('landing')}
              className="text-xl font-bold tracking-tight text-[var(--color-ink)] hover:opacity-80 transition-opacity"
              style={{ fontFamily: 'var(--font-serif)' }}
            >
              NyayaLens
            </button>
            <span className="disclaimer-badge hidden sm:inline-flex">
              ⚖️ Information, not legal advice
            </span>
          </div>

          {/* Navigation */}
          <nav className="flex items-center gap-1.5 sm:gap-2 text-xs font-sans">
            {view !== 'landing' ? (
              <>
                {currentDoc && (
                  <button
                    onClick={() => setView('workspace')}
                    className={`px-3 py-1.5 rounded transition-colors font-medium ${
                      view === 'workspace'
                        ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                        : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink)]'
                    }`}
                  >
                    Manuscript
                  </button>
                )}

                <button
                  onClick={() => setView('compare')}
                  className={`px-3 py-1.5 rounded transition-colors font-medium ${
                    view === 'compare'
                      ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                      : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink)]'
                  }`}
                >
                  Compare
                </button>

                {currentDoc && (
                  <>
                    <button
                      onClick={() => setView('checklist')}
                      className={`px-3 py-1.5 rounded transition-colors font-medium ${
                        view === 'checklist'
                          ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                          : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink)]'
                      }`}
                    >
                      Calendar & Duties
                    </button>
                    <button
                      onClick={() => setView('brief')}
                      className={`px-3 py-1.5 rounded transition-colors font-medium ${
                        view === 'brief'
                          ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                          : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink)]'
                      }`}
                    >
                      Lawyer Brief
                    </button>
                  </>
                )}

                <button
                  onClick={() => setView('navigator')}
                  className={`px-3 py-1.5 rounded transition-colors font-medium ${
                    view === 'navigator'
                      ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                      : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink)]'
                  }`}
                >
                  Navigator
                </button>

                <button
                  onClick={() => setView('privacy')}
                  className={`px-3 py-1.5 rounded transition-colors font-medium ${
                    view === 'privacy'
                      ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                      : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink)]'
                  }`}
                >
                  Privacy
                </button>

                <button
                  onClick={() => deleteSession()}
                  className="px-3 py-1.5 rounded text-[var(--color-vermilion)] hover:bg-[var(--color-vermilion-bg)] transition-colors font-medium ml-1"
                >
                  Wipe Data
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setView('compare')}
                  className="px-3 py-1.5 rounded text-[var(--color-ink-faded)] hover:bg-[var(--color-paper-dark)] transition-colors"
                >
                  Compare Demo
                </button>
                <button
                  onClick={() => setView('navigator')}
                  className="px-3 py-1.5 rounded text-[var(--color-ink-faded)] hover:bg-[var(--color-paper-dark)] transition-colors"
                >
                  Dispute Navigator
                </button>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div
          className="fixed top-12 left-0 right-0 z-40 bg-[var(--color-vermilion-bg)] border-b border-[var(--color-vermilion)] px-6 py-2 text-xs font-sans text-[var(--color-vermilion)] flex items-center justify-between"
        >
          <span>{error}</span>
          <button
            onClick={() => useStore.setState({ error: null })}
            className="underline font-semibold"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content */}
      <main className="pt-14">
        {view === 'landing' && <Landing />}
        {view === 'workspace' && <Workspace />}
        {view === 'compare' && <CompareView />}
        {view === 'checklist' && <ChecklistCalendar />}
        {view === 'brief' && <BriefView />}
        {view === 'navigator' && <NavigatorView />}
        {view === 'privacy' && <PrivacyPanel />}
      </main>
    </div>
  );
}

function PrivacyPanel() {
  const analysis = useStore((s) => s.analysis);
  const redaction = analysis?.redaction;

  return (
    <div className="max-w-3xl mx-auto px-6 py-12 font-sans">
      <div className="mb-8 pb-4 border-b border-[var(--color-paper-dark)]">
        <span className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)]">
          Zero Data Retention & Privacy by Design
        </span>
        <h2 className="text-3xl font-serif font-bold text-[var(--color-ink)] mt-0.5">
          Privacy: What We Mask & Guarantee
        </h2>
      </div>

      <div className="bg-white rounded-lg border border-[var(--color-paper-dark)] p-6 mb-6 shadow-sm">
        <h3 className="text-base font-semibold mb-3 font-serif">
          Masked Identifiers in Current Session
        </h3>
        {redaction?.pii_found && redaction.pii_found.length > 0 ? (
          <ul className="space-y-2">
            {redaction.pii_found.map((item, i) => (
              <li key={i} className="flex items-center gap-3 font-mono text-xs">
                <span className="px-2 py-0.5 bg-[var(--color-sage-bg)] text-[var(--color-sage)] rounded font-semibold uppercase">
                  {item.type}
                </span>
                <span className="text-[var(--color-ink-light)]">→ {item.token}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[var(--color-ink-light)] text-xs">
            No PII was detected or masked in the active document.
          </p>
        )}
      </div>

      <div className="bg-[var(--color-turmeric-bg)] rounded-lg border border-[var(--color-turmeric)] p-6 mb-6">
        <h3 className="text-base font-semibold mb-2 font-serif text-amber-950">
          ⚠️ What is NOT masked automatically
        </h3>
        <p className="text-xs text-amber-900 leading-relaxed">
          Names and addresses are <strong>not</strong> automatically masked to preserve legal party identification in clauses. Structured financial and statutory identifiers (Aadhaar numbers, PAN numbers, Indian phone numbers, emails, bank accounts, and IFSC codes) are replaced with synthetic cryptographic tokens before any text is processed by LLM endpoints.
        </p>
      </div>

      <div className="bg-white rounded-lg border border-[var(--color-paper-dark)] p-6 shadow-sm">
        <h3 className="text-base font-semibold mb-3 font-serif">
          Privacy Commitments
        </h3>
        <ul className="text-xs text-[var(--color-ink-faded)] space-y-2">
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-sage)] font-bold">✓</span>
            <span>Documents are bound strictly to your temporary browser session token.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-sage)] font-bold">✓</span>
            <span>All session documents and parsed clauses are hard-deleted automatically after 24 hours.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-sage)] font-bold">✓</span>
            <span>Clicking "Wipe Data" instantly drops your database records, embeddings, and cached analysis.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-[var(--color-sage)] font-bold">✓</span>
            <span>No user document data is ever retained for model training or secondary telemetry.</span>
          </li>
        </ul>
      </div>
    </div>
  );
}
