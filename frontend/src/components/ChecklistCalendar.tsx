import React, { useEffect, useState } from 'react';
import { useStore } from '../store';
import { api, type ObligationItem } from '../api';

export function ChecklistCalendar() {
  const { currentDoc, obligations, isLoadingObligations, loadObligations } = useStore();
  const [activeTab, setActiveTab] = useState<'you' | 'they' | 'dates'>('you');

  useEffect(() => {
    if (currentDoc && !obligations && !isLoadingObligations) {
      loadObligations();
    }
  }, [currentDoc, obligations, isLoadingObligations, loadObligations]);

  if (!currentDoc) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] text-[var(--color-ink-light)] font-sans">
        Please upload or select a document first.
      </div>
    );
  }

  if (isLoadingObligations) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <div className="w-10 h-10 border-2 border-[var(--color-ink)] border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-[var(--color-ink-faded)] font-sans">
          Extracting duties, deadlines, and calendar events...
        </p>
      </div>
    );
  }

  const grouped = obligations?.grouped || { you_must: [], they_must: [], dates_to_remember: [] };
  const currentList =
    activeTab === 'you'
      ? grouped.you_must
      : activeTab === 'they'
      ? grouped.they_must
      : grouped.dates_to_remember;

  const icsUrl = api.getIcsDownloadUrl(currentDoc.id);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-[var(--color-paper-dark)]">
        <div>
          <h2 className="text-3xl font-serif font-bold text-[var(--color-ink)]">
            Obligations & Calendar Reminders
          </h2>
          <p className="text-sm font-sans text-[var(--color-ink-faded)] mt-1">
            Contractual duties mapped by party, with deadlines and missed-obligation consequences.
          </p>
        </div>

        {/* Calendar Export */}
        <div className="flex flex-col items-end gap-1">
          <a
            href={icsUrl}
            download
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-[var(--color-ink)] text-[var(--color-paper)] rounded text-sm font-sans font-medium hover:opacity-90 transition-opacity shadow-sm"
          >
            <span>📅</span>
            <span>Download .ics Calendar</span>
          </a>
          <span className="text-[11px] font-mono text-[var(--color-ink-light)]">
            Preconfigured with 3-day advance alerts
          </span>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-[var(--color-paper-dark)] pb-2 font-sans">
        <button
          onClick={() => setActiveTab('you')}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            activeTab === 'you'
              ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
          }`}
        >
          You Must ({grouped.you_must.length})
        </button>
        <button
          onClick={() => setActiveTab('they')}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            activeTab === 'they'
              ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
          }`}
        >
          They Must ({grouped.they_must.length})
        </button>
        <button
          onClick={() => setActiveTab('dates')}
          className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
            activeTab === 'dates'
              ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
          }`}
        >
          Dates & Deadlines ({grouped.dates_to_remember.length})
        </button>
      </div>

      {/* List Content */}
      {currentList.length === 0 ? (
        <div className="text-center py-12 text-sm text-[var(--color-ink-light)] font-sans">
          No explicit obligations found in this category.
        </div>
      ) : (
        <div className="space-y-4">
          {currentList.map((ob: ObligationItem, idx: number) => (
            <div
              key={ob.id || idx}
              className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-5 shadow-sm hover:border-[var(--color-ink-light)] transition-colors font-sans"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-[var(--color-paper-dark)] text-[var(--color-ink)]">
                    {ob.party === 'you' ? 'Your Duty' : ob.party === 'other' ? "Other Party's Duty" : 'Mutual Duty'}
                  </span>
                  {ob.due_kind !== 'none' && (
                    <span className="text-xs font-mono uppercase px-2 py-0.5 rounded bg-[var(--color-turmeric-bg)] text-amber-900 border border-[var(--color-turmeric)]">
                      {ob.due_kind}: {ob.due_value || 'specified in clause'}
                    </span>
                  )}
                </div>

                {ob.evidence_quote && (
                  <span className="verified-badge">
                    ✓ Verified in doc
                  </span>
                )}
              </div>

              {/* Action Description */}
              <p className="text-base font-medium text-[var(--color-ink)] mb-2 font-serif">
                {ob.action}
              </p>

              {/* Consequence if Missed */}
              {ob.consequence && (
                <div className="mb-3 px-3 py-1.5 rounded bg-[var(--color-vermilion-bg)] border-l-2 border-[var(--color-vermilion)] text-xs text-[var(--color-vermilion)]">
                  <strong>Consequence if missed:</strong> {ob.consequence}
                </div>
              )}

              {/* Evidence Quote */}
              {ob.evidence_quote && (
                <blockquote className="text-xs italic text-[var(--color-ink-faded)] pl-3 border-l-2 border-[var(--color-paper-dark)] font-serif">
                  "{ob.evidence_quote}"
                </blockquote>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
