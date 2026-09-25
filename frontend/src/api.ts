const API_ROOT = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const BASE = API_ROOT ? `${API_ROOT}/api` : '/api';

export interface Session {
  id: string;
  language: string;
  reading_level: string;
  created_at: string;
  expires_at: string;
}

export interface DocumentUploadResponse {
  id: string;
  session_id: string;
  filename: string;
  status: string;
  clause_count: number;
}

export interface ClauseData {
  id: string;
  ordinal: number;
  heading: string;
  text: string;
  char_start: number;
  char_end: number;
  page: number;
}

export interface FindingData {
  id: string;
  clause_type: string;
  plain_text: string;
  what_it_means: string;
  risk_level: 'low' | 'medium' | 'high';
  risk_reasons: string[];
  favors: string;
  questions: string[];
  needs_review: boolean;
  confidence: number;
  evidence_quote: string;
  verified: boolean;
  verification_method: string | null;
}

export interface ClauseWithFindings {
  clause: ClauseData;
  findings: FindingData[];
}

export interface MissingClause {
  name: string;
  why_it_matters: string;
  severity: string;
}

export interface RiskBreakdown {
  [key: string]: {
    score: number;
    max: number;
    detail: string;
  };
}

export interface AnalysisResult {
  document_id: string;
  doc_type: string;
  status: string;
  key_facts: Record<string, unknown>;
  clauses: ClauseWithFindings[];
  missing_clauses: MissingClause[];
  risk_score: number;
  risk_breakdown: RiskBreakdown;
  top_concerns: string[];
  redaction?: {
    pii_found: Array<{ type: string; token: string }>;
    note: string;
  };
}

export interface QACitation {
  clause_id: string;
  clause_ordinal: number;
  clause_heading: string;
  exact_quote: string;
  verified: boolean;
}

export interface QAResponse {
  answer: string;
  citations: QACitation[];
  grounded: boolean;
  followups: string[];
}

export interface QAMessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: QACitation[];
  grounded: boolean;
  created_at: string | null;
}

export interface ClauseDiffItem {
  topic: string;
  change_type: 'added' | 'removed' | 'modified' | 'unchanged';
  risk_delta: 'better' | 'worse' | 'neutral' | 'none';
  doc_a_clause_ordinal?: number | null;
  doc_b_clause_ordinal?: number | null;
  doc_a_text?: string;
  doc_b_text?: string;
  explanation: string;
  impact_on_user: string;
}

export interface CompareResult {
  summary: string;
  net_risk_delta: 'better' | 'worse' | 'neutral' | 'mixed';
  bottom_line_bullets: string[];
  clause_diffs: ClauseDiffItem[];
  overall_score_a: number;
  overall_score_b: number;
}

export interface CompareResponse {
  id: string;
  doc_a_id: string;
  doc_b_id: string;
  result: CompareResult;
}

export interface ObligationItem {
  id: string;
  party: 'you' | 'other' | 'both';
  action: string;
  due_kind: 'absolute' | 'relative' | 'recurring' | 'conditional' | 'none';
  due_value: string;
  consequence: string;
  evidence_quote: string;
}

export interface ObligationsResponse {
  document_id: string;
  total_count: number;
  obligations: ObligationItem[];
  grouped: {
    you_must: ObligationItem[];
    they_must: ObligationItem[];
    dates_to_remember: ObligationItem[];
  };
}

export interface EscalationStep {
  step_number: number;
  title: string;
  timeframe: string;
  cost_estimate: string;
  action_description: string;
  tips: string[];
}

export interface NavigatorResponse {
  situation_summary: string;
  dispute_category: string;
  urgent_lawyer_needed: boolean;
  urgent_reasons: string[];
  steps: EscalationStep[];
  evidence_needed: string[];
  free_legal_aid: Array<{
    name: string;
    description: string;
    contact: string;
    url?: string;
  }>;
}

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`API error ${resp.status}: ${text}`);
  }
  return resp.json();
}

export const api = {
  async createSession(language = 'en', readingLevel = 'standard'): Promise<Session> {
    const resp = await fetch(`${BASE}/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ language, reading_level: readingLevel }),
    });
    return handleResponse<Session>(resp);
  },

  async deleteSession(sessionId: string): Promise<void> {
    await fetch(`${BASE}/session/${sessionId}`, { method: 'DELETE' });
  },

  async uploadDocument(sessionId: string, file: File): Promise<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    const resp = await fetch(`${BASE}/documents`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DocumentUploadResponse>(resp);
  },

  async uploadText(sessionId: string, text: string, filename = 'pasted.txt'): Promise<DocumentUploadResponse> {
    const blob = new Blob([text], { type: 'text/plain' });
    const file = new File([blob], filename);
    return this.uploadDocument(sessionId, file);
  },

  async triggerAnalysis(docId: string): Promise<{ status: string }> {
    const resp = await fetch(`${BASE}/documents/${docId}/analyze`, { method: 'POST' });
    return handleResponse(resp);
  },

  async getAnalysis(docId: string): Promise<AnalysisResult> {
    const resp = await fetch(`${BASE}/documents/${docId}/analysis`);
    return handleResponse<AnalysisResult>(resp);
  },

  async getClauses(docId: string): Promise<ClauseData[]> {
    const resp = await fetch(`${BASE}/documents/${docId}/clauses`);
    return handleResponse<ClauseData[]>(resp);
  },

  async getDocumentText(docId: string): Promise<{ text: string; content_hash: string }> {
    const resp = await fetch(`${BASE}/documents/${docId}/text`);
    return handleResponse(resp);
  },

  // Phase 4: Grounded Q&A
  async askQuestion(sessionId: string, docIds: string[], question: string): Promise<QAResponse> {
    const resp = await fetch(`${BASE}/qa`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        doc_ids: docIds,
        question,
      }),
    });
    return handleResponse<QAResponse>(resp);
  },

  async getQAHistory(sessionId: string): Promise<QAMessageItem[]> {
    const resp = await fetch(`${BASE}/session/${sessionId}/qa-history`);
    return handleResponse<QAMessageItem[]>(resp);
  },

  // Phase 5: Compare
  async compareDocuments(docAId: string, docBId: string): Promise<CompareResponse> {
    const resp = await fetch(`${BASE}/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ doc_a: docAId, doc_b: docBId }),
    });
    return handleResponse<CompareResponse>(resp);
  },

  async getComparison(compId: string): Promise<CompareResponse> {
    const resp = await fetch(`${BASE}/compare/${compId}`);
    return handleResponse<CompareResponse>(resp);
  },

  // Phase 6: Obligations & Calendar & Brief
  async getObligations(docId: string): Promise<ObligationsResponse> {
    const resp = await fetch(`${BASE}/documents/${docId}/obligations`);
    return handleResponse<ObligationsResponse>(resp);
  },

  getIcsDownloadUrl(docId: string): string {
    return `${BASE}/documents/${docId}/obligations.ics`;
  },

  getBriefPdfUrl(docId: string): string {
    return `${BASE}/documents/${docId}/brief.pdf`;
  },

  // Phase 8: Situation Navigator
  async navigateSituation(situation: string, docContext = '', docType = 'general'): Promise<NavigatorResponse> {
    const resp = await fetch(`${BASE}/navigator`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_situation: situation,
        doc_context: docContext,
        doc_type: docType,
      }),
    });
    return handleResponse<NavigatorResponse>(resp);
  },
};

