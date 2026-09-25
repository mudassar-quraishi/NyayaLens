import React, { useState } from 'react';
import { useStore } from '../store';
import type { ClauseDiffItem } from '../api';

export function CompareView() {
  const { compareResult, isComparing, loadSampleCompare } = useStore();
  const [filter, setFilter] = useState<'all' | 'worse' | 'added' | 'modified' | 'removed'>('all');

  if (isComparing) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="w-10 h-10 border-2 border-[var(--color-ink)] border-t-transparent rounded-full animate-spin" />
        <p className="text-base text-[var(--color-ink)] font-serif">
          Aligning clauses & computing semantic risk delta...
        </p>
        <p className="text-xs text-[var(--color-ink-light)] font-mono">
          Detecting additions, silent deletions, and clause escalations
        </p>
      </div>
    );
  }

  if (!compareResult) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-16 text-center">
        <h2 className="text-3xl font-serif font-bold mb-4">Compare Two Contracts</h2>
        <p className="text-sm text-[var(--color-ink-faded)] max-w-lg mx-auto mb-8 font-sans">
          Never sign an amended contract or second draft without knowing exactly what changed.
          NyayaLens aligns clauses by canonical legal topics, flags silent risks, and warns you if the new version is worse.
        </p>

        <div className="bg-white border border-[var(--color-paper-dark)] rounded-xl p-8 max-w-xl mx-auto shadow-sm">
          <span className="demo-badge mb-3 inline-block">1-Click Demonstration</span>
          <h3 className="text-xl font-serif font-semibold mb-2">
            Freelance Agreement v1 vs v2
          </h3>
          <p className="text-xs text-[var(--color-ink-faded)] font-sans mb-6">
            Compare our planted benchmark sample: Version 2 introduces 10 predatory changes including a 2-year non-compete, net-90 payment terms, and unlimited indemnity.
          </p>
          <button
            onClick={loadSampleCompare}
            className="w-full py-3 px-6 bg-[var(--color-ink)] text-[var(--color-paper)] font-sans text-sm font-medium rounded hover:opacity-90 transition-opacity"
          >
            Run Benchmark Comparison (10 Changes) →
          </button>
        </div>
      </div>
    );
  }

  const {
    summary = '',
    net_risk_delta = 'neutral',
    bottom_line_bullets = [],
    clause_diffs = [],
    overall_score_a = 0,
    overall_score_b = 0,
  } = compareResult || {};

  const diffs = Array.isArray(clause_diffs) ? clause_diffs : [];
  const worseCount = diffs.filter((d) => d.risk_delta === 'worse').length;
  const modCount = diffs.filter((d) => d.change_type === 'modified').length;
  const addCount = diffs.filter((d) => d.change_type === 'added').length;
  const remCount = diffs.filter((d) => d.change_type === 'removed').length;

  const filteredDiffs = diffs.filter((d) => {
    if (filter === 'worse') return d.risk_delta === 'worse';
    if (filter === 'added') return d.change_type === 'added';
    if (filter === 'modified') return d.change_type === 'modified';
    if (filter === 'removed') return d.change_type === 'removed';
    return true;
  });

  const isNetWorse = net_risk_delta === 'worse' || overall_score_b > overall_score_a;

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Top Banner: Net Risk Delta */}
      <div
        className={`rounded-lg border p-6 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
          isNetWorse
            ? 'bg-[var(--color-vermilion-bg)] border-[var(--color-vermilion)]'
            : 'bg-[var(--color-sage-bg)] border-[var(--color-sage)]'
        }`}
      >
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-xl">{isNetWorse ? '⚠️' : '✓'}</span>
            <h2 className="text-2xl font-serif font-bold text-[var(--color-ink)]">
              {isNetWorse ? 'Version 2 is Significantly Worse for You' : 'Risk Decreased in Version 2'}
            </h2>
          </div>
          <p className="text-sm font-sans text-[var(--color-ink-faded)] max-w-2xl">
            {summary}
          </p>
        </div>

        {/* Risk Scores Comparison */}
        <div className="flex items-center gap-4 bg-white px-5 py-3 rounded border border-[var(--color-paper-dark)] font-sans">
          <div className="text-center">
            <div className="text-xs uppercase text-[var(--color-ink-light)] font-mono">Original (v1)</div>
            <div className="text-2xl font-bold font-serif text-[var(--color-sage)]">{overall_score_a}</div>
          </div>
          <span className="text-xl text-[var(--color-ink-light)]">→</span>
          <div className="text-center">
            <div className="text-xs uppercase text-[var(--color-ink-light)] font-mono">Revised (v2)</div>
            <div className="text-2xl font-bold font-serif text-[var(--color-vermilion)]">{overall_score_b}</div>
          </div>
        </div>
      </div>

      {/* 5-Bullet "Bottom Line" */}
      <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 mb-8">
        <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] mb-4">
          The Bottom Line: 5 Critical Changes
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bottom_line_bullets.map((bullet, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 rounded bg-[var(--color-paper)] border border-[var(--color-paper-dark)] text-sm font-sans"
            >
              <span className="text-[var(--color-vermilion)] font-bold flex-shrink-0">
                #{idx + 1}
              </span>
              <span className="text-[var(--color-ink)]">{bullet}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-6 border-b border-[var(--color-paper-dark)] pb-3 font-sans">
        <span className="text-xs font-mono uppercase text-[var(--color-ink-light)] mr-2">Filter:</span>
        <button
          onClick={() => setFilter('all')}
          className={`px-3 py-1 rounded text-xs transition-colors ${
            filter === 'all'
              ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
          }`}
        >
          All Changes ({clause_diffs.length})
        </button>
        <button
          onClick={() => setFilter('worse')}
          className={`px-3 py-1 rounded text-xs transition-colors ${
            filter === 'worse'
              ? 'bg-[var(--color-vermilion)] text-white'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-vermilion)]'
          }`}
        >
          Risk Worse ({worseCount})
        </button>
        <button
          onClick={() => setFilter('modified')}
          className={`px-3 py-1 rounded text-xs transition-colors ${
            filter === 'modified'
              ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
          }`}
        >
          Modified ({modCount})
        </button>
        <button
          onClick={() => setFilter('added')}
          className={`px-3 py-1 rounded text-xs transition-colors ${
            filter === 'added'
              ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
              : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
          }`}
        >
          Added ({addCount})
        </button>
        {remCount > 0 && (
          <button
            onClick={() => setFilter('removed')}
            className={`px-3 py-1 rounded text-xs transition-colors ${
              filter === 'removed'
                ? 'bg-[var(--color-ink)] text-[var(--color-paper)]'
                : 'hover:bg-[var(--color-paper-dark)] text-[var(--color-ink-faded)]'
            }`}
          >
            Removed ({remCount})
          </button>
        )}
      </div>

      {/* Clause Diff Cards */}
      <div className="space-y-6">
        {filteredDiffs.map((diff: ClauseDiffItem, idx: number) => (
          <ClauseDiffCard key={idx} diff={diff} />
        ))}
      </div>
    </div>
  );
}

