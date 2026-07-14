import { create } from "zustand";

interface UiStore {
  // Modals
  isExportModalOpen: boolean;
  isQuestionEditorOpen: boolean;
  editingQuestionId: string | null;
  isGenerateFormOpen: boolean;
  isConfirmDeleteOpen: boolean;
  deleteTarget: { id: string; label: string } | null;
  isKeyboardShortcutsOpen: boolean;
  isCommandPaletteOpen: boolean;

  // Sidebar
  isSidebarCollapsed: boolean;

  // Parse progress
  parseJobId: string | null;
  parseProgress: number;
  parseMessage: string;
  isParseRunning: boolean;

  // Actions
  openExportModal: () => void;
  closeExportModal: () => void;

  openQuestionEditor: (questionId?: string) => void;
  closeQuestionEditor: () => void;

  openGenerateForm: () => void;
  closeGenerateForm: () => void;

  openConfirmDelete: (id: string, label: string) => void;
  closeConfirmDelete: () => void;

  toggleKeyboardShortcuts: () => void;
  toggleCommandPalette: () => void;
  toggleSidebar: () => void;

  setParseProgress: (jobId: string, progress: number, message: string) => void;
  startParse: (jobId: string) => void;
  endParse: () => void;
}

export const useUiStore = create<UiStore>((set) => ({
  // ─── Modals ────────────────────────────────────────────────────────────────
  isExportModalOpen: false,
  isQuestionEditorOpen: false,
  editingQuestionId: null,
  isGenerateFormOpen: false,
  isConfirmDeleteOpen: false,
  deleteTarget: null,
  isKeyboardShortcutsOpen: false,
  isCommandPaletteOpen: false,

  // ─── Sidebar ──────────────────────────────────────────────────────────────
  isSidebarCollapsed: false,

  // ─── Parse ────────────────────────────────────────────────────────────────
  parseJobId: null,
  parseProgress: 0,
  parseMessage: "",
  isParseRunning: false,

  // ─── Actions ──────────────────────────────────────────────────────────────
  openExportModal: () => set({ isExportModalOpen: true }),
  closeExportModal: () => set({ isExportModalOpen: false }),

  openQuestionEditor: (questionId) =>
    set({ isQuestionEditorOpen: true, editingQuestionId: questionId ?? null }),
  closeQuestionEditor: () =>
    set({ isQuestionEditorOpen: false, editingQuestionId: null }),

  openGenerateForm: () => set({ isGenerateFormOpen: true }),
  closeGenerateForm: () => set({ isGenerateFormOpen: false }),

  openConfirmDelete: (id, label) =>
    set({ isConfirmDeleteOpen: true, deleteTarget: { id, label } }),
  closeConfirmDelete: () =>
    set({ isConfirmDeleteOpen: false, deleteTarget: null }),

  toggleKeyboardShortcuts: () =>
    set((state) => ({
      isKeyboardShortcutsOpen: !state.isKeyboardShortcutsOpen,
    })),
  toggleCommandPalette: () =>
    set((state) => ({
      isCommandPaletteOpen: !state.isCommandPaletteOpen,
    })),
  toggleSidebar: () =>
    set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),

  setParseProgress: (jobId, progress, message) =>
    set({ parseJobId: jobId, parseProgress: progress, parseMessage: message }),
  startParse: (jobId) =>
    set({
      parseJobId: jobId,
      isParseRunning: true,
      parseProgress: 0,
      parseMessage: "Starting…",
    }),
  endParse: () =>
    set({ isParseRunning: false, parseProgress: 100, parseJobId: null }),
}));
