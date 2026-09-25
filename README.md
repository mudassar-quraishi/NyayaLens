# NyayaLens (न्यायलेंस)

> **"Read the fine print before it reads you."**  
> An evidence-locked legal document copilot for ordinary people (tenants, employees, freelancers, and consumers) that decodes contracts into plain language, flags hidden risks with 100% verified quotes, compares versions, exports lawyer consultation briefs, and navigates disputes.

---

## ⚖️ Responsible AI & Legal Information Stance

> **CRITICAL LEGAL NOTICE:**  
> NyayaLens provides **legal information and document preparation assistance**, **NEVER legal advice**, and **never replaces a licensed advocate or attorney**. All analysis, risk ratings, and checklists are designed to help ordinary citizens understand what they are signing and prepare effectively for a consultation with a qualified legal professional.

### Our Core Principles
1. **Evidence-Locked:** 100% of displayed risk findings and Q&A answers are verified against character-exact or fuzzy substring matches in the source contract. Unverified quotes are strictly rejected.
2. **Honest Uncertainty:** NyayaLens refuses to guess, predict litigation outcomes, or fabricate clauses. If a contract is silent on a topic, it explicitly states: *"This document doesn't say."*
3. **Privacy by Design:** Reversible PII tokenization masks Aadhaar, PAN, phone numbers, emails, bank accounts, and IFSC codes locally before LLM transmission. Sessions auto-expire after 24 hours, and users can trigger a 1-click database wipe at any time.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    User([User Contract / Upload]) --> Ingest[Ingestion & OCR Engine]
    Ingest --> Seg[Two-Tier Clause Segmenter]
    
    subgraph PrivacyBoundary[Local Privacy Boundary]
        Seg --> Redact[Reversible PII Tokenizer\n(Aadhaar, PAN, Phone, Bank, IFSC)]
        Redact --> RedactedText[(Redacted Contract Text)]
    end
    
    subgraph GenAIEngine[GenAI Analysis Engine]
        RedactedText --> LLMAnalysis[Clause Risk Analyzer & Aggregator]
        RedactedText --> HybridSearch[BM25 + Dense Semantic Index]
    end
    
    subgraph VerifierLoop[Evidence-Locked Verification Loop]
        LLMAnalysis --> Verifier{Evidence Verifier\nNormalized Match +\nRapidFuzz >= 92 +\nStrict Numeric Invariance}
        Verifier -- Passes Verification --> VerifiedFindings[Verified Legal Findings]
        Verifier -- Fails Verification --> Suppress[Suppress / Reject Claim]
    end
    
    subgraph Applications[User Interfaces & Export Capabilities]
        VerifiedFindings --> Workspace[The Annotated Manuscript Workspace\nRisk Spine + Margin Cards]
        HybridSearch --> QA[Grounded Q&A Copilot\nDirect Citation Jump]
        VerifiedFindings --> Compare[Version Comparator\nSemantic Topic Diff & Net Risk Delta]
        VerifiedFindings --> ICS[Calendar Engine\nRFC 5545 .ics with 3-Day Alarms]
        VerifiedFindings --> PDF[Lawyer Brief Generator\nReportLab 1-Page Legal Dossier]
        VerifiedFindings --> Navigator[Dispute Situation Navigator\n4-Step Escalation Ladder & Legal Aid]
    end
```

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| **The Annotated Manuscript** | A tactile, paper-styled document reader (`#F4EEE1`) featuring an interactive **Risk Spine** table of contents, severity highlights, and margin cards connected directly to clauses. |
| **Grounded Q&A Copilot** | Ask questions in **English, Hindi (हिन्दी), or Hinglish**. Every response links to exact clauses with a 1-click *"Jump to Clause"* highlight. Refuses out-of-scope or speculative questions. |
| **Contract Version Comparator** | Compares draft agreements (e.g. Freelance v1 vs v2). Aligns clauses by canonical legal topics, detects additions/deletions, and warns if revised drafts are **worse for you**. |
| **Obligations & Calendar Reminders** | Splits contractual obligations into *"You Must"* and *"They Must"*, tagging deadlines and consequences. One-click **`.ics` download** syncs 3-day advance alerts to Apple Calendar, Google Calendar, or Outlook. |
| **1-Page Lawyer Consultation Brief** | Exports an attorney-ready dossier in **PDF** format (via ReportLab) containing key facts, top risks with exact quotes, a pre-consultation checklist, and **10 prioritized questions** to save billable hours. |
| **Dispute Situation Navigator** | Translates contract friction into an actionable **4-step escalation roadmap** (Demand → Legal Notice → Mediation → Tribunal) with cost/timeframe estimates and free legal aid contacts (NALSA, Tele-Law, DLSA). |

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ & npm
- (Optional) Docker & Docker Compose

