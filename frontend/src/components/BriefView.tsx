import React from 'react';
import { useStore } from '../store';
import { api } from '../api';

const DEFAULT_QUESTIONS_BY_TYPE: Record<string, string[]> = {
  rental: [
    'Is the 10-month lock-in period legally enforceable if there is a genuine emergency or job transfer?',
    'Is the 18% annual interest penalty on late rent payment legally disproportionate under Indian contract law?',
    'Does the landlord have the right to enter the premises without 24-hour advance written notice?',
    'What is my recourse if the security deposit is not refunded within the stipulated 15-day window?',
    'Who is legally liable if a major structural defect occurs during the tenancy period?',
    'Can the landlord unilaterally escalate rent above standard indexation caps?',
    'Is the notice period for early termination mutual and equitable between both parties?',
    'What evidence should I document during move-in to safeguard against deposit deductions?',
    'Does this agreement require mandatory registration under the state Rent Control Act?',
    'Which local court or Rent Authority has jurisdiction if a dispute arises?',
  ],
  employment: [
    'Is the post-termination non-compete clause legally void under Section 27 of the Indian Contract Act?',
    'Can the employer legally claim ownership of personal side-projects created outside working hours?',
    'Is the training bond or liquidated damages clause enforceable if I resign early?',
    'Can the employer deduct salary in lieu of notice if I cannot serve the full notice period?',
    'Are there hidden IP assignment clauses covering proprietary pre-existing inventions?',
    'What remedies do I have if discretionary bonus or variable pay commitments are breached?',
    'Is the non-solicitation of clients and coworkers enforceable post-resignation?',
    'Does the indemnity clause expose me to personal financial liability for company losses?',
    'Are the dispute resolution and arbitration provisions fair and balanced?',
    'Which state jurisdiction governs employment grievances and labour court claims?',
  ],
  general: [
    'Are the termination clauses mutual and commercially reasonable?',
    'Is the liability limitation balanced or does it expose one party to uncapped damages?',
    'Are there any unilateral modification rights granted to the other party?',
    'What constitutes a material breach under this agreement?',
    'Is the dispute resolution clause realistic in terms of costs and arbitration venue?',
    'Are the intellectual property assignment clauses overly broad?',
    'What warranties or representations am I making that could trigger liability?',
    'Is there an indemnity clause requiring me to defend the other party against third-party claims?',
    'Does this agreement comply with statutory public policy and mandatory local laws?',
    'What specific amendments should I negotiate before signing this draft?',
  ],
};

const CHECKLIST_ITEMS = [
  'Original signed or draft agreement (all pages, annexures, and schedules)',
  'Proof of identity and address (Aadhaar / Passport / Voter ID)',
  'All email correspondence, WhatsApp chats, and written notes regarding negotiations',
  'Payment receipts, bank transfer statements, or invoices related to this agreement',
  'Condition report, photos/videos of premises or initial work deliverables (if applicable)',
  'Prior version or competitor contract for reference comparison',
];

