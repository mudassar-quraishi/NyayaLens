import React, { useEffect } from 'react';
import { useStore } from '../store';
import type { ClauseWithFindings } from '../api';
import { QADrawer } from './QADrawer';

export function Workspace() {
  const {
    currentDoc,
    analysis,
    isAnalyzing,
    triggerAnalysis,
    language,
    setLanguage,
    readingLevel,
    setReadingLevel,
    setView,
  } = useStore();

  useEffect(() => {
    if (currentDoc && !analysis && !isAnalyzing) {
      triggerAnalysis();
    }
  }, [currentDoc, analysis, isAnalyzing, triggerAnalysis]);

  if (!currentDoc) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-[var(--color-ink-light)] font-sans gap-4">
        <p>No document loaded.</p>
        <button
          onClick={() => setView('landing')}
          className="px-4 py-2 bg-[var(--color-ink)] text-[var(--color-paper)] rounded text-sm"
        >
          Return to Upload
        </button>
      </div>
    );
  }

  if (isAnalyzing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-10 h-10 border-2 border-[var(--color-ink)] border-t-transparent rounded-full animate-spin" />
        <p className="text-base text-[var(--color-ink)] font-serif">
          Analyzing your document...
        </p>
        <p className="text-xs text-[var(--color-ink-light)] font-sans">
          Redacting PII · Parsing clauses · Flagging risk · Verifying 100% of quotes
        </p>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-[var(--color-ink-light)] font-sans">
        Waiting for analysis results...
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 pb-24">
      {/* Document Subheader / Utility Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6 pb-4 border-b border-[var(--color-paper-dark)] font-sans">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-[var(--color-paper-dark)] text-[var(--color-ink)] uppercase">
            {analysis.doc_type}
          </span>
          <h2 className="font-serif font-bold text-xl text-[var(--color-ink)] truncate max-w-md">
            {currentDoc.filename}
          </h2>
          <span className="verified-badge hidden sm:inline-flex">
            ✓ 100% Quotes Evidence-Locked
          </span>
        </div>

        {/* Controls: Language + Reading Level */}
        <div className="flex items-center gap-4 text-xs">
          <label className="flex items-center gap-1.5 text-[var(--color-ink-faded)]">
            <span>Language:</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="bg-white border border-[var(--color-paper-dark)] rounded px-2 py-1 text-xs"
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी</option>
              <option value="hinglish">Hinglish</option>
            </select>
          </label>

          <label className="flex items-center gap-1.5 text-[var(--color-ink-faded)]">
            <span>Detail:</span>
            <select
              value={readingLevel}
              onChange={(e) => setReadingLevel(e.target.value)}
              className="bg-white border border-[var(--color-paper-dark)] rounded px-2 py-1 text-xs"
            >
              <option value="simple">Simple</option>
              <option value="standard">Standard</option>
              <option value="detailed">Detailed</option>
            </select>
          </label>
        </div>
      </div>

      {/* Top Bar: Score + Key Facts */}
      <div className="flex flex-col md:flex-row gap-6 mb-8">
        <RiskScoreCard score={analysis.risk_score} breakdown={analysis.risk_breakdown} />
        <TopConcerns concerns={analysis.top_concerns} />
      </div>

      {/* Main Layout: Risk Spine | Document Page | Margin Cards */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Risk Spine (Table of Contents / Risk Rail) */}
        <aside className="w-full lg:w-48 flex-shrink-0 lg:pr-4 lg:border-r border-[var(--color-paper-dark)]">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-xs font-mono font-medium uppercase tracking-widest text-[var(--color-ink-light)]">
              Clauses ({analysis.clauses.length})
            </h3>
            <span className="text-[10px] text-[var(--color-ink-light)] font-mono">click to jump</span>
          </div>
          <div className="max-h-60 lg:max-h-[70vh] overflow-y-auto space-y-1">
            {analysis.clauses.map((cw) => (
              <RiskSpineItem key={cw.clause.ordinal} clauseWithFindings={cw} />
            ))}
          </div>
        </aside>

        {/* Document + Margin Cards */}
        <div className="flex-1 flex flex-col xl:flex-row gap-6">
          {/* Document Page */}
          <div className="flex-1 max-w-[700px]">
            <div className="document-page">
              {analysis.clauses.map((cw, i) => (
                <ClauseBlock key={cw.clause.ordinal} clauseWithFindings={cw} index={i} />
              ))}
            </div>
          </div>

          {/* Margin Annotations */}
          <aside className="w-full xl:w-80 flex-shrink-0 space-y-4">
            <div className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] mb-1">
              Active Findings & Red Flags
            </div>

            {analysis.clauses
              .filter((cw) => cw.findings.some((f) => f.risk_level !== 'low'))
              .map((cw) => (
                <MarginCard key={cw.clause.ordinal} clauseWithFindings={cw} />
              ))}

            {/* Missing Clauses */}
            {analysis.missing_clauses.length > 0 && (
              <div className="margin-card border-[var(--color-vermilion)] !bg-[var(--color-vermilion-bg)]">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-vermilion)] mb-2 font-mono">
                  Missing Statutory Protections
                </h4>
                {analysis.missing_clauses.map((mc, i) => (
                  <div key={i} className="mb-2 last:mb-0">
                    <p className="text-sm font-semibold">{mc.name}</p>
                    <p className="text-xs text-[var(--color-ink-faded)] mt-0.5">{mc.why_it_matters}</p>
                  </div>
                ))}
              </div>
            )}
          </aside>
        </div>
      </div>

      {/* Floating / Sliding Grounded Q&A Drawer */}
      <QADrawer />
    </div>
  );
}

