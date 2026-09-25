/* Zustand store for NyayaLens state management */

import { create } from 'zustand';
import {
  api,
  type Session,
  type AnalysisResult,
  type DocumentUploadResponse,
  type QAMessageItem,
  type CompareResult,
  type ObligationsResponse,
  type NavigatorResponse,
} from './api';

export type AppView = 'landing' | 'workspace' | 'compare' | 'checklist' | 'brief' | 'navigator' | 'privacy';

interface AppState {
  // Session
  session: Session | null;
  language: string;
  readingLevel: string;

  // Documents
  currentDoc: DocumentUploadResponse | null;
  analysis: AnalysisResult | null;
  isUploading: boolean;
  isAnalyzing: boolean;
  error: string | null;

  // UI state
  activeClause: number | null;
  view: AppView;

  // Q&A state
  qaHistory: QAMessageItem[];
  isQALoading: boolean;
  qaOpen: boolean;

  // Compare state
  compareResult: CompareResult | null;
  isComparing: boolean;
  compareDocAId: string | null;
  compareDocBId: string | null;

  // Obligations state
  obligations: ObligationsResponse | null;
  isLoadingObligations: boolean;

  // Navigator state
  navigatorResult: NavigatorResponse | null;
  isNavigating: boolean;

  // Actions
  setLanguage: (lang: string) => void;
  setReadingLevel: (level: string) => void;
  setActiveClause: (ordinal: number | null) => void;
  setView: (view: AppView) => void;
  setQAOpen: (open: boolean) => void;
  initSession: () => Promise<void>;
  uploadDocument: (file: File) => Promise<void>;
  uploadText: (text: string) => Promise<void>;
  triggerAnalysis: () => Promise<void>;
  pollAnalysis: () => Promise<void>;
  deleteSession: () => Promise<void>;
  reset: () => void;

  // Q&A actions
  askQuestion: (question: string) => Promise<void>;
  loadQAHistory: () => Promise<void>;

  // Compare actions
  runCompare: (docAId: string, docBId: string) => Promise<void>;
  loadSampleCompare: () => Promise<void>;

  // Obligations actions
  loadObligations: () => Promise<void>;

  // Navigator actions
  submitSituation: (situation: string) => Promise<void>;
}

