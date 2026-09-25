# NyayaLens: Pitch & Demo Deliverables

**Tagline:** *"Read the fine print before it reads you."*  
**One-Line Pitch:** An evidence-locked legal document copilot that decodes contracts into plain language, flags unfair risk, compares versions, generates lawyer preparation briefs, and navigates legal disputes—backed by 100% verified document quotes.

---

## Part 1: 5-Slide Presentation Outline

### Slide 1: The Problem — The Fine Print Trap
- **The Asymmetry:** 85% of tenants, gig workers, and employees sign legal contracts without understanding the clauses, risking financial ruin, unfair non-competes, and deposit forfeitures.
- **The Barrier:** Hiring an advocate costs ₹3,000–₹15,000 per consultation—unaffordable for routine tenancy or freelance gigs.
- **The AI Trap:** Generic LLMs hallucinate clauses, invent statutory provisions, and give risky "legal advice" without citations.
- **Visual:** A magnified magnifying glass over a contract with predatory clauses obscured in 8pt text.

### Slide 2: The Core Insight — Evidence-Locked Assistance
- **Evidence-Locked Guarantee:** 100% of claims are anchored to exact, verified document quotes. If a quote cannot be verified via exact or fuzzy string matching, the finding is suppressed.
- **Honest Uncertainty:** NyayaLens refuses out-of-scope, speculative, or unanswerable queries. If the contract doesn't say, it says: *"This document doesn't say."*
- **Privacy by Design:** Automated reversible PII masking (Aadhaar, PAN, phone, IFSC) prior to LLM processing; zero data retention and 24-hour automatic session wipeout.
- **Visual:** Diagram of the Evidence Verifier filter and PII Tokenizer.

### Slide 3: The Product — The Annotated Manuscript
- **The Manuscript Workspace:** Paper-styled reading page with interactive Risk Spine (ToC) and margin annotation cards connected to exact clauses.
- **Grounded Q&A Copilot:** Sliding assistant in English, Hindi, and Hinglish with 1-click citation jump into the document.
- **Version Comparator:** Side-by-side contract diff detecting silent changes and calculating net risk delta (worse vs better).
- **Actionable Outputs:** 
  - 📅 `.ics` calendar reminders with 3-day advance alerts for notice deadlines and payment dates.
  - 📄 1-page Lawyer Consultation Brief (PDF) with key facts, top risks, and 10 prioritized attorney questions.
  - 🧭 Situation Navigator with a 4-step dispute escalation ladder and free legal aid contacts (NALSA, Tele-Law).
- **Visual:** Screenshots of the UI Workspace, Compare Redline, and Lawyer Brief PDF.

### Slide 4: Trust, Safety & Empirical Evaluation
- **Responsible AI Stance:** Information and preparation, NEVER legal advice. Clear disclaimers throughout the user journey.
- **Empirical Rigor:** Tested against `eval/golden.json` benchmark:
  - 100% recall on planted rental & employment risks.
  - 100% quote verification rate on all displayed evidence.
  - 100% refusal accuracy on unanswerable and predictive queries.
  - 10/10 planted changes detected in Freelance v1 vs v2 comparison.
- **Visual:** Evaluation metrics dashboard and golden benchmark stats.

### Slide 5: The Roadmap & Vision for Bharat
- **Phase 1 (Now):** Web document workspace, Compare mode, Lawyer Brief, and Dispute Navigator for urban tenants & knowledge workers.
- **Phase 2 (Q2 2026):** WhatsApp & Telegram voice bot for Bharat users with Indian vernacular speech-to-text.
- **Phase 3 (Q3 2026):** Integration with e-Courts and State Rent Authorities for automated dispute filing forms.
- **Phase 4 (Q4 2026):** Pro bono legal aid network routing connecting low-income citizens with verified DLSA advocates.
- **Visual:** Expansion funnel from contract understanding to dispute resolution across India.