function ClauseDiffCard({ diff }: { diff: ClauseDiffItem }) {
  const isWorse = diff.risk_delta === 'worse';
  const isBetter = diff.risk_delta === 'better';

  const riskBadgeColor = isWorse
    ? 'bg-[var(--color-vermilion-bg)] text-[var(--color-vermilion)] border-[var(--color-vermilion)]'
    : isBetter
    ? 'bg-[var(--color-sage-bg)] text-[var(--color-sage)] border-[var(--color-sage)]'
    : 'bg-[var(--color-turmeric-bg)] text-amber-800 border-[var(--color-turmeric)]';

  return (
    <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 shadow-sm">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4 pb-3 border-b border-[var(--color-paper-dark)]">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs uppercase px-2 py-0.5 rounded bg-[var(--color-paper-dark)] text-[var(--color-ink)]">
            {diff.topic.replace(/_/g, ' ')}
          </span>
          <span className="text-xs uppercase font-mono text-[var(--color-ink-light)]">
            Type: {diff.change_type}
          </span>
        </div>

        <span className={`text-xs font-mono uppercase px-2.5 py-0.5 rounded border ${riskBadgeColor}`}>
          Risk: {diff.risk_delta}
        </span>
      </div>

      {/* Explanation & Impact */}
      <div className="mb-4">
        <p className="text-sm font-medium text-[var(--color-ink)] mb-1 font-sans">
          {diff.explanation}
        </p>
        <p className="text-xs text-[var(--color-vermilion)] font-sans italic">
          Impact: {diff.impact_on_user}
        </p>
      </div>

      {/* Side-by-side or comparison boxes */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Version 1 */}
        <div className="p-3 bg-[var(--color-paper)] rounded border border-[var(--color-paper-dark)]">
          <div className="text-xs font-mono uppercase text-[var(--color-ink-light)] mb-2 flex items-center justify-between">
            <span>Original (v1) {diff.doc_a_clause_ordinal ? `· C${diff.doc_a_clause_ordinal}` : ''}</span>
          </div>
          <div className="text-xs text-[var(--color-ink-faded)] font-mono whitespace-pre-wrap leading-relaxed">
            {diff.doc_a_text ? diff.doc_a_text : <span className="italic text-[var(--color-ink-light)]">(Clause was not present in v1)</span>}
          </div>
        </div>

        {/* Version 2 */}
        <div
          className={`p-3 rounded border ${
            isWorse
              ? 'bg-[var(--color-vermilion-bg)] border-[var(--color-vermilion-light)]'
              : 'bg-white border-[var(--color-paper-dark)]'
          }`}
        >
          <div className="text-xs font-mono uppercase text-[var(--color-ink-light)] mb-2 flex items-center justify-between">
            <span className={isWorse ? 'text-[var(--color-vermilion)] font-semibold' : ''}>
              Revised (v2) {diff.doc_b_clause_ordinal ? `· C${diff.doc_b_clause_ordinal}` : ''}
            </span>
          </div>
          <div className="text-xs text-[var(--color-ink)] font-mono whitespace-pre-wrap leading-relaxed">
            {diff.doc_b_text ? diff.doc_b_text : <span className="italic text-[var(--color-ink-light)]">(Clause removed in v2)</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
