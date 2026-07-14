import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";
import type { Question, QuestionFilters, Difficulty } from "@/types";
import { arrayMove } from "@/lib/utils";

interface QuestionsStore {
  questions: Question[];
  filteredQuestions: Question[];
  selectedIds: Set<string>;
  isDirty: boolean;
  lastSaved: Date | null;
  filters: QuestionFilters;

  // Actions
  setQuestions: (questions: Question[]) => void;
  addQuestion: (question: Question) => void;
  updateQuestion: (id: string, updates: Partial<Question>) => void;
  removeQuestion: (id: string) => void;
  duplicateQuestion: (id: string) => void;
  reorderQuestions: (activeId: string, overId: string) => void;
  moveQuestion: (id: string, direction: "up" | "down") => void;

  // Selection
  selectQuestion: (id: string) => void;
  deselectQuestion: (id: string) => void;
  toggleSelection: (id: string) => void;
  clearSelection: () => void;
  selectAll: () => void;

  // Filters
  setFilters: (filters: Partial<QuestionFilters>) => void;
  applyFilters: () => void;
  clearFilters: () => void;

  // State
  markDirty: () => void;
  markSaved: () => void;

  // Computed
  getQuestionById: (id: string) => Question | undefined;
  getTopics: () => string[];
  getStats: () => {
    total: number;
    valid: number;
    invalid: number;
    withAnswers: number;
    topics: string[];
    difficultyBreakdown: Record<Difficulty, number>;
    totalMarks: number;
  };
}

const DEFAULT_FILTERS: QuestionFilters = {
  search: "",
  topic: "",
  difficulty: "",
  status: "all",
  sort_field: "position",
  sort_order: "asc",
};