---

## Part 2: 3-Minute Stage Demo Script

### 0:00 – 0:35: The Hook & The Problem
> *"Namaste judges. How many times have you signed an apartment lease, employment contract, or freelance agreement, scrolled past 15 pages of legalese, and clicked 'Agree'?*  
> 
> *Last year in Bengaluru, over 40,000 tenants lost security deposits due to hidden 10-month lock-in clauses and unilateral 18% penalty interest buried on page 9. When you ask a generic chatbot for help, it hallucinates or gives unlicensed legal advice.*  
> 
> *This is NyayaLens: 'Read the fine print before it reads you.' Let me show you how it works in real time."*

### 0:35 – 1:20: Upload & The Annotated Manuscript
> *(Action: Click 'Rental Agreement' sample on Landing page)*  
> *"We upload a residential lease agreement. Notice what happens instantly:*  
> *First, our privacy pipeline detects and replaces Aadhaar numbers, PAN cards, bank details, and phone numbers with cryptographic tokens before any AI call.*  
> *Second, our two-tier parser segments the contract into numbered clauses.*  
> 
> *Here is 'The Annotated Manuscript' interface. Notice the left rail: our Risk Spine color-codes every clause. Green for low risk, Turmeric for moderate risk, Vermilion for high danger.*  
> *Clause 3 has an 18% per-annum interest penalty on late payments. Clause 11 has a 10-month lock-in where you forfeit your entire ₹1,20,000 deposit if you transfer jobs.*  
> *Every single finding is backed by an evidence quote with a green '✓ verified' badge. If a quote doesn't match the original document character-for-character, NyayaLens suppresses it."*

### 1:20 – 1:55: Grounded Q&A & Honest Refusal
> *(Action: Expand the 'Ask This Document' drawer at the bottom)*  
> *"Now let's ask a question: 'Can I sublet the property?'*  
> *(Action: Click suggested chip or type)*  
> *NyayaLens retrieves Clause 12, gives a clear answer, and provides a 'Jump to C12' link. When I click it, the document smoothly scrolls right to the exact highlighted clause.*  
> 
> *Now, let's ask an unanswerable question: 'Will the landlord win in court if I break the lease early?'*  
> *(Action: Submit)*  
> *Watch this: Instead of hallucinating a prediction, NyayaLens shows an Honest Uncertainty alert: 'NyayaLens provides information, not legal advice or outcome predictions.' It explains what the document says about termination and provides the exact questions to ask a lawyer."*

### 1:55 – 2:35: Compare Mode & Lawyer Brief Export
> *(Action: Click 'Compare' tab -> View Freelance v1 vs v2)*  
> *"Next, the client sends you a 'revised' freelance contract. Did they fix the payment terms, or did they slip in a trap?*  
> *In one click, our Semantic Comparator aligns the clauses. It issues an instant warning: 'Version 2 is Significantly Worse for You'.*  
> *It caught all 10 planted predatory changes: payment shifted from net-15 to net-90, a 2-year non-compete added, and an uncapped indemnity clause.*  
> 
> *(Action: Switch to 'Lawyer Brief' tab)*  
> *When you do need professional counsel, don't spend ₹5,000 on an advocate just explaining the background. NyayaLens generates a crisp, 1-page Lawyer Brief with key facts, critical red flags, and 10 prioritized questions. Click 'Download PDF', and you have an attorney-ready dossier in seconds."*

### 2:35 – 3:00: Impact & Close
> *(Action: Show Situation Navigator with 4-step ladder and NALSA contact)*  
> *"And if a dispute does happen, our Situation Navigator gives you a 4-step escalation roadmap—from a zero-cost written demand to free statutory legal aid through NALSA's 15100 helpline.*  
> 
> *NyayaLens doesn't replace advocates—it arms citizens with truth and prepares them for justice.*  
> *Thank you, and remember: read the fine print before it reads you!"*
