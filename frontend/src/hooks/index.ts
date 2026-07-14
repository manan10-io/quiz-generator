"use client";
import { useEffect, useCallback, useRef } from "react";
import { useSession } from "next-auth/react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useQuestionsStore } from "@/store/questionsStore";
import { useProjectStore } from "@/store/projectStore";
import { useUiStore } from "@/store/uiStore";
import { useSettingsStore } from "@/store/settingsStore";
import {
  projectService,
  questionService,
  parserService,
  googleFormService,
  exportService,
  dashboardService,
  settingsService,
} from "@/services";
import type {
  Question,
  ParseOptions,
  GoogleFormSettings,
  ExportFormat,
} from "@/types";
import { AUTOSAVE_INTERVAL_MS } from "@/lib/constants";
import { debounce } from "@/lib/utils";

// ─── Auth ─────────────────────────────────────────────────────────────────────

export function useAuth() {
  const { data: session, status } = useSession();
  return {
    user: session?.user ?? null,
    accessToken: session?.accessToken ?? null,
    isAuthenticated: status === "authenticated",
    isLoading: status === "loading",
  };
}

// ─── Dashboard stats ──────────────────────────────────────────────────────────

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: dashboardService.getStats,
    staleTime: 60_000,
  });
}

// ─── Projects ─────────────────────────────────────────────────────────────────

export function useProjects() {
  const { setProjects } = useProjectStore();
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["projects"],
    queryFn: projectService.list,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (query.data) setProjects(query.data);
  }, [query.data, setProjects]);

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) =>
      projectService.create(data),
    onSuccess: (project) => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Project created");
      return project;
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: projectService.delete,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
      toast.success("Project deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<{ name: string; description: string }> }) =>
      projectService.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["projects"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return {
    projects: query.data ?? [],
    isLoading: query.isLoading,
    error: query.error,
    createProject: createMutation.mutateAsync,
    deleteProject: deleteMutation.mutate,
    updateProject: updateMutation.mutateAsync,
    isCreating: createMutation.isPending,
  };
}

// ─── Questions (for a specific project) ──────────────────────────────────────

export function useQuestions(projectId: string) {
  const store = useQuestionsStore();
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["questions", projectId],
    queryFn: () => questionService.list(projectId),
    enabled: !!projectId,
    staleTime: 10_000,
  });

  useEffect(() => {
    if (query.data?.items) store.setQuestions(query.data.items);
  }, [query.data]);

  const createMutation = useMutation({
    mutationFn: (data: Partial<Question>) =>
      questionService.create(
        projectId,
        data as Omit<Question, "id" | "project_id" | "created_at" | "updated_at">
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions", projectId] });
      toast.success("Question added");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({
      questionId,
      data,
    }: {
      questionId: string;
      data: Partial<Question>;
    }) => questionService.update(projectId, questionId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["questions", projectId] }),
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (questionId: string) =>
      questionService.delete(projectId, questionId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["questions", projectId] });
      toast.success("Question deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const duplicateMutation = useMutation({
    mutationFn: (questionId: string) =>
      questionService.duplicate(projectId, questionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["questions", projectId] }),
    onError: (err: Error) => toast.error(err.message),
  });

  const reorderMutation = useMutation({
    mutationFn: (orderedIds: string[]) =>
      questionService.reorder(projectId, orderedIds),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["questions", projectId] }),
    onError: (err: Error) => toast.error(err.message),
  });

  return {
    questions: store.filteredQuestions,
    allQuestions: store.questions,
    isLoading: query.isLoading,
    stats: store.getStats(),
    filters: store.filters,
    setFilters: store.setFilters,
    clearFilters: store.clearFilters,
    createQuestion: createMutation.mutateAsync,
    updateQuestion: updateMutation.mutateAsync,
    deleteQuestion: deleteMutation.mutate,
    reorderQuestions: (activeId: string, overId: string) => {
      store.reorderQuestions(activeId, overId);
      const newOrder = store.questions.map((q) => q.id);
      reorderMutation.mutate(newOrder);
    },
    // Duplicate is persisted server-side (the backend clones the row and
    // shifts positions); we then refetch so the new row gets its real id.
    duplicateQuestion: (id: string) => duplicateMutation.mutate(id),
    // Arrow up/down reorders optimistically in the store, then persists the
    // whole new order so it survives a refresh.
    moveQuestion: (id: string, direction: "up" | "down") => {
      store.moveQuestion(id, direction);
      reorderMutation.mutate(store.questions.map((q) => q.id));
    },
  };
}

