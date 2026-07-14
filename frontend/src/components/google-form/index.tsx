"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { motion } from "framer-motion";
import {
  ExternalLink, Copy, CheckCircle2, Edit3,
  Shuffle, Eye, MessageSquare, Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { googleFormSettingsSchema, type GoogleFormSettingsValues } from "@/lib/validators";
import { scaleIn } from "@/lib/animations";
import type { GeneratedForm } from "@/types";
import { copyToClipboard } from "@/lib/utils";
import { toast } from "sonner";
import { useState } from "react";

// ─── Form Settings Panel ──────────────────────────────────────────────────────

interface FormSettingsPanelProps {
  defaultTitle?: string;
  totalQuestions: number;
  totalMarks: number;
  onGenerate: (settings: GoogleFormSettingsValues) => Promise<void>;
  isGenerating: boolean;
}

export function FormSettingsPanel({
  defaultTitle = "Quiz",
  totalQuestions,
  totalMarks,
  onGenerate,
  isGenerating,
}: FormSettingsPanelProps) {
  const { register, handleSubmit, watch, setValue, formState: { errors } } =
    useForm<GoogleFormSettingsValues>({
      resolver: zodResolver(googleFormSettingsSchema),
      defaultValues: {
        title: defaultTitle,
        description: "",
        quiz_mode: true,
        shuffle_questions: false,
        shuffle_options: false,
        immediate_release: true,
        confirmation_message: "Thank you for completing the quiz!",
      },
    });

  const quizMode = watch("quiz_mode");

  return (
    <form onSubmit={handleSubmit(onGenerate)} className="space-y-6">
      {/* Summary banner */}
      <div className="rounded-2xl border border-border bg-muted/30 p-4 flex items-center gap-4">
        <div className="flex-1">
          <p className="text-sm font-medium text-foreground">
            {totalQuestions} question{totalQuestions !== 1 ? "s" : ""}
          </p>
          <p className="text-xs text-muted-foreground">
            {totalMarks} total marks
          </p>
        </div>
        <div className="h-10 w-10 rounded-xl bg-red-100 dark:bg-red-950 flex items-center justify-center">
          <svg className="h-5 w-5" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
          </svg>
        </div>
      </div>

      {/* Form title + description */}
      <div className="space-y-3">
        <div className="space-y-1.5">
          <Label>Form title *</Label>
          <Input {...register("title")} placeholder="e.g. Chapter 5 Quiz" />
          {errors.title && (
            <p className="text-xs text-destructive">{errors.title.message}</p>
          )}
        </div>
        <div className="space-y-1.5">
          <Label>Description (optional)</Label>
          <Textarea
            {...register("description")}
            placeholder="Instructions for students…"
            className="min-h-[60px]"
          />
        </div>
      </div>

      {/* Quiz settings toggles */}
      <div className="space-y-3">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Quiz settings
        </p>

        {[
          {
            field: "quiz_mode" as const,
            icon: Zap,
            label: "Quiz mode",
            desc: "Show scores and correct answers to respondents",
          },
          {
            field: "immediate_release" as const,
            icon: Eye,
            label: "Immediate release",
            desc: "Show feedback immediately after submission",
            disabled: !quizMode,
          },
          {
            field: "shuffle_questions" as const,
            icon: Shuffle,
            label: "Shuffle questions",
            desc: "Randomise question order for each respondent",
          },
          {
            field: "shuffle_options" as const,
            icon: Shuffle,
            label: "Shuffle options",
            desc: "Randomise answer choices within each question",
          },
        ].map(({ field, icon: Icon, label, desc, disabled }) => (
          <div
            key={field}
            className={`flex items-center gap-3 rounded-xl border border-border p-3 ${
              disabled ? "opacity-50" : ""
            }`}
          >
            <div className="h-8 w-8 rounded-lg bg-accent flex items-center justify-center shrink-0">
              <Icon className="h-3.5 w-3.5 text-accent-foreground" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-foreground">{label}</p>
              <p className="text-xs text-muted-foreground">{desc}</p>
            </div>
            <Switch
              checked={watch(field) as boolean}
              onCheckedChange={(v) => setValue(field, v)}
              disabled={disabled}
            />
          </div>
        ))}
      </div>

      {/* Confirmation message */}
      <div className="space-y-1.5">
        <Label className="flex items-center gap-1.5">
          <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
          Confirmation message
        </Label>
        <Input
          {...register("confirmation_message")}
          placeholder="Thank you for completing the quiz!"
        />
      </div>

      {/* Generate button */}
      <Button
        type="submit"
        size="lg"
        className="w-full"
        disabled={isGenerating}
      >
        {isGenerating ? (
          <>
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
              <path fill="currentColor" className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Generating form…
          </>
        ) : (
          <>
            <svg className="h-4 w-4" viewBox="0 0 24 24">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="currentColor" opacity="0.8" />
            </svg>
            Generate Google Form quiz
          </>
        )}
      </Button>
    </form>
  );
}

// ─── Form Success Card ────────────────────────────────────────────────────────

interface FormSuccessCardProps {
  form: GeneratedForm;
}

export function FormSuccessCard({ form }: FormSuccessCardProps) {
  const [copied, setCopied] = useState<"responder" | "edit" | null>(null);

  const copy = async (url: string, type: "responder" | "edit") => {
    await copyToClipboard(url);
    setCopied(type);
    toast.success("Link copied!");
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <motion.div
      variants={scaleIn}
      initial="hidden"
      animate="visible"
      className="rounded-2xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/30 p-6 space-y-5"
    >
      {/* Success header */}
      <div className="flex items-center gap-3">
        <div className="h-12 w-12 rounded-2xl bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center">
          <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
        </div>
        <div>
          <h3 className="font-semibold text-foreground">Google Form created!</h3>
          <p className="text-sm text-muted-foreground">
            {form.question_count} questions · {form.total_marks} marks
          </p>
        </div>
      </div>

      {/* Links */}
      <div className="space-y-2">
        {[
          { label: "Share with students", url: form.google_form_url, type: "responder" as const, icon: ExternalLink },
          { label: "Edit in Google Forms", url: form.google_form_edit_url, type: "edit" as const, icon: Edit3 },
        ].map(({ label, url, type, icon: Icon }) => (
          <div key={type} className="flex items-center gap-2 rounded-xl border border-border bg-card p-3">
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-muted-foreground">{label}</p>
              <p className="text-xs text-foreground truncate font-mono mt-0.5">{url}</p>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={() => copy(url, type)}
                title="Copy link"
              >
                {copied === type ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                ) : (
                  <Copy className="h-3.5 w-3.5" />
                )}
              </Button>
              <Button variant="ghost" size="icon-sm" asChild title="Open">
                <a href={url} target="_blank" rel="noopener noreferrer">
                  <Icon className="h-3.5 w-3.5" />
                </a>
              </Button>
            </div>
          </div>
        ))}
      </div>

      {/* Open button */}
      <Button className="w-full" asChild>
        <a href={form.google_form_url} target="_blank" rel="noopener noreferrer">
          <ExternalLink className="h-4 w-4" />
          Open form
        </a>
      </Button>
    </motion.div>
  );
}
