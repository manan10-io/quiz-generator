import { z } from "zod";

// ─── Question ────────────────────────────────────────────────────────────────

export const questionFormSchema = z.object({
  question_text: z
    .string()
    .min(3, "Question must be at least 3 characters")
    .max(2000, "Question must be under 2000 characters"),
  option_a: z.string().min(1, "Option A is required"),
  option_b: z.string().min(1, "Option B is required"),
  option_c: z.string().min(1, "Option C is required"),
  option_d: z.string().min(1, "Option D is required"),
  option_e: z.string().optional(),
  correct_answer: z.enum(["A", "B", "C", "D", "E"], {
    required_error: "Select the correct answer",
  }),
  marks: z
    .number({ invalid_type_error: "Marks must be a number" })
    .min(0, "Marks cannot be negative")
    .max(100, "Marks cannot exceed 100"),
  negative_marks: z
    .number({ invalid_type_error: "Negative marks must be a number" })
    .min(0, "Cannot be negative")
    .max(100, "Cannot exceed 100"),
  difficulty: z.enum(["easy", "medium", "hard"]).optional().or(z.literal("")),
  topic: z.string().max(255, "Topic too long").optional().or(z.literal("")),
  explanation: z
    .string()
    .max(5000, "Explanation too long")
    .optional()
    .or(z.literal("")),
});

export type QuestionFormValues = z.infer<typeof questionFormSchema>;

// ─── Project ─────────────────────────────────────────────────────────────────

export const projectFormSchema = z.object({
  name: z
    .string()
    .min(1, "Project name is required")
    .max(500, "Project name must be under 500 characters"),
  description: z.string().max(2000, "Description too long").optional(),
});

export type ProjectFormValues = z.infer<typeof projectFormSchema>;

// ─── Parse options ────────────────────────────────────────────────────────────

export const parseOptionsSchema = z.object({
  ai_cleanup: z.boolean().default(true),
  remove_duplicates: z.boolean().default(true),
  auto_number: z.boolean().default(false),
  detect_topics: z.boolean().default(true),
  default_marks: z.number().min(0).max(100).default(1),
  default_difficulty: z.enum(["easy", "medium", "hard"]).optional().or(z.literal("")),
});

// ─── New project form (combines project + parse options) ──────────────────────

export const newProjectSchema = z.object({
  name: z.string().min(1, "Project name is required").max(500),
  description: z.string().max(2000).optional(),
  parse_options: parseOptionsSchema,
});

export type NewProjectValues = z.infer<typeof newProjectSchema>;

// ─── Google Form settings ─────────────────────────────────────────────────────

export const googleFormSettingsSchema = z.object({
  title: z.string().min(1, "Form title is required").max(500),
  description: z.string().max(2000).default(""),
  quiz_mode: z.boolean().default(true),
  shuffle_questions: z.boolean().default(false),
  shuffle_options: z.boolean().default(false),
  immediate_release: z.boolean().default(true),
  confirmation_message: z.string().max(500).default("Thank you for completing the quiz!"),
});

export type GoogleFormSettingsValues = z.infer<typeof googleFormSettingsSchema>;

// ─── User settings ────────────────────────────────────────────────────────────

export const userSettingsSchema = z.object({
  default_marks: z.number().min(0).max(100).default(1),
  shuffle_questions: z.boolean().default(false),
  shuffle_options: z.boolean().default(false),
  theme: z.enum(["light", "dark", "system"]).default("system"),
  language: z.string().default("en"),
  default_difficulty: z.enum(["easy", "medium", "hard"]).optional().or(z.literal("")),
  autosave_interval: z.number().min(1).max(60).default(5),
});

export type UserSettingsValues = z.infer<typeof userSettingsSchema>;