// ─── Parser ───────────────────────────────────────────────────────────────────

export function useParser() {
  const { startParse, setParseProgress, endParse } = useUiStore();
  const { setQuestions } = useQuestionsStore();
  const qc = useQueryClient();

  const textMutation = useMutation({
    mutationFn: ({
      text,
      projectId,
      options,
    }: {
      text: string;
      projectId: string;
      options: ParseOptions;
    }) => parserService.parseText(text, projectId, options),
    onSuccess: (result, vars) => {
      setQuestions(result.questions);
      qc.invalidateQueries({ queryKey: ["questions", vars.projectId] });
      toast.success(
        `Parsed ${result.questions.length} questions`,
        result.warnings.length
          ? {
              description: `${result.warnings.length} warning${result.warnings.length > 1 ? "s" : ""}`,
            }
          : undefined
      );
    },
    onError: (err: Error) => toast.error(`Parse failed: ${err.message}`),
  });

  const fileMutation = useMutation({
    mutationFn: ({
      file,
      projectId,
      options,
    }: {
      file: File;
      projectId: string;
      options: ParseOptions;
    }) => parserService.parseFile(file, projectId, options),
    onSuccess: ({ job_id }, vars) => {
      startParse(job_id);
      pollJobStatus(job_id, vars.projectId);
    },
    onError: (err: Error) => toast.error(`Upload failed: ${err.message}`),
  });

  const pollJobStatus = useCallback(
    async (jobId: string, projectId: string) => {
      const interval = setInterval(async () => {
        try {
          const job = await parserService.getJobStatus(jobId);
          const progressMap: Record<string, number> = {
            pending: 5,
            ocr: 30,
            parsing: 60,
            ai_clean: 85,
            done: 100,
            failed: 0,
          };
          setParseProgress(
            jobId,
            progressMap[job.status] ?? 50,
            job.status === "done"
              ? `Found ${job.questions_found} questions`
              : job.status
          );

          if (job.status === "done") {
            clearInterval(interval);
            endParse();
            qc.invalidateQueries({ queryKey: ["questions", projectId] });
            toast.success(`Parsed ${job.questions_found} questions`);
          } else if (job.status === "failed") {
            clearInterval(interval);
            endParse();
            toast.error(job.error_message ?? "Parsing failed");
          }
        } catch {
          clearInterval(interval);
          endParse();
        }
      }, 1500);
    },
    [setParseProgress, endParse, qc]
  );

  return {
    parseText: textMutation.mutateAsync,
    parseFile: fileMutation.mutateAsync,
    isParsing: textMutation.isPending || fileMutation.isPending,
  };
}

// ─── Google Form generation ───────────────────────────────────────────────────