export const useQuestionsStore = create<QuestionsStore>()(
  subscribeWithSelector((set, get) => ({
    questions: [],
    filteredQuestions: [],
    selectedIds: new Set(),
    isDirty: false,
    lastSaved: null,
    filters: DEFAULT_FILTERS,

    setQuestions: (questions) => {
      set({ questions, isDirty: false });
      get().applyFilters();
    },

    addQuestion: (question) => {
      set((state) => ({
        questions: [...state.questions, question],
        isDirty: true,
      }));
      get().applyFilters();
    },

    updateQuestion: (id, updates) => {
      set((state) => ({
        questions: state.questions.map((q) =>
          q.id === id ? { ...q, ...updates } : q
        ),
        isDirty: true,
      }));
      get().applyFilters();
    },

    removeQuestion: (id) => {
      set((state) => {
        const newSelected = new Set(state.selectedIds);
        newSelected.delete(id);
        return {
          questions: state.questions.filter((q) => q.id !== id),
          selectedIds: newSelected,
          isDirty: true,
        };
      });
      get().applyFilters();
    },

    duplicateQuestion: (id) => {
      const q = get().getQuestionById(id);
      if (!q) return;
      const duplicate: Question = {
        ...q,
        id: `${id}-copy-${Date.now()}`,
        question_number: null,
        position: q.position + 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      set((state) => {
        const idx = state.questions.findIndex((q) => q.id === id);
        const newQuestions = [...state.questions];
        newQuestions.splice(idx + 1, 0, duplicate);
        // Fix positions
        return {
          questions: newQuestions.map((q, i) => ({ ...q, position: i })),
          isDirty: true,
        };
      });
      get().applyFilters();
    },

    reorderQuestions: (activeId, overId) => {
      set((state) => {
        const questions = state.questions;
        const oldIndex = questions.findIndex((q) => q.id === activeId);
        const newIndex = questions.findIndex((q) => q.id === overId);
        if (oldIndex === -1 || newIndex === -1) return state;
        const reordered = arrayMove(questions, oldIndex, newIndex).map(
          (q, i) => ({ ...q, position: i })
        );
        return { questions: reordered, isDirty: true };
      });
      get().applyFilters();
    },

    moveQuestion: (id, direction) => {
      set((state) => {
        const idx = state.questions.findIndex((q) => q.id === id);
        if (idx === -1) return state;
        const newIdx = direction === "up" ? idx - 1 : idx + 1;
        if (newIdx < 0 || newIdx >= state.questions.length) return state;
        const reordered = arrayMove(state.questions, idx, newIdx).map(
          (q, i) => ({ ...q, position: i })
        );
        return { questions: reordered, isDirty: true };
      });
      get().applyFilters();
    },

    // ─── Selection ────────────────────────────────────────────────────────────
    selectQuestion: (id) =>
      set((state) => {
        const newSet = new Set(state.selectedIds);
        newSet.add(id);
        return { selectedIds: newSet };
      }),

    deselectQuestion: (id) =>
      set((state) => {
        const newSet = new Set(state.selectedIds);
        newSet.delete(id);
        return { selectedIds: newSet };
      }),

    toggleSelection: (id) => {
      const { selectedIds } = get();
      if (selectedIds.has(id)) {
        get().deselectQuestion(id);
      } else {
        get().selectQuestion(id);
      }
    },

    clearSelection: () => set({ selectedIds: new Set() }),

    selectAll: () =>
      set((state) => ({
        selectedIds: new Set(state.questions.map((q) => q.id)),
      })),

    // ─── Filters ─────────────────────────────────────────────────────────────
    setFilters: (filters) => {
      set((state) => ({
        filters: { ...state.filters, ...filters },
      }));
      get().applyFilters();
    },

    applyFilters: () => {
      const { questions, filters } = get();
      let result = [...questions];

      // Search
      if (filters.search.trim()) {
        const q = filters.search.toLowerCase();
        result = result.filter(
          (item) =>
            item.question_text.toLowerCase().includes(q) ||
            item.topic?.toLowerCase().includes(q) ||
            item.option_a?.toLowerCase().includes(q) ||
            item.option_b?.toLowerCase().includes(q)
        );
      }

      // Topic filter
      if (filters.topic) {
        result = result.filter((item) => item.topic === filters.topic);
      }

      // Difficulty filter
      if (filters.difficulty) {
        result = result.filter((item) => item.difficulty === filters.difficulty);
      }

      // Status filter
      if (filters.status === "valid") {
        result = result.filter((item) => item.is_valid);
      } else if (filters.status === "invalid") {
        result = result.filter((item) => !item.is_valid);
      }

      // Sort
      result.sort((a, b) => {
        const field = filters.sort_field;
        const dir = filters.sort_order === "asc" ? 1 : -1;
        if (field === "position") return (a.position - b.position) * dir;
        if (field === "marks") return (a.marks - b.marks) * dir;
        if (field === "topic")
          return (a.topic ?? "").localeCompare(b.topic ?? "") * dir;
        if (field === "difficulty") {
          const order = { easy: 0, medium: 1, hard: 2 };
          return (
            ((order[a.difficulty ?? "easy"] ?? 0) -
              (order[b.difficulty ?? "easy"] ?? 0)) *
            dir
          );
        }
        return 0;
      });

      set({ filteredQuestions: result });
    },

    clearFilters: () => {
      set({ filters: DEFAULT_FILTERS });
      get().applyFilters();
    },

    // ─── State ───────────────────────────────────────────────────────────────
    markDirty: () => set({ isDirty: true }),
    markSaved: () => set({ isDirty: false, lastSaved: new Date() }),

    // ─── Computed ────────────────────────────────────────────────────────────
    getQuestionById: (id) => get().questions.find((q) => q.id === id),

    getTopics: () => {
      const topics = get()
        .questions.map((q) => q.topic)
        .filter((t): t is string => !!t);
      return [...new Set(topics)].sort();
    },

    getStats: () => {
      const qs = get().questions;
      const valid = qs.filter((q) => q.is_valid).length;
      const withAnswers = qs.filter((q) => q.correct_answer).length;
      const topics = [...new Set(qs.map((q) => q.topic).filter(Boolean))] as string[];
      const totalMarks = qs.reduce((sum, q) => sum + q.marks, 0);

      const difficultyBreakdown: Record<Difficulty, number> = {
        easy: 0,
        medium: 0,
        hard: 0,
      };
      qs.forEach((q) => {
        if (q.difficulty) difficultyBreakdown[q.difficulty]++;
      });

      return {
        total: qs.length,
        valid,
        invalid: qs.length - valid,
        withAnswers,
        topics,
        difficultyBreakdown,
        totalMarks,
      };
    },
  }))
);