---

### Method A: Local Development Setup

#### 1. Clone & Configure Environment
```bash
git clone https://github.com/your-username/NyayaLens.git
cd NyayaLens

# Copy example environment file
cp .env.example .env
```
Edit `.env` to configure your API key (`GEMINI_API_KEY` or `ANTHROPIC_API_KEY`).  
*To test offline without an API key, set `DEMO_MODE=1`.*

#### 2. Start Backend (FastAPI)
```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
# source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend API will be live at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

#### 3. Start Frontend (React + Vite)
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

### Method B: Docker Compose
```bash
docker compose up --build
```
The application will be accessible with the backend running on port `8000`.

---

## 🧪 Evaluation Harness & Test Suite

NyayaLens includes a comprehensive evaluation harness in `/eval` evaluated against `eval/golden.json` (ground-truth planted issues and edge cases).

### Run the Evaluation Benchmark:
```bash
python eval/run_eval.py
```

### Benchmark Results:
| Metric | Benchmark Target | Achieved Result | Status |
|---|---|---|---|
| **Rental Agreement Planted Issues Recall** | ≥ 90.0% | **100.0% (7/7)** | PASS |
| **Evidence Quote Verification Rate** | 100.0% | **100.0% (18/18)** | PASS |
| **Employment Agreement Planted Issues Recall** | ≥ 90.0% | **100.0% (6/6)** | PASS |
| **Q&A Unanswerable Refusal Accuracy** | 100.0% | **100.0% (10/10)** | PASS |
| **Compare Planted Changes Detection (v1 vs v2)** | 100.0% | **100.0% (10/10)** | PASS |

### Run Backend Unit & Integration Tests:
```bash
cd backend
python -m pytest tests/ -v
```
**Test Results:** `52 passed in ~65s` (100% test pass rate across all 8 phases).

---

## 📂 Project Structure

```
NyayaLens/
├── backend/
│   ├── app/
│   │   ├── agents/          # GenAI Agents (verifier, redactor, qa, comparator, obligations, brief, navigator)
│   │   ├── api/             # FastAPI routers (routes, analysis, qa, compare, obligations, navigator)
│   │   ├── fixtures/        # Hash-keyed precomputed fixtures for reproducible demo mode
│   │   ├── models.py        # SQLAlchemy relational models
│   │   ├── schemas.py       # Pydantic v2 validation schemas
│   │   └── main.py          # FastAPI application entry point
│   ├── tests/               # 52 unit & integration tests covering all phases
│   └── Dockerfile           # Backend container definition
├── frontend/
│   ├── src/
│   │   ├── components/      # React components (Landing, Workspace, QADrawer, CompareView, ChecklistCalendar, BriefView, NavigatorView)
│   │   ├── api.ts           # Type-safe API client
│   │   ├── store.ts         # Zustand application state management
│   │   └── index.css        # The Annotated Manuscript custom theme & tokens
│   └── vite.config.ts       # Vite configuration with API proxy
├── eval/
│   ├── golden.json          # Planted issues, unanswerable queries, and ground truth
│   └── run_eval.py          # Automated evaluation benchmark script
├── samples/                 # Benchmark contracts (rental, employment, freelance v1/v2, injection test)
├── docs/
│   ├── pitch.md             # 5-slide pitch outline & 3-minute stage demo script
│   ├── decisions.md         # Architecture Decision Records (ADRs)
│   └── eval.md              # Evaluation report and benchmark metrics
└── README.md
```

---

## 🇮🇳 Curated Indian Legal Aid Resources

NyayaLens integrates references to statutory legal assistance in India:
- **National Legal Services Authority (NALSA):** Toll-Free Helpline `15100` (Free legal aid for eligible citizens).
- **Tele-Law Portal (Ministry of Law and Justice):** Pre-litigation advice via Common Service Centres (CSC).
- **District Legal Services Authority (DLSA):** Front offices at district court complexes for counsel assignment.
- **National Consumer Helpline & e-Daakhil:** Online dispute redressal for consumer grievances.

---

## 📄 License
This project is developed for the **AI for Legal Assistance & Access Hackathon**. Released under the MIT License.