export function useGoogleForm() {
  const qc = useQueryClient();

  const generateMutation = useMutation({
    mutationFn: ({
      projectId,
      settings,
    }: {
      projectId: string;
      settings: GoogleFormSettings;
    }) => googleFormService.generate(projectId, settings),
    onSuccess: (form) => {
      qc.invalidateQueries({ queryKey: ["generated-forms"] });
      toast.success("Google Form created!", {
        description: "Opening form in a new tab…",
        action: {
          label: "Open",
          onClick: () => window.open(form.google_form_url, "_blank"),
        },
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const formsQuery = useQuery({
    queryKey: ["generated-forms"],
    queryFn: googleFormService.list,
    staleTime: 30_000,
  });

  return {
    generateForm: generateMutation.mutateAsync,
    isGenerating: generateMutation.isPending,
    generatedForm: generateMutation.data,
    forms: formsQuery.data ?? [],
    isLoadingForms: formsQuery.isLoading,
  };
}

// ─── Export ───────────────────────────────────────────────────────────────────

export function useExport() {
  const qc = useQueryClient();

  const exportMutation = useMutation({
    mutationFn: ({
      projectId,
      format,
    }: {
      projectId: string;
      format: ExportFormat;
    }) => exportService.generate(projectId, format),
    onSuccess: async (record) => {
      toast.success("Export ready!", {
        description: record.file_name,
        action: {
          label: "Download",
          onClick: async () => {
            const url = await exportService.getDownloadUrl(record.id);
            const a = document.createElement("a");
            a.href = url;
            a.download = record.file_name;
            a.click();
          },
        },
      });
      qc.invalidateQueries({ queryKey: ["export-history"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const historyQuery = useQuery({
    queryKey: ["export-history"],
    queryFn: exportService.history,
    staleTime: 30_000,
  });

  return {
    exportProject: exportMutation.mutateAsync,
    isExporting: exportMutation.isPending,
    exportHistory: historyQuery.data ?? [],
  };
}

// ─── Autosave ─────────────────────────────────────────────────────────────────

export function useAutosave(
  projectId: string | null,
  onSave: (id: string) => Promise<void>
) {
  const { isDirty, markSaved } = useQuestionsStore();
  const { settings } = useSettingsStore();
  const isSavingRef = useRef(false);

  const save = useCallback(
    debounce(async (id: string) => {
      if (isSavingRef.current) return;
      isSavingRef.current = true;
      try {
        await onSave(id);
        markSaved();
      } finally {
        isSavingRef.current = false;
      }
    }, AUTOSAVE_INTERVAL_MS) as unknown as (id: string) => void,
    [onSave, markSaved]
  );

  useEffect(() => {
    if (isDirty && projectId) {
      save(projectId);
    }
  }, [isDirty, projectId, save]);
}

// ─── Keyboard shortcuts ───────────────────────────────────────────────────────

export function useKeyboard(
  shortcuts: Array<{
    key: string;
    meta?: boolean;
    ctrl?: boolean;
    shift?: boolean;
    handler: () => void;
  }>
) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        const metaMatch = shortcut.meta ? e.metaKey || e.ctrlKey : true;
        const ctrlMatch = shortcut.ctrl ? e.ctrlKey : true;
        const shiftMatch = shortcut.shift ? e.shiftKey : true;
        const keyMatch = e.key.toLowerCase() === shortcut.key.toLowerCase();

        if (metaMatch && ctrlMatch && shiftMatch && keyMatch) {
          e.preventDefault();
          shortcut.handler();
          break;
        }
      }
    };

    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [shortcuts]);
}

// ─── Settings ─────────────────────────────────────────────────────────────────

export function useSettings() {
  const { settings, updateSettings } = useSettingsStore();
  const qc = useQueryClient();

  const query = useQuery({
    queryKey: ["settings"],
    queryFn: settingsService.get,
    staleTime: 30_000,
  });

  useEffect(() => {
    if (query.data) updateSettings(query.data);
  }, [query.data, updateSettings]);

  const syncMutation = useMutation({
    mutationFn: settingsService.update,
    onSuccess: (savedSettings) => {
      updateSettings(savedSettings);
      qc.invalidateQueries({ queryKey: ["settings"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const save = async (updates: Partial<typeof settings>) => {
    updateSettings(updates);
    await syncMutation.mutateAsync(updates);
  };

  return {
    settings,
    save,
    isSaving: syncMutation.isPending,
    isLoading: query.isLoading,
  };
}

// ─── Search ───────────────────────────────────────────────────────────────────

export function useSearch() {
  const { filters, setFilters, getTopics } = useQuestionsStore();

  const setSearch = useCallback(
    debounce((value: string) => {
      setFilters({ search: value });
    }, 250) as unknown as (value: string) => void,
    [setFilters]
  );

  return {
    search: filters.search,
    setSearch,
    topic: filters.topic,
    setTopic: (topic: string) => setFilters({ topic }),
    difficulty: filters.difficulty,
    setDifficulty: (d: string) =>
      setFilters({ difficulty: d as typeof filters.difficulty }),
    status: filters.status,
    setStatus: (s: string) =>
      setFilters({ status: s as typeof filters.status }),
    availableTopics: getTopics(),
    clearAll: useQuestionsStore.getState().clearFilters,
  };
}
