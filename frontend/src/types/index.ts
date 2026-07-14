// ─── Question ────────────────────────────────────────────────────────────────

export type Difficulty = "easy" | "medium" | "hard";

export type CorrectAnswer = "A" | "B" | "C" | "D" | "E";

export interface Question {
  id: string;
  project_id: string;
  question_number: number | null;
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  option_e?: string;
  correct_answer: CorrectAnswer | null;
  marks: number;
  negative_marks: number;
  difficulty: Difficulty | null;
  topic: string | null;
  explanation: string | null;
  position: number;
  is_valid: boolean;
  validation_errors: string[];
  created_at: string;
  updated_at: string;
}

export interface QuestionFormData {
  question_text: string;
  option_a: string;
  option_b: string;
  option_c: string;
  option_d: string;
  option_e?: string;
  correct_answer: CorrectAnswer | "";
  marks: number;
  negative_marks: number;
  difficulty: Difficulty | "";
  topic: string;
  explanation: string;
}

export interface ValidationResult {
  is_valid: boolean;
  errors: string[];
}

// ─── Project ─────────────────────────────────────────────────────────────────

export type ProjectStatus = "draft" | "ready" | "archived";

export interface ProjectMetadata {
  source_type: "text" | "pdf" | "docx" | "image" | "txt" | "csv";
  original_filename?: string;
  parse_duration_ms?: number;
  topics_detected?: string[];
  difficulty_distribution?: Record<Difficulty, number>;
  warnings?: string[];
  duplicates_found?: number;
}

export interface Project {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  status: ProjectStatus;
  question_count: number;
  metadata: ProjectMetadata | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectWithQuestions extends Project {
  questions: Question[];
}

// ─── Parser ──────────────────────────────────────────────────────────────────

export type InputType = "text" | "pdf" | "docx" | "image" | "txt";

export type ParseJobStatus =
  | "pending"
  | "ocr"
  | "parsing"
  | "ai_clean"
  | "done"
  | "failed";

export interface ParseJob {
  id: string;
  project_id: string;
  status: ParseJobStatus;
  input_type: InputType;
  questions_found: number;
  warnings: string[];
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface ParseJobProgress {
  job_id: string;
  status: ParseJobStatus;
  progress: number;
  message: string;
  questions_found?: number;
}

export interface ParseOptions {
  ai_cleanup: boolean;
  remove_duplicates: boolean;
  auto_number: boolean;
  detect_topics: boolean;
  default_marks: number;
  default_difficulty: Difficulty | "";
}

export interface ParseRequest {
  text: string;
  project_id?: string;
  options: ParseOptions;
}

export interface ParseResult {
  job_id: string;
  questions: Question[];
  warnings: string[];
  duplicates_removed: number;
  parse_duration_ms: number;
}

// ─── Google Forms ────────────────────────────────────────────────────────────

export interface GoogleFormSettings {
  title: string;
  description: string;
  quiz_mode: boolean;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  immediate_release: boolean;
  confirmation_message: string;
}

export interface GeneratedForm {
  id: string;
  project_id: string;
  user_id: string;
  google_form_id: string;
  google_form_url: string;
  google_form_edit_url: string;
  title: string;
  description: string | null;
  question_count: number;
  total_marks: number;
  settings: GoogleFormSettings;
  generated_at: string;
}

// ─── Export ──────────────────────────────────────────────────────────────────

export type ExportFormat =
  | "pdf"
  | "docx"
  | "excel"
  | "csv"
  | "json"
  | "txt"
  | "moodle"
  | "quizizz"
  | "kahoot";

export interface ExportRecord {
  id: string;
  project_id: string;
  user_id: string;
  format: ExportFormat;
  file_name: string;
  file_size: number | null;
  download_url: string | null;
  expires_at: string | null;
  created_at: string;
}

// ─── User / Auth ─────────────────────────────────────────────────────────────

export interface UserSettings {
  default_marks: number;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  theme: "light" | "dark" | "system";
  language: string;
  default_difficulty: Difficulty | "" | null;
  autosave_interval: number;
}

export interface User {
  id: string;
  google_id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  settings: UserSettings;
  created_at: string;
}

// ─── API ─────────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code: number;
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface DashboardStats {
  total_questions: number;
  total_projects: number;
  forms_generated: number;
  parse_accuracy: number;
  questions_this_week: number;
  difficulty_distribution: Record<Difficulty, number>;
  top_topics: Array<{ topic: string; count: number }>;
}

// ─── UI State ────────────────────────────────────────────────────────────────

export interface Toast {
  id: string;
  title: string;
  description?: string;
  type: "success" | "error" | "warning" | "info";
}

export type SortField = "position" | "topic" | "difficulty" | "marks" | "created_at";
export type SortOrder = "asc" | "desc";

export interface QuestionFilters {
  search: string;
  topic: string;
  difficulty: Difficulty | "";
  status: "all" | "valid" | "invalid";
  sort_field: SortField;
  sort_order: SortOrder;
}