export function BriefView() {
  const { currentDoc, analysis } = useStore();

  if (!currentDoc || !analysis) {
    return (
      <div className="flex items-center justify-center min-h-[50vh] text-[var(--color-ink-light)] font-sans">
        Please upload and analyze a document first.
      </div>
    );
  }

  const pdfUrl = api.getBriefPdfUrl(currentDoc.id);
  const docType = analysis.doc_type || 'general';
  const prioritizedQuestions = DEFAULT_QUESTIONS_BY_TYPE[docType] || DEFAULT_QUESTIONS_BY_TYPE.general;

  const highRiskFindings = analysis.clauses
    .flatMap((cw) =>
      cw.findings
        .filter((f) => f.risk_level === 'high')
        .map((f) => ({ ...f, ordinal: cw.clause.ordinal, heading: cw.clause.heading }))
    );

  const keyFacts = analysis.key_facts || {};

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-6 border-b border-[var(--color-paper-dark)]">
        <div>
          <span className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)]">
            Evidence-Locked Dossier
          </span>
          <h2 className="text-3xl font-serif font-bold text-[var(--color-ink)] mt-0.5">
            Lawyer Consultation Brief
          </h2>
          <p className="text-sm font-sans text-[var(--color-ink-faded)] mt-1">
            Hand this 1-page structured dossier to your lawyer to save billable hours and focus on critical red flags.
          </p>
        </div>

        <a
          href={pdfUrl}
          download
          className="inline-flex items-center gap-2 px-6 py-3 bg-[var(--color-ink)] text-[var(--color-paper)] rounded text-sm font-sans font-medium hover:opacity-90 transition-opacity shadow-sm self-start sm:self-auto"
        >
          <span>📄</span>
          <span>Download PDF Brief</span>
        </a>
      </div>

      {/* Manuscript Styled Brief Preview */}
      <div className="bg-white border border-[var(--color-paper-dark)] rounded-lg p-8 sm:p-12 shadow-sm font-serif">
        {/* Document Header */}
        <div className="border-b-2 border-[var(--color-ink)] pb-6 mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="text-xs font-mono uppercase tracking-widest text-[var(--color-vermilion)] mb-1">
              NyayaLens Legal Consultation Dossier
            </div>
            <h1 className="text-2xl font-bold">{currentDoc.filename}</h1>
            <div className="text-xs font-sans text-[var(--color-ink-light)] mt-1">
              Category: <span className="uppercase font-mono">{analysis.doc_type}</span> · Generated for Client Preparation
            </div>
          </div>

          <div className="text-right font-sans">
            <div className="text-xs uppercase text-[var(--color-ink-light)] font-mono">Assessed Risk</div>
            <div
              className={`text-3xl font-bold font-serif ${
                analysis.risk_score >= 70
                  ? 'text-[var(--color-vermilion)]'
                  : analysis.risk_score >= 40
                  ? 'text-amber-600'
                  : 'text-[var(--color-sage)]'
              }`}
            >
              {analysis.risk_score} / 100
            </div>
          </div>
        </div>

        {/* Section 1: Key Facts */}
        <div className="mb-8 font-sans">
          <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] mb-3 pb-1 border-b border-[var(--color-paper-dark)]">
            I. Key Contractual Facts
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
            {Object.entries(keyFacts).map(([k, v]) => (
              <div key={k} className="p-3 bg-[var(--color-paper)] rounded border border-[var(--color-paper-dark)]">
                <span className="font-mono uppercase text-[var(--color-ink-light)] block mb-1">
                  {k.replace(/_/g, ' ')}
                </span>
                <span className="font-semibold text-[var(--color-ink)]">
                  {String(v) || 'Not specified'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Section 2: High Risk Clauses */}
        <div className="mb-8 font-sans">
          <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-vermilion)] mb-3 pb-1 border-b border-[var(--color-vermilion)] flex items-center justify-between">
            <span>II. Critical Red Flags Requiring Legal Counsel</span>
            <span className="text-[11px] font-mono">({highRiskFindings.length} High-Risk Findings)</span>
          </h3>

          <div className="space-y-4">
            {highRiskFindings.map((f, i) => (
              <div
                key={i}
                className="p-4 rounded border-l-4 border-[var(--color-vermilion)] bg-[var(--color-vermilion-bg)] text-xs"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono font-bold text-[var(--color-vermilion)]">
                    Clause {f.ordinal}: {f.heading || f.clause_type}
                  </span>
                  <span className="verified-badge">✓ Verified Quote</span>
                </div>
                <p className="font-medium text-[var(--color-ink)] mb-1 text-sm font-serif">
                  {f.what_it_means}
                </p>
                {f.evidence_quote && (
                  <blockquote className="italic text-[var(--color-ink-faded)] pl-3 border-l-2 border-[var(--color-vermilion-light)] my-2">
                    "{f.evidence_quote}"
                  </blockquote>
                )}
                {f.risk_reasons.length > 0 && (
                  <ul className="text-[var(--color-ink-faded)] space-y-0.5 mt-1">
                    {f.risk_reasons.map((r, ri) => (
                      <li key={ri}>• {r}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Section 3: Missing Clauses */}
        {analysis.missing_clauses.length > 0 && (
          <div className="mb-8 font-sans">
            <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-turmeric)] mb-3 pb-1 border-b border-[var(--color-turmeric)]">
              III. Missing Protections (Standard Clauses Omitted)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              {analysis.missing_clauses.map((mc, idx) => (
                <div key={idx} className="p-3 bg-amber-50/50 rounded border border-amber-200">
                  <span className="font-semibold text-amber-900 block">{mc.name}</span>
                  <p className="text-[var(--color-ink-faded)] mt-0.5">{mc.why_it_matters}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Section 4: 10 Prioritized Questions for the Lawyer */}
        <div className="mb-8 font-sans">
          <h3 className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] mb-3 pb-1 border-b border-[var(--color-paper-dark)]">
            IV. 10 Prioritized Questions for Your Attorney Consultation
          </h3>
          <ol className="space-y-2 text-xs text-[var(--color-ink)] font-serif">
            {prioritizedQuestions.map((q, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="font-mono font-bold text-[var(--color-ink-light)] w-6 flex-shrink-0">
                  {idx + 1}.
                </span>
                <span>{q}</span>
              </li>
            ))}
          </ol>
        </div>

        {/* Section 5: Documents to Bring Checklist */}
        <div className="p-5 bg-[var(--color-paper)] rounded border border-[var(--color-paper-dark)] font-sans text-xs">
          <h4 className="font-semibold uppercase tracking-wider text-[var(--color-ink)] mb-2 font-mono">
            V. Checklist: What to Bring to Your Lawyer
          </h4>
          <ul className="space-y-1.5 text-[var(--color-ink-faded)]">
            {CHECKLIST_ITEMS.map((item, idx) => (
              <li key={idx} className="flex items-center gap-2">
                <input type="checkbox" className="rounded text-[var(--color-ink)]" readOnly checked={false} />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
