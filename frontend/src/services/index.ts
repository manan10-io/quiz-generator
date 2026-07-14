import api, { uploadFile } from "./api";
import { API_URL } from "@/lib/constants";
import type {
  Project,
  Question,
  ParseResult,
  ParseOptions,
  GeneratedForm,
  GoogleFormSettings,
  ExportFormat,
  ExportRecord,
  DashboardStats,
  UserSettings,
  PaginatedResponse,
} from "@/types";

// ─── Projects ────────────────────────────────────────────────────────────────

export const projectService = {
  list: async (): Promise<Project[]> => {
    const res = await api.get<{ items: Project[] }>("/projects");
    return res.data.items;
  },

  get: async (id: string): Promise<Project> => {
    const res = await api.get<Project>(`/projects/${id}`);
    return res.data;
  },

  create: async (data: {
    name: string;
    description?: string;
  }): Promise<Project> => {
    const res = await api.post<Project>("/projects", data);
    return res.data;
  },

  update: async (
    id: string,
    data: Partial<Pick<Project, "name" | "description" | "status">>
  ): Promise<Project> => {
    const res = await api.patch<Project>(`/projects/${id}`, data);
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/projects/${id}`);
  },

  duplicate: async (id: string): Promise<Project> => {
    const res = await api.post<Project>(`/projects/${id}/duplicate`);
    return res.data;
  },
};

// ─── Questions ────────────────────────────────────────────────────────────────

export const questionService = {
  list: async (
    projectId: string,
    page = 1,
    pageSize = 100
  ): Promise<PaginatedResponse<Question>> => {
    const res = await api.get<PaginatedResponse<Question>>(
      `/projects/${projectId}/questions`,
      { params: { page, page_size: pageSize } }
    );
    return res.data;
  },

  create: async (
    projectId: string,
    data: Omit<Question, "id" | "project_id" | "created_at" | "updated_at">
  ): Promise<Question> => {
    const res = await api.post<Question>(
      `/projects/${projectId}/questions`,
      data
    );
    return res.data;
  },

  update: async (
    projectId: string,
    questionId: string,
    data: Partial<Question>
  ): Promise<Question> => {
    const res = await api.patch<Question>(
      `/projects/${projectId}/questions/${questionId}`,
      data
    );
    return res.data;
  },

  delete: async (projectId: string, questionId: string): Promise<void> => {
    await api.delete(`/projects/${projectId}/questions/${questionId}`);
  },

  duplicate: async (
    projectId: string,
    questionId: string
  ): Promise<Question> => {
    const res = await api.post<Question>(
      `/projects/${projectId}/questions/${questionId}/duplicate`
    );
    return res.data;
  },

  reorder: async (
    projectId: string,
    orderedIds: string[]
  ): Promise<void> => {
    await api.post(`/projects/${projectId}/questions/reorder`, {
      ordered_ids: orderedIds,
    });
  },

  validateAll: async (
    projectId: string
  ): Promise<{ valid: number; invalid: number; warnings: string[] }> => {
    const res = await api.post(`/projects/${projectId}/questions/validate`);
    return res.data;
  },
};

// ─── Parser ───────────────────────────────────────────────────────────────────

export const parserService = {
  parseText: async (
    text: string,
    projectId: string,
    options: ParseOptions
  ): Promise<ParseResult> => {
    const res = await api.post<ParseResult>("/parse/text", {
      text,
      project_id: projectId,
      options,
    });
    return res.data;
  },

  parseFile: async (
    file: File,
    projectId: string,
    options: ParseOptions
  ): Promise<{ job_id: string }> => {
    const result = await uploadFile("/parse/file", file, {
      project_id: projectId,
      options: JSON.stringify(options),
    });
    return result as { job_id: string };
  },

  getJobStatus: async (jobId: string) => {
    const res = await api.get(`/parse/jobs/${jobId}`);
    return res.data;
  },
};

// ─── Google Forms ─────────────────────────────────────────────────────────────

export const googleFormService = {
  generate: async (
    projectId: string,
    settings: GoogleFormSettings
  ): Promise<GeneratedForm> => {
    const res = await api.post<GeneratedForm>("/forms/generate", {
      project_id: projectId,
      ...settings,
    });
    return res.data;
  },

  list: async (): Promise<GeneratedForm[]> => {
    const res = await api.get<{ items: GeneratedForm[] }>("/forms");
    return res.data.items;
  },

  get: async (id: string): Promise<GeneratedForm> => {
    const res = await api.get<GeneratedForm>(`/forms/${id}`);
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/forms/${id}`);
  },
};

// ─── Exports ─────────────────────────────────────────────────────────────────

export const exportService = {
  generate: async (
    projectId: string,
    format: ExportFormat
  ): Promise<ExportRecord> => {
    const res = await api.post<ExportRecord>(
      `/export/${projectId}/${format}`
    );
    return res.data;
  },

  history: async (): Promise<ExportRecord[]> => {
    const res = await api.get<{ items: ExportRecord[] }>("/export/history");
    return res.data.items;
  },

  getDownloadUrl: async (recordId: string): Promise<string> => {
    const res = await api.get<{ url: string }>(
      `/export/download/${recordId}`
    );
    return new URL(res.data.url, API_URL).toString();
  },
};

// ─── Dashboard ────────────────────────────────────────────────────────────────

export const dashboardService = {
  getStats: async (): Promise<DashboardStats> => {
    const res = await api.get<DashboardStats>("/dashboard/stats");
    return res.data;
  },
};

// ─── Settings ────────────────────────────────────────────────────────────────

export const settingsService = {
  get: async (): Promise<UserSettings> => {
    const res = await api.get<UserSettings>("/settings");
    return res.data;
  },

  update: async (settings: Partial<UserSettings>): Promise<UserSettings> => {
    const res = await api.put<UserSettings>("/settings", settings);
    return res.data;
  },
};
