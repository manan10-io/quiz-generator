"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeft, Sparkles, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { InputTabs, ParseProgress } from "@/components/upload";
import { newProjectSchema, type NewProjectValues } from "@/lib/validators";
import { DEFAULT_PARSE_OPTIONS, DIFFICULTY_OPTIONS } from "@/lib/constants";
import { useProjects, useParser } from "@/hooks";
import { pageVariants, fadeUp } from "@/lib/animations";
import { toast } from "sonner";
import type { ParseOptions } from "@/types";

const AUTO_DIFFICULTY_VALUE = "_auto";

export default function NewProjectPage() {
  const router = useRouter();
  const { createProject } = useProjects();
  const { parseText, parseFile, isParsing } = useParser();
  const [pastedText, setPastedText] = useState("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [isCreating, setIsCreating] = useState(false);

  const { register, handleSubmit, watch, setValue, formState: { errors } } =
    useForm<NewProjectValues>({
      resolver: zodResolver(newProjectSchema),
      defaultValues: {
        name: "",
        description: "",
        parse_options: DEFAULT_PARSE_OPTIONS,
      },
    });

  const parseOptions = watch("parse_options");

  const onSubmit = async (data: NewProjectValues) => {
    const hasInput = pastedText.trim().length > 10 || uploadedFile;
    if (!hasInput) {
      toast.error("Please paste text or upload a file first");
      return;
    }

    setIsCreating(true);
    try {
      // 1. Create the project
      const project = await createProject({
        name: data.name || "Untitled project",
        description: data.description,
      });

      // 2. Parse the input
      const options: ParseOptions = {
        ...data.parse_options,
        default_difficulty: data.parse_options.default_difficulty || "",
      };
      if (pastedText.trim()) {
        const result = await parseText({
          text: pastedText,
          projectId: project.id,
          options,
        });
        setWarnings(result.warnings);
      } else if (uploadedFile) {
        await parseFile({
          file: uploadedFile,
          projectId: project.id,
          options,
        });
        // File parsing is async — redirect and polling happens there
        router.push(`/projects/${project.id}/editor`);
        return;
      }

      // 3. Navigate to editor
      router.push(`/projects/${project.id}/editor`);
    } catch (err: unknown) {
      toast.error((err as Error)?.message ?? "Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <>
      <Header
        title="New project"
        subtitle="Import your question bank"
        actions={
          <Button
            onClick={handleSubmit(onSubmit)}
            disabled={isCreating || isParsing}
            size="sm"
          >
            {isCreating || isParsing ? "Parsing…" : "Parse & continue →"}
          </Button>
        }
      />

      <motion.div
        variants={pageVariants}
        initial="hidden"
        animate="visible"
        className="p-5"
      >
        <div className="max-w-5xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ─── Left: Input area ─── */}
          <div className="lg:col-span-2 space-y-4">
            <motion.div variants={fadeUp} className="rounded-2xl border border-border bg-card p-5 shadow-card">
              <h2 className="text-sm font-semibold text-foreground mb-4">
                Import questions
              </h2>
              <InputTabs
                text={pastedText}
                onTextChange={setPastedText}
                onFile={setUploadedFile}
              />
            </motion.div>

            {/* Parse progress */}
            <AnimatePresence>
              {isParsing && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <ParseProgress />
                </motion.div>
              )}
            </AnimatePresence>

            {/* Warnings */}
            <AnimatePresence>
              {warnings.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4 space-y-2"
                >
                  <div className="flex items-center gap-2 text-sm font-medium text-amber-800 dark:text-amber-400">
                    <AlertTriangle className="h-4 w-4" />
                    {warnings.length} warning{warnings.length !== 1 ? "s" : ""} detected
                  </div>
                  <ul className="space-y-1">
                    {warnings.map((w) => (
                      <li key={w} className="text-xs text-amber-700 dark:text-amber-500 flex items-start gap-1.5">
                        <span className="mt-0.5 shrink-0">•</span>
                        {w}
                      </li>
                    ))}
                  </ul>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* ─── Right: Settings ─── */}
          <div className="space-y-4">
            {/* Project details */}
            <motion.div variants={fadeUp} className="rounded-2xl border border-border bg-card p-5 shadow-card space-y-4">
              <h2 className="text-sm font-semibold text-foreground">Project details</h2>

              <div className="space-y-1.5">
                <Label>Project name</Label>
                <Input
                  {...register("name")}
                  placeholder="e.g. Class 10 Science MCQ"
                />
                {errors.name && (
                  <p className="text-xs text-destructive">{errors.name.message}</p>
                )}
              </div>

              <div className="space-y-1.5">
                <Label>Description (optional)</Label>
                <Textarea
                  {...register("description")}
                  placeholder="Notes about this question bank…"
                  className="min-h-[64px]"
                />
              </div>

              <div className="space-y-1.5">
                <Label>Default marks per question</Label>
                <Input
                  type="number"
                  step="0.5"
                  min="0"
                  {...register("parse_options.default_marks", { valueAsNumber: true })}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Default difficulty</Label>
                <Select
                  value={parseOptions.default_difficulty || AUTO_DIFFICULTY_VALUE}
                  onValueChange={(v) =>
                    setValue(
                      "parse_options.default_difficulty",
                      v === AUTO_DIFFICULTY_VALUE
                        ? ""
                        : (v as typeof parseOptions.default_difficulty)
                    )
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Auto-detect" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={AUTO_DIFFICULTY_VALUE}>Auto-detect</SelectItem>
                    {DIFFICULTY_OPTIONS.map(({ value, label }) => (
                      <SelectItem key={value} value={value}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </motion.div>

            {/* Parse options */}
            <motion.div variants={fadeUp} className="rounded-2xl border border-border bg-card p-5 shadow-card space-y-4">
              <h2 className="text-sm font-semibold text-foreground">Parse options</h2>

              {[
                { field: "parse_options.ai_cleanup" as const, label: "AI cleanup", desc: "Fix broken lines and merge split questions" },
                { field: "parse_options.remove_duplicates" as const, label: "Remove duplicates", desc: "Detect and remove identical questions" },
                { field: "parse_options.auto_number" as const, label: "Auto-number", desc: "Re-number questions sequentially" },
                { field: "parse_options.detect_topics" as const, label: "Detect topics", desc: "Auto-assign topics from question content" },
              ].map(({ field, label, desc }) => {
                const parts = field.split(".");
                const key = parts[1] as keyof typeof parseOptions;
                return (
                  <div key={field} className="flex items-center justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-sm text-foreground">{label}</p>
                      <p className="text-xs text-muted-foreground">{desc}</p>
                    </div>
                    <Switch
                      checked={parseOptions[key] as boolean}
                      onCheckedChange={(v) => setValue(field, v)}
                    />
                  </div>
                );
              })}
            </motion.div>

            {/* AI info box */}
            <motion.div
              variants={fadeUp}
              className="rounded-2xl border border-primary/20 bg-accent/40 p-4 flex gap-3"
            >
              <Sparkles className="h-4 w-4 text-primary shrink-0 mt-0.5" />
              <p className="text-xs text-muted-foreground leading-relaxed">
                AI cleanup uses Claude to fix broken OCR output, repair split
                questions, and resolve ambiguous answer formats.
              </p>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </>
  );
}
