import React, { useCallback, useState } from 'react';
import { useStore } from '../store';

const SAMPLE_DOCS = [
  { name: 'Rental Agreement', file: 'rental_agreement.txt', desc: 'Residential lease with 10-month lock-in and 18% penalty' },
  { name: 'Employment Offer', file: 'employment_offer.txt', desc: 'Job offer with 2-year non-compete and weekend IP claim' },
  { name: 'Freelance Agreement (v2)', file: 'freelance_v2.txt', desc: 'Aggressive client agreement with net-90 and broad indemnity' },
];

export function Landing() {
  const { uploadDocument, uploadText, isUploading, loadSampleCompare, setView } = useStore();
  const [dragActive, setDragActive] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [showPaste, setShowPaste] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) uploadDocument(file);
  }, [uploadDocument]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadDocument(file);
  }, [uploadDocument]);

  const handleSampleClick = useCallback(async (filename: string) => {
    try {
      const resp = await fetch(`/samples/${filename}`);
      const text = await resp.text();
      await uploadText(text);
    } catch {
      useStore.setState({ error: 'Sample file not found. Upload your own document.' });
    }
  }, [uploadText]);

  return (
    <div className="landing-gradient min-h-screen">
      <div className="max-w-4xl mx-auto px-6 pt-20 pb-16">
        {/* Hero */}
        <div className="text-center mb-12">
          <h1
            className="text-5xl md:text-6xl font-bold mb-4 tracking-tight"
            style={{ fontFamily: 'var(--font-serif)', letterSpacing: '-0.03em' }}
          >
            Read the fine print
            <br />
            <span className="text-[var(--color-vermilion)]">before it reads you.</span>
          </h1>
          <p
            className="text-lg text-[var(--color-ink-faded)] max-w-xl mx-auto"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            An evidence-locked legal copilot for tenants, employees, and freelancers.
            Decodes contracts into plain language, flags risks with 100% verified quotes, compares versions, and prepares you for a lawyer consultation.
          </p>
          <span className="disclaimer-badge mt-4 inline-flex">
            ⚖️ Information, not legal advice. NyayaLens does not replace a lawyer.
          </span>
        </div>

        {/* Upload Zone */}
        <div
          className={`upload-zone mb-6 ${dragActive ? 'active' : ''} ${isUploading ? 'opacity-60 pointer-events-none' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
          onDragLeave={() => setDragActive(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
          role="button"
          tabIndex={0}
          aria-label="Upload a document by clicking or dragging"
          onKeyDown={(e) => { if (e.key === 'Enter') document.getElementById('file-input')?.click(); }}
        >
          <input
            id="file-input"
            type="file"
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg"
            className="hidden"
            onChange={handleFileSelect}
          />
          {isUploading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-8 h-8 border-2 border-[var(--color-ink)] border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-[var(--color-ink-faded)]" style={{ fontFamily: 'var(--font-sans)' }}>
                Segmenting clauses & redacting PII...
              </span>
            </div>
          ) : (
            <>
              <div className="text-3xl mb-3">📄</div>
              <p className="text-base font-medium mb-1">
                Drop your contract here, or click to browse
              </p>
              <p className="text-sm text-[var(--color-ink-light)]" style={{ fontFamily: 'var(--font-sans)' }}>
                PDF, DOCX, scan/image, or text file — processed in your isolated session
              </p>
            </>
          )}
        </div>

        {/* Or paste text */}
        <div className="text-center mb-10">
          <button
            onClick={() => setShowPaste(!showPaste)}
            className="text-sm text-[var(--color-ink-faded)] underline hover:text-[var(--color-ink)] transition-colors"
            style={{ fontFamily: 'var(--font-sans)' }}
          >
            {showPaste ? 'Hide text paste' : 'Or paste contract text directly'}
          </button>
          {showPaste && (
            <div className="mt-4 max-w-xl mx-auto">
              <textarea
                value={pasteText}
                onChange={(e) => setPasteText(e.target.value)}
                placeholder="Paste your agreement clauses here..."
                className="w-full h-40 p-4 border border-[var(--color-paper-dark)] rounded-lg bg-white text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[var(--color-turmeric)]"
                style={{ fontFamily: 'var(--font-serif)' }}
              />
              <button
                onClick={() => { if (pasteText.trim()) uploadText(pasteText); }}
                disabled={!pasteText.trim() || isUploading}
                className="mt-2 px-6 py-2 bg-[var(--color-ink)] text-[var(--color-paper)] rounded text-sm font-medium disabled:opacity-40 hover:bg-[var(--color-ink-faded)] transition-colors"
                style={{ fontFamily: 'var(--font-sans)' }}
              >
                Analyze Pasted Text
              </button>
            </div>
          )}
        </div>

        {/* Sample Documents */}
        <div className="mb-8">
          <h2
            className="text-xs font-mono uppercase tracking-widest text-[var(--color-ink-light)] text-center mb-4"
          >
            Explore Pre-Computed Samples
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {SAMPLE_DOCS.map((sample) => (
              <button
                key={sample.file}
                onClick={() => handleSampleClick(sample.file)}
                className="text-left p-5 bg-white border border-[var(--color-paper-dark)] rounded-lg hover:border-[var(--color-ink-light)] hover:shadow-sm transition-all group"
              >
                <div className="text-base font-semibold mb-1 group-hover:text-[var(--color-vermilion)] transition-colors" style={{ fontFamily: 'var(--font-serif)' }}>
                  {sample.name}
                </div>
                <div className="text-xs text-[var(--color-ink-light)] mb-3" style={{ fontFamily: 'var(--font-sans)' }}>
                  {sample.desc}
                </div>
                <div className="demo-badge">Instant Demo</div>
              </button>
            ))}
          </div>
        </div>

        {/* Feature Highlights / Quick Demos */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-10 font-sans">
          <div className="p-5 bg-white border border-[var(--color-paper-dark)] rounded-lg shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">⚖️</span>
                <h3 className="font-serif font-bold text-base text-[var(--color-ink)]">
                  Compare Two Contracts (v1 vs v2)
                </h3>
              </div>
              <p className="text-xs text-[var(--color-ink-faded)] mb-4 leading-relaxed">
                See side-by-side redlines with 10 planted changes detected in our Freelance benchmark. Evaluates whether revised drafts make conditions worse for you.
              </p>
            </div>
            <button
              onClick={loadSampleCompare}
              className="py-2 px-4 rounded bg-[var(--color-paper)] border border-[var(--color-paper-dark)] hover:border-[var(--color-ink)] text-xs font-mono font-medium text-[var(--color-ink)] transition-colors text-center"
            >
              Launch Compare Benchmark Demo →
            </button>
          </div>

          <div className="p-5 bg-white border border-[var(--color-paper-dark)] rounded-lg shadow-sm flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">🧭</span>
                <h3 className="font-serif font-bold text-base text-[var(--color-ink)]">
                  Dispute Situation Navigator
                </h3>
              </div>
              <p className="text-xs text-[var(--color-ink-faded)] mb-4 leading-relaxed">
                Facing a security deposit dispute, unpaid freelance invoice, or notice buyout? Get a 4-step calibrated escalation ladder with free legal aid contacts.
              </p>
            </div>
            <button
              onClick={() => setView('navigator')}
              className="py-2 px-4 rounded bg-[var(--color-paper)] border border-[var(--color-paper-dark)] hover:border-[var(--color-ink)] text-xs font-mono font-medium text-[var(--color-ink)] transition-colors text-center"
            >
              Open Dispute Navigator →
            </button>
          </div>
        </div>

        {/* Language & Settings Footer */}
        <div className="flex flex-wrap justify-center gap-6 text-sm text-[var(--color-ink-faded)] font-sans border-t border-[var(--color-paper-dark)] pt-6">
          <label className="flex items-center gap-2">
            Language:
            <select
              value={useStore.getState().language}
              onChange={(e) => useStore.getState().setLanguage(e.target.value)}
              className="bg-white border border-[var(--color-paper-dark)] rounded px-2.5 py-1 text-xs"
            >
              <option value="en">English</option>
              <option value="hi">हिन्दी (Hindi)</option>
              <option value="hinglish">Hinglish</option>
            </select>
          </label>
          <label className="flex items-center gap-2">
            Explanation Level:
            <select
              value={useStore.getState().readingLevel}
              onChange={(e) => useStore.getState().setReadingLevel(e.target.value)}
              className="bg-white border border-[var(--color-paper-dark)] rounded px-2.5 py-1 text-xs"
            >
              <option value="simple">Simple (Plain talk)</option>
              <option value="standard">Standard (Balanced)</option>
              <option value="detailed">Detailed (Legal nuances)</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  );
}