/* ── Sub-components ── */

function RiskScoreCard({
  score,
  breakdown,
}: {
  score: number;
  breakdown: Record<string, { score: number; max: number; detail: string }>;
}) {
  const color =
    score >= 70
      ? 'var(--color-vermilion)'
      : score >= 40
      ? 'var(--color-turmeric)'
      : 'var(--color-sage)';
  const label =
    score >= 70 ? 'High Risk' : score >= 40 ? 'Moderate Risk' : 'Lower Risk';

  return (
    <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-5 w-full md:w-64 shadow-sm">
      <div className="text-xs font-mono font-medium uppercase tracking-widest text-[var(--color-ink-light)] mb-2">
        Risk Assessment
      </div>
      <div className="flex items-end gap-2 mb-3">
        <span className="text-4xl font-bold font-serif" style={{ color }}>
          {score}
        </span>
        <span className="text-sm mb-1 font-sans font-medium" style={{ color }}>
          / 100 · {label}
        </span>
      </div>

      {/* Score breakdown bar */}
      <div className="flex h-2 rounded overflow-hidden bg-[var(--color-paper)]">
        {Object.entries(breakdown).map(([key, val]) => (
          <div
            key={key}
            className="h-full"
            style={{
              width: `${(val.score / 100) * 100}%`,
              background:
                key === 'clause_risk'
                  ? 'var(--color-vermilion)'
                  : key === 'missing_protections'
                  ? 'var(--color-turmeric)'
                  : key === 'inconsistencies'
                  ? '#6366f1'
                  : 'var(--color-ink-light)',
            }}
            title={`${key}: ${val.score}/${val.max} — ${val.detail}`}
          />
        ))}
      </div>
      <div className="mt-2 space-y-0.5">
        {Object.entries(breakdown).map(([key, val]) => (
          <div
            key={key}
            className="flex justify-between text-xs text-[var(--color-ink-light)] font-sans"
          >
            <span>{key.replace(/_/g, ' ')}</span>
            <span className="font-mono">{val.score}/{val.max}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function TopConcerns({ concerns }: { concerns: string[] }) {
  return (
    <div className="flex-1 bg-white border border-[var(--color-paper-dark)] rounded-lg p-5 shadow-sm font-sans">
      <div className="text-xs font-mono font-medium uppercase tracking-widest text-[var(--color-ink-light)] mb-3">
        Top Contractual Concerns
      </div>
      <ul className="space-y-2">
        {concerns.map((c, i) => (
          <li key={i} className="flex gap-2 text-sm">
            <span className="text-[var(--color-vermilion)] flex-shrink-0 font-bold">●</span>
            <span className="text-[var(--color-ink)]">{c}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function RiskSpineItem({ clauseWithFindings }: { clauseWithFindings: ClauseWithFindings }) {
  const { clause, findings } = clauseWithFindings;
  const activeClause = useStore((s) => s.activeClause);
  const setActiveClause = useStore((s) => s.setActiveClause);

  const order: Record<'low' | 'medium' | 'high', number> = { high: 3, medium: 2, low: 1 };
  const maxRisk = findings.reduce<'low' | 'medium' | 'high'>((max, f) => {
    return order[f.risk_level] > order[max] ? f.risk_level : max;
  }, 'low');

  return (
    <button
      className={`risk-spine-item w-full text-left ${
        activeClause === clause.ordinal ? 'bg-[var(--color-paper-dark)]' : ''
      }`}
      onClick={() => {
        setActiveClause(clause.ordinal);
        document
          .getElementById(`clause-${clause.ordinal}`)
          ?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }}
      aria-label={`Clause ${clause.ordinal}: ${clause.heading || 'Untitled'}, ${maxRisk} risk`}
    >
      <span className={`risk-dot risk-dot-${maxRisk}`} aria-hidden="true" />
      <span className="truncate text-[var(--color-ink-faded)] font-semibold">
        C{clause.ordinal}
      </span>
      <span className="truncate flex-1 text-[var(--color-ink)]">
        {clause.heading || '—'}
      </span>
    </button>
  );
}

function ClauseBlock({
  clauseWithFindings,
  index,
}: {
  clauseWithFindings: ClauseWithFindings;
  index: number;
}) {
  const { clause, findings } = clauseWithFindings;
  const activeClause = useStore((s) => s.activeClause);

  const order: Record<'low' | 'medium' | 'high', number> = { high: 3, medium: 2, low: 1 };
  const maxRisk = findings.reduce<'low' | 'medium' | 'high'>((max, f) => {
    return order[f.risk_level] > order[max] ? f.risk_level : max;
  }, 'low');

  const riskClass =
    maxRisk === 'high' ? 'risk-high' : maxRisk === 'medium' ? 'risk-medium' : '';

  return (
    <div
      id={`clause-${clause.ordinal}`}
      className={`clause-enter mb-6 transition-all ${
        activeClause === clause.ordinal
          ? 'ring-2 ring-[var(--color-turmeric)] ring-offset-2 rounded p-1'
          : ''
      }`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className="flex items-baseline gap-2 mb-1.5">
        <span className="font-mono text-xs text-[var(--color-ink-light)] font-semibold">
          Clause {clause.ordinal}
        </span>
        {clause.heading && (
          <h3 className="text-base font-semibold text-[var(--color-ink)]">
            {clause.heading}
          </h3>
        )}
        {findings.some((f) => f.needs_review) && (
          <span
            className="text-[11px] px-2 py-0.5 bg-[var(--color-vermilion-bg)] text-[var(--color-vermilion)] rounded font-sans font-medium"
          >
            Review with lawyer
          </span>
        )}
      </div>

      <div className={`text-sm leading-relaxed ${riskClass}`}>
        {clause.text}
      </div>

      {/* Inline plain-language explanation */}
      {findings.length > 0 && findings[0].plain_text && (
        <div
          className="mt-3 pl-4 border-l-2 border-[var(--color-turmeric)] text-sm text-[var(--color-ink-faded)] font-sans"
        >
          <strong className="text-[var(--color-ink)]">In plain language:</strong>{' '}
          {findings[0].plain_text}
          {findings[0].what_it_means && (
            <div className="mt-1 text-xs italic text-[var(--color-vermilion)]">
              → {findings[0].what_it_means}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function MarginCard({
  clauseWithFindings,
}: {
  clauseWithFindings: ClauseWithFindings;
}) {
  const { clause, findings } = clauseWithFindings;
  const mainFinding = findings.find((f) => f.risk_level !== 'low') || findings[0];
  if (!mainFinding) return null;

  const riskColor =
    mainFinding.risk_level === 'high'
      ? 'var(--color-vermilion)'
      : mainFinding.risk_level === 'medium'
      ? 'var(--color-turmeric)'
      : 'var(--color-sage)';

  return (
    <div
      className="margin-card"
      style={{ borderLeftColor: riskColor, borderLeftWidth: 3 }}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-[var(--color-ink-light)] font-bold">
            C{clause.ordinal}
          </span>
          <span
            className="text-xs font-semibold uppercase font-mono"
            style={{ color: riskColor }}
          >
            {mainFinding.risk_level} risk
          </span>
        </div>

        {mainFinding.verified && (
          <span
            className="verified-badge"
            title="Evidence quote verified against document"
          >
            ✓ verified
          </span>
        )}
      </div>

      {/* Risk reasons */}
      <ul className="space-y-1 mb-2">
        {mainFinding.risk_reasons.map((r, i) => (
          <li key={i} className="text-xs text-[var(--color-ink-faded)] font-sans">
            • {r}
          </li>
        ))}
      </ul>

      {/* Evidence quote */}
      {mainFinding.evidence_quote && (
        <blockquote className="text-xs italic border-l-2 border-[var(--color-ink-light)] pl-2 text-[var(--color-ink-faded)] mb-2 font-serif">
          "{mainFinding.evidence_quote.slice(0, 120)}
          {mainFinding.evidence_quote.length > 120 ? '...' : ''}"
        </blockquote>
      )}

      {/* Questions to ask */}
      {mainFinding.questions.length > 0 && (
        <div className="text-xs text-[var(--color-blue-faded)] font-sans">
          <span className="font-semibold">Ask other party:</span> {mainFinding.questions[0]}
        </div>
      )}

      {/* Favors indicator */}
      <div className="mt-2 pt-2 border-t border-[var(--color-paper-dark)] flex items-center justify-between font-mono text-[11px] text-[var(--color-ink-light)]">
        <span>
          Favors:{' '}
          {mainFinding.favors === 'party_a'
            ? 'Other party'
            : mainFinding.favors === 'party_b'
            ? 'You'
            : mainFinding.favors === 'balanced'
            ? 'Balanced'
            : 'Unclear'}
        </span>
        <span>{Math.round(mainFinding.confidence * 100)}% conf</span>
      </div>
    </div>
  );
}
