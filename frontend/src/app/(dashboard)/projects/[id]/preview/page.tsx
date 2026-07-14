"use client";

import { use } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import {
  ArrowLeft, Edit2, Download, CheckCircle2, Circle,
  BookOpen, Target, Sparkles,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { QuestionSearch } from "@/components/questions";
import { EmptyState, PageLoading } from "@/components/common";
import { ExportModal } from "@/components/export";
import { useProjects, useQuestions, useExport } from "@/hooks";
import { useUiStore } from "@/store/uiStore";
import { pageVariants, staggerContainer, questionItemVariants } from "@/lib/animations";
import { cn, getDifficultyColor, formatMarks } from "@/lib/utils";
import type { Question } from "@/types";

interface PreviewPageProps {
  params: Promise<{
     id: string;
  }>;
}

function PreviewCard({ question, index }: { question: Question; index: number }) {
  const options = [
    { letter: "A", text: question.option_a },
    { letter: "B", text: question.option_b },
    { letter: "C", text: question.option_c },
    { letter: "D", text: question.option_d },
    ...(question.option_e ? [{ letter: "E", text: question.option_e }] : []),
  ].filter((o) => o.text);

  return (
    <motion.div
      variants={questionItemVariants}
      className="rounded-2xl border border-border bg-card shadow-card p-5 space-y-4"
    >
      {/* Question header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 flex-1 min-w-0">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent text-xs font-bold text-accent-foreground">
            {index + 1}
          </span>
          <p className="text-sm font-medium text-foreground leading-snug pt-0.5">
            {question.question_text}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          {question.topic && (
            <Badge variant="accent" className="text-[10px]">
              {question.topic}
            </Badge>
          )}
          {question.difficulty && (
            <span className={cn("text-[10px] px-2 py-0.5 rounded-md font-medium", getDifficultyColor(question.difficulty))}>
              {question.difficulty}
            </span>
          )}
        </div>
      </div>

      {/* Options */}
      <div className="space-y-2">
        {options.map(({ letter, text }) => {
          const isCorrect = question.correct_answer === letter;
          return (
            <div
              key={letter}
              className={cn(
                "flex items-center gap-3 rounded-xl p-3 border transition-colors",
                isCorrect
                  ? "border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40"
                  : "border-border bg-muted/20"
              )}
            >
              <div className={cn(
                "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold",
                isCorrect
                  ? "border-emerald-500 bg-emerald-500 text-white"
                  : "border-border text-muted-foreground"
              )}>
                {isCorrect ? <CheckCircle2 className="h-3.5 w-3.5" /> : letter}
              </div>
              <span className={cn(
                "text-sm",
                isCorrect ? "text-emerald-800 dark:text-emerald-300 font-medium" : "text-foreground"
              )}>
                {text}
              </span>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-1 border-t border-border">
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Target className="h-3 w-3" />
            {formatMarks(question.marks)}
          </span>
          {question.correct_answer && (
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-3 w-3" />
              Answer: {question.correct_answer}
            </span>
          )}
        </div>
        {question.explanation && (
          <Badge variant="outline" className="text-[10px]">
            Has explanation
          </Badge>
        )}
      </div>

      {/* Explanation */}
      {question.explanation && (
        <div className="rounded-xl bg-muted/40 border border-border px-3.5 py-2.5">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Explanation: </span>
            {question.explanation}
          </p>
        </div>
      )}
    </motion.div>
  );
}

export default function PreviewPage({ params }: PreviewPageProps) {
  const resolvedParams = use(params) as { id: string };
  const projectId = resolvedParams.id;
  const { projects } = useProjects();
  const project = projects.find((p) => p.id === projectId);
  const { questions, isLoading, stats, filters, setFilters } = useQuestions(projectId);
  const { isExportModalOpen, openExportModal, closeExportModal } = useUiStore();
  const { exportProject } = useExport();

  if (isLoading) return <PageLoading label="Loading preview…" />;

  return (
    <>
      <Header
        title={`Preview — ${project?.name ?? "Questions"}`}
        subtitle={`${stats.total} questions · ${stats.totalMarks} marks`}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link href={`/projects/${projectId}/editor`}>
                <Edit2 className="h-4 w-4" />
                Edit
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={openExportModal}>
              <Download className="h-4 w-4" />
              Export
            </Button>
            <Button size="sm" asChild className="shadow-glow-violet">
              <Link href={`/projects/${projectId}/editor`}>
                <Sparkles className="h-4 w-4" />
                Generate form
              </Link>
            </Button>
          </div>
        }
      />

      <motion.div
        variants={pageVariants}
        initial="hidden"
        animate="visible"
        className="p-5 space-y-4"
      >
        {/* Stats strip */}
        <motion.div
          variants={staggerContainer}
          className="flex flex-wrap gap-3 text-xs"
        >
          {[
            { icon: Target, label: `${stats.total} questions`, color: "text-foreground" },
            { icon: CheckCircle2, label: `${stats.withAnswers} with answers`, color: "text-emerald-600 dark:text-emerald-400" },
            { icon: BookOpen, label: `${stats.topics.length} topics`, color: "text-foreground" },
          ].map(({ icon: Icon, label, color }) => (
            <div key={label} className={cn("flex items-center gap-1.5", color)}>
              <Icon className="h-3.5 w-3.5" />
              <span>{label}</span>
            </div>
          ))}
        </motion.div>

        {/* Search */}
        <QuestionSearch
          search={filters.search}
          onSearchChange={(v) => setFilters({ search: v })}
          topic={filters.topic}
          onTopicChange={(v) => setFilters({ topic: v })}
          difficulty={filters.difficulty}
          onDifficultyChange={(v) => setFilters({ difficulty: v as typeof filters.difficulty })}
          topics={stats.topics}
          totalCount={stats.total}
          filteredCount={questions.length}
        />

        {/* Cards */}
        {questions.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No questions found"
            description="Try clearing your search or filters."
          />
        ) : (
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
            className="grid grid-cols-1 xl:grid-cols-2 gap-4"
          >
            {questions.map((q, idx) => (
              <PreviewCard key={q.id} question={q} index={idx} />
            ))}
          </motion.div>
        )}
      </motion.div>

      <ExportModal
        open={isExportModalOpen}
        onOpenChange={closeExportModal}
        projectName={project?.name ?? "Questions"}
        onExport={async (format) => {
          await exportProject({ projectId, format });
        }}
      />
    </>
  );
}