export const useStore = create<AppState>((set, get) => ({
  // Initial state
  session: null,
  language: 'en',
  readingLevel: 'standard',
  currentDoc: null,
  analysis: null,
  isUploading: false,
  isAnalyzing: false,
  error: null,
  activeClause: null,
  view: 'landing',

  qaHistory: [],
  isQALoading: false,
  qaOpen: false,

  compareResult: null,
  isComparing: false,
  compareDocAId: null,
  compareDocBId: null,

  obligations: null,
  isLoadingObligations: false,

  navigatorResult: null,
  isNavigating: false,

  // Actions
  setLanguage: (lang) => set({ language: lang }),
  setReadingLevel: (level) => set({ readingLevel: level }),
  setActiveClause: (ordinal) => set({ activeClause: ordinal }),
  setView: (view) => set({ view }),
  setQAOpen: (open) => set({ qaOpen: open }),

  initSession: async () => {
    try {
      const { language, readingLevel } = get();
      const session = await api.createSession(language, readingLevel);
      set({ session, error: null });
    } catch (e) {
      set({ error: `Failed to create session: ${e}` });
    }
  },

  uploadDocument: async (file) => {
    let s = get().session;
    if (!s) {
      await get().initSession();
      s = get().session;
    }
    if (!s) return;

    set({ isUploading: true, error: null });
    try {
      const doc = await api.uploadDocument(s.id, file);
      set({ currentDoc: doc, isUploading: false, view: 'workspace', qaHistory: [], obligations: null });
    } catch (e) {
      set({ isUploading: false, error: `Upload failed: ${e}` });
    }
  },

  uploadText: async (text) => {
    let s = get().session;
    if (!s) {
      await get().initSession();
      s = get().session;
    }
    if (!s) return;

    set({ isUploading: true, error: null });
    try {
      const doc = await api.uploadText(s.id, text);
      set({ currentDoc: doc, isUploading: false, view: 'workspace', qaHistory: [], obligations: null });
    } catch (e) {
      set({ isUploading: false, error: `Upload failed: ${e}` });
    }
  },

  triggerAnalysis: async () => {
    const { currentDoc } = get();
    if (!currentDoc) return;

    set({ isAnalyzing: true, error: null });
    try {
      await api.triggerAnalysis(currentDoc.id);
      get().pollAnalysis();
    } catch (e) {
      set({ isAnalyzing: false, error: `Analysis failed: ${e}` });
    }
  },

  pollAnalysis: async () => {
    const { currentDoc } = get();
    if (!currentDoc) return;

    const poll = async () => {
      try {
        const result = await api.getAnalysis(currentDoc.id);
        if (result.status === 'analyzed') {
          set({ analysis: result, isAnalyzing: false });
        } else if (result.status === 'error') {
          set({ isAnalyzing: false, error: 'Analysis failed. Please try again.' });
        } else {
          setTimeout(poll, 1500);
        }
      } catch (e) {
        set({ isAnalyzing: false, error: `Failed to fetch analysis: ${e}` });
      }
    };
    poll();
  },

  deleteSession: async () => {
    const { session } = get();
    if (session) {
      try {
        await api.deleteSession(session.id);
      } catch (_) {
        // ignore
      }
    }
    get().reset();
  },

  reset: () => set({
    session: null,
    currentDoc: null,
    analysis: null,
    isUploading: false,
    isAnalyzing: false,
    error: null,
    activeClause: null,
    view: 'landing',
    qaHistory: [],
    isQALoading: false,
    qaOpen: false,
    compareResult: null,
    isComparing: false,
    compareDocAId: null,
    compareDocBId: null,
    obligations: null,
    isLoadingObligations: false,
    navigatorResult: null,
    isNavigating: false,
  }),

  // Q&A actions
  askQuestion: async (question: string) => {
    const { session, currentDoc, qaHistory } = get();
    if (!session || !currentDoc) return;

    set({ isQALoading: true, error: null });
    // optimistic user message
    const tempUserMsg: QAMessageItem = {
      id: `tmp-${Date.now()}`,
      role: 'user',
      content: question,
      citations: [],
      grounded: true,
      created_at: new Date().toISOString(),
    };
    set({ qaHistory: [...qaHistory, tempUserMsg] });

    try {
      const resp = await api.askQuestion(session.id, [currentDoc.id], question);
      const asstMsg: QAMessageItem = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: resp.answer,
        citations: resp.citations,
        grounded: resp.grounded,
        created_at: new Date().toISOString(),
      };
      set({
        qaHistory: [...get().qaHistory, asstMsg],
        isQALoading: false,
      });
    } catch (e) {
      set({
        isQALoading: false,
        error: `Q&A error: ${e}`,
      });
    }
  },

  loadQAHistory: async () => {
    const { session } = get();
    if (!session) return;
    try {
      const history = await api.getQAHistory(session.id);
      set({ qaHistory: history });
    } catch (_) {
      // ignore
    }
  },

  // Compare actions
  runCompare: async (docAId: string, docBId: string) => {
    set({ isComparing: true, error: null, compareDocAId: docAId, compareDocBId: docBId });
    try {
      const resp = await api.compareDocuments(docAId, docBId);
      set({ compareResult: resp.result, isComparing: false, view: 'compare' });
    } catch (e) {
      set({ isComparing: false, error: `Comparison failed: ${e}` });
    }
  },

  loadSampleCompare: async () => {
    let s = get().session;
    if (!s) {
      await get().initSession();
      s = get().session;
    }
    if (!s) return;

    set({ isComparing: true, error: null });
    try {
      // Fetch sample texts for freelance_v1 and freelance_v2
      const [v1Resp, v2Resp] = await Promise.all([
        fetch('/samples/freelance_v1.txt'),
        fetch('/samples/freelance_v2.txt'),
      ]);
      const [v1Text, v2Text] = await Promise.all([v1Resp.text(), v2Resp.text()]);

      const docA = await api.uploadText(s.id, v1Text, 'freelance_v1.txt');
      const docB = await api.uploadText(s.id, v2Text, 'freelance_v2.txt');

      const compResp = await api.compareDocuments(docA.id, docB.id);
      set({
        currentDoc: docB,
        compareDocAId: docA.id,
        compareDocBId: docB.id,
        compareResult: compResp.result,
        isComparing: false,
        view: 'compare',
      });
    } catch (e) {
      set({ isComparing: false, error: `Failed to load freelance comparison sample: ${e}` });
    }
  },

  // Obligations
  loadObligations: async () => {
    const { currentDoc } = get();
    if (!currentDoc) return;
    set({ isLoadingObligations: true, error: null });
    try {
      const data = await api.getObligations(currentDoc.id);
      set({ obligations: data, isLoadingObligations: false });
    } catch (e) {
      set({ isLoadingObligations: false, error: `Failed to load obligations: ${e}` });
    }
  },

  // Navigator
  submitSituation: async (situation: string) => {
    const { currentDoc, analysis } = get();
    set({ isNavigating: true, error: null });
    try {
      const docContext = analysis?.clauses.map(c => `[C${c.clause.ordinal}] ${c.clause.text}`).join('\n') || '';
      const docType = analysis?.doc_type || 'general';
      const result = await api.navigateSituation(situation, docContext, docType);
      set({ navigatorResult: result, isNavigating: false, view: 'navigator' });
    } catch (e) {
      set({ isNavigating: false, error: `Situation navigator failed: ${e}` });
    }
  },
}));
