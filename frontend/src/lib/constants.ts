import type { Difficulty, ExportFormat, ParseOptions } from "@/types";

export const APP_NAME = "QuizGen AI";
export const APP_TAGLINE = "Convert any question bank into a Google Quiz in seconds";
export const APP_URL = process.env.NEXTAUTH_URL ?? "http://localhost:3000";
export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// ─── Pagination ───────────────────────────────────────────────────────────────
export const DEFAULT_PAGE_SIZE = 20;

// ─── Autosave ─────────────────────────────────────────────────────────────────
export const AUTOSAVE_INTERVAL_MS = 5000;

// ─── File upload limits ───────────────────────────────────────────────────────
export const MAX_FILE_SIZE_MB = 25;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
export const ACCEPTED_FILE_TYPES = {
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "text/plain": [".txt"],
  "text/csv": [".csv"],
  "image/png": [".png"],
  "image/jpeg": [".jpg", ".jpeg"],
  "image/webp": [".webp"],
  "image/gif": [".gif"],
};

// ─── Difficulties ─────────────────────────────────────────────────────────────
export const DIFFICULTY_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

// ─── Answer options ───────────────────────────────────────────────────────────
export const ANSWER_OPTIONS = [
  { value: "A", label: "A" },
  { value: "B", label: "B" },
  { value: "C", label: "C" },
  { value: "D", label: "D" },
  { value: "E", label: "E" },
];

// ─── Export formats ───────────────────────────────────────────────────────────
export const EXPORT_FORMATS: Array<{
  format: ExportFormat;
  label: string;
  description: string;
  icon: string;
  category: string;
}> = [
  {
    format: "pdf",
    label: "PDF",
    description: "Printable question paper",
    icon: "FileText",
    category: "Document",
  },
  {
    format: "docx",
    label: "Word Document",
    description: "Editable .docx file",
    icon: "FileType",
    category: "Document",
  },
  {
    format: "excel",
    label: "Excel Spreadsheet",
    description: "Questions in .xlsx format",
    icon: "Sheet",
    category: "Spreadsheet",
  },
  {
    format: "csv",
    label: "CSV",
    description: "Comma-separated values",
    icon: "Table",
    category: "Spreadsheet",
  },
  {
    format: "json",
    label: "JSON",
    description: "Structured JSON data",
    icon: "Braces",
    category: "Data",
  },
  {
    format: "txt",
    label: "Plain Text",
    description: "Simple text format",
    icon: "AlignLeft",
    category: "Data",
  },
  {
    format: "moodle",
    label: "Moodle XML",
    description: "Import to Moodle LMS",
    icon: "GraduationCap",
    category: "LMS",
  },
  {
    format: "quizizz",
    label: "Quizizz CSV",
    description: "Import to Quizizz",
    icon: "Zap",
    category: "LMS",
  },
  {
    format: "kahoot",
    label: "Kahoot CSV",
    description: "Import to Kahoot",
    icon: "Gamepad2",
    category: "LMS",
  },
];

// ─── Default parse options ────────────────────────────────────────────────────
export const DEFAULT_PARSE_OPTIONS: ParseOptions = {
  ai_cleanup: true,
  remove_duplicates: true,
  auto_number: false,
  detect_topics: true,
  default_marks: 1,
  default_difficulty: "",
};

// ─── Keyboard shortcuts ───────────────────────────────────────────────────────
export const KEYBOARD_SHORTCUTS = [
  { keys: ["⌘", "K"], description: "Open command palette" },
  { keys: ["⌘", "N"], description: "New project" },
  { keys: ["⌘", "S"], description: "Save project" },
  { keys: ["⌘", "E"], description: "Export questions" },
  { keys: ["⌘", "G"], description: "Generate Google Form" },
  { keys: ["⌘", "F"], description: "Search questions" },
  { keys: ["⌘", "/"], description: "Toggle keyboard shortcuts" },
  { keys: ["?"], description: "Show keyboard shortcuts" },
];

// ─── Navigation items ─────────────────────────────────────────────────────────
export const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: "LayoutDashboard" },
  { href: "/projects", label: "Projects", icon: "Folder" },
  { href: "/projects/new", label: "New project", icon: "FilePlus" },
  { href: "/history", label: "History", icon: "Clock" },
  { href: "/settings", label: "Settings", icon: "Settings" },
];

// ─── Topic suggestions (common exam topics) ───────────────────────────────────
export const COMMON_TOPICS = [
  "Mathematics",
  "Physics",
  "Chemistry",
  "Biology",
  "History",
  "Geography",
  "Economics",
  "Political Science",
  "English",
  "Hindi",
  "Science",
  "Social Science",
  "Computer Science",
  "Reasoning",
  "General Knowledge",
  "Current Affairs",
];

// ─── Parse status messages ────────────────────────────────────────────────────
export const PARSE_STATUS_MESSAGES: Record<string, string> = {
  pending: "Queued for processing…",
  ocr: "Extracting text from image…",
  parsing: "Detecting questions and options…",
  ai_clean: "AI is cleaning up the text…",
  done: "Parsing complete!",
  failed: "Parsing failed",
};
