import React, { useState } from 'react';
import { useStore } from '../store';
import type { EscalationStep } from '../api';

const SCENARIOS = [
  {
    title: 'Deposit Withheld (Rental)',
    text: 'I vacated my rental apartment 40 days ago after serving a full 1-month notice. The landlord has refused to return my ₹1,20,000 security deposit, claiming vague maintenance charges without any bills or receipts.',
  },
  {
    title: 'Unpaid Invoices (Freelance)',
    text: 'I delivered the completed web application source code to the client 60 days ago. The client approved the work via email but is now ghosting my follow-ups and has not paid the outstanding ₹95,000 invoice.',
  },
  {
    title: 'Salary Deduction (Employment)',
    text: 'I resigned due to a medical emergency and offered 15 days notice instead of 60 days. The company is refusing to give my relieving letter and is demanding 2 months gross salary deduction as notice buyout.',
  },
];

export function NavigatorView() {
  const { navigatorResult, isNavigating, submitSituation } = useStore();
  const [situationText, setSituationText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!situationText.trim() || isNavigating) return;
    submitSituation(situationText.trim());
  };

  const handleScenarioSelect = (text: string) => {
    setSituationText(text);
    submitSituation(text);
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="mb-8 pb-6 border-b border-[var(--color-paper-dark)]">
        <span className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)]">
          Dispute Resolution & Escalation
        </span>
        <h2 className="text-3xl font-serif font-bold text-[var(--color-ink)] mt-0.5">
          Situation Navigator
        </h2>
        <p className="text-sm font-sans text-[var(--color-ink-faded)] mt-1">
          Turn contract friction into a clear, calibrated strategy before hiring an expensive attorney.
        </p>
      </div>

      {/* Intake Card */}
      <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 mb-8 shadow-sm font-sans">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-[var(--color-ink)] mb-2 font-mono">
          Describe What Happened
        </h3>
        <p className="text-xs text-[var(--color-ink-faded)] mb-4">
          Explain what the other party did, what amount or right is disputed, and any deadlines that passed.
        </p>

        {/* Quick Scenario Chips */}
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <span className="text-xs font-mono text-[var(--color-ink-light)]">Try sample scenario:</span>
          {SCENARIOS.map((s, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleScenarioSelect(s.text)}
              className="text-xs px-3 py-1 bg-[var(--color-paper)] border border-[var(--color-paper-dark)] rounded hover:border-[var(--color-ink)] text-[var(--color-ink)] transition-colors"
            >
              {s.title}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            value={situationText}
            onChange={(e) => setSituationText(e.target.value)}
            rows={4}
            placeholder="E.g. I moved out 30 days ago, landlord has not returned my security deposit..."
            className="w-full p-4 text-sm bg-[var(--color-paper)] border border-[var(--color-paper-dark)] rounded font-serif focus:outline-none focus:border-[var(--color-ink)]"
          />

          <button
            type="submit"
            disabled={isNavigating || !situationText.trim()}
            className="px-6 py-2.5 bg-[var(--color-ink)] text-[var(--color-paper)] text-sm font-medium rounded hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            {isNavigating ? 'Analyzing Situation...' : 'Build Escalation Roadmap →'}
          </button>
        </form>
      </div>

      {/* Loading */}
      {isNavigating && (
        <div className="flex flex-col items-center justify-center py-12 gap-3">
          <div className="w-8 h-8 border-2 border-[var(--color-ink)] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-[var(--color-ink-faded)] font-sans">
            Calibrating escalation ladder and checking statutory remedies...
          </p>
        </div>
      )}

      {/* Results Section */}
      {navigatorResult && !isNavigating && (
        <div className="space-y-8 font-sans">
          {/* Urgent Lawyer Banner */}
          {navigatorResult.urgent_lawyer_needed && (
            <div className="p-4 rounded-lg bg-[var(--color-vermilion-bg)] border border-[var(--color-vermilion)] text-[var(--color-vermilion)]">
              <div className="flex items-center gap-2 font-bold text-sm mb-1">
                <span>⚠️</span>
                <span>Immediate Legal Notice Recommended</span>
              </div>
              <ul className="text-xs space-y-1 list-disc pl-5">
                {navigatorResult.urgent_reasons.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Situation Summary & Category */}
          <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="font-mono text-xs uppercase px-2 py-0.5 rounded bg-[var(--color-paper-dark)] text-[var(--color-ink)]">
                Category: {navigatorResult.dispute_category}
              </span>
              <span className="text-xs text-[var(--color-ink-light)] font-mono">Calibrated Indian Legal Framework</span>
            </div>
            <p className="text-sm font-serif text-[var(--color-ink)] leading-relaxed">
              {navigatorResult.situation_summary}
            </p>
          </div>

          {/* 4-Step Escalation Ladder */}
          <div>
            <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] mb-4">
              Step-by-Step Escalation Ladder
            </h3>
            <div className="space-y-4">
              {navigatorResult.steps.map((step: EscalationStep) => (
                <div
                  key={step.step_number}
                  className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 shadow-sm hover:border-[var(--color-ink-light)] transition-colors"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                    <div className="flex items-center gap-3">
                      <span className="w-7 h-7 rounded-full bg-[var(--color-ink)] text-[var(--color-paper)] font-mono text-xs flex items-center justify-center font-bold">
                        {step.step_number}
                      </span>
                      <h4 className="text-base font-semibold font-serif text-[var(--color-ink)]">
                        {step.title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-xs">
                      <span className="px-2 py-0.5 rounded bg-[var(--color-paper)] text-[var(--color-ink-faded)] border border-[var(--color-paper-dark)]">
                        ⏱ {step.timeframe}
                      </span>
                      <span className="px-2 py-0.5 rounded bg-[var(--color-paper)] text-[var(--color-ink-faded)] border border-[var(--color-paper-dark)]">
                        💰 {step.cost_estimate}
                      </span>
                    </div>
                  </div>

                  <p className="text-sm text-[var(--color-ink-faded)] font-serif mb-3 leading-relaxed">
                    {step.action_description}
                  </p>

                  {step.tips.length > 0 && (
                    <div className="bg-[var(--color-paper)] rounded p-3 text-xs text-[var(--color-ink)] space-y-1">
                      <span className="font-mono font-semibold uppercase text-[var(--color-ink-light)] block mb-1">
                        Practical Tips:
                      </span>
                      {step.tips.map((t, idx) => (
                        <div key={idx} className="flex items-start gap-1.5">
                          <span className="text-[var(--color-sage)] font-bold">✓</span>
                          <span>{t}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Evidence Needed */}
          <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 shadow-sm">
            <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] mb-3">
              Required Evidence Checklist
            </h3>
            <p className="text-xs text-[var(--color-ink-faded)] mb-3">
              Before sending legal notices or filing claims, assemble these records:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
              {navigatorResult.evidence_needed.map((item, idx) => (
                <div key={idx} className="flex items-center gap-2 p-2 bg-[var(--color-paper)] rounded border border-[var(--color-paper-dark)]">
                  <span className="text-[var(--color-vermilion)]">📁</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Free Legal Aid Directory */}
          <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-6 shadow-sm">
            <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-sage)] mb-3">
              Free & Subsidized Legal Aid Directory (India)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {navigatorResult.free_legal_aid.map((aid, idx) => (
                <div key={idx} className="p-4 rounded border border-[var(--color-paper-dark)] bg-[var(--color-paper)]">
                  <h5 className="font-semibold text-sm text-[var(--color-ink)] mb-1 font-serif">
                    {aid.name}
                  </h5>
                  <p className="text-[var(--color-ink-faded)] mb-2">{aid.description}</p>
                  <div className="font-mono text-[var(--color-ink)] font-medium">
                    📞 {aid.contact}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
