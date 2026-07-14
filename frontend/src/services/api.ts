import axios, { type AxiosError, type AxiosInstance } from "axios";
import { getSession } from "next-auth/react";
import { API_URL } from "@/lib/constants";
import type { ApiError } from "@/types";

// ─── Create axios instance ────────────────────────────────────────────────────

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// ─── Request interceptor — attach JWT ─────────────────────────────────────────

api.interceptors.request.use(
  async (config) => {
    try {
      const session = await getSession();
      if (session?.accessToken) {
        config.headers.Authorization = `Bearer ${session.accessToken}`;
      }
    } catch {
      // No session, proceed without auth header
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ─── Response interceptor — normalise errors ──────────────────────────────────

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const status = error.response?.status;

    // Session expired
    if (status === 401) {
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      return Promise.reject(error);
    }

    // Surface backend error detail
    const detail = error.response?.data?.detail ?? error.message;
    const apiError = new Error(detail) as Error & {
      statusCode: number;
      detail: string;
    };
    apiError.statusCode = status ?? 0;
    apiError.detail = detail;

    return Promise.reject(apiError);
  }
);

export default api;

// ─── Multipart upload helper ──────────────────────────────────────────────────

export async function uploadFile(
  endpoint: string,
  file: File,
  extraFields?: Record<string, string>
): Promise<unknown> {
  const session = await getSession();
  const form = new FormData();
  form.append("file", file);

  if (extraFields) {
    Object.entries(extraFields).forEach(([k, v]) => form.append(k, v));
  }

  const res = await axios.post(`${API_URL}${endpoint}`, form, {
    headers: {
      "Content-Type": "multipart/form-data",
      ...(session?.accessToken
        ? { Authorization: `Bearer ${session.accessToken}` }
        : {}),
    },
    timeout: 120000, // 2 minutes for large files
  });

  return res.data;
}
