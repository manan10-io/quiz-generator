"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  ArrowLeft, Plus, Download, Sparkles, Eye,
  CheckCircle2, AlertTriangle, Target, BookOpen, BarChart3,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  QuestionList, QuestionEditor, QuestionSearch,
} from "@/components/questions";
import { FormSettingsPanel, FormSuccessCard } from "@/components/google-form";
import { ExportModal } from "@/components/export";
import { EmptyState, PageLoading } from "@/components/common";
import { ParseProgress } from "@/components/upload";
import { Separator } from "@/components/ui/separator";
import {
  useQuestions, useProjects, useGoogleForm, useExport, useKeyboard,
} from "@/hooks";
import { useUiStore } from "@/store/uiStore";
import { useQuestionsStore } from "@/store/questionsStore";
import { pageVariants, fadeUp } from "@/lib/animations";
import type { QuestionFormValues } from "@/lib/validators";
import type { Question } from "@/types";
import { cn } from "@/lib/utils";

interface EditorPageProps {
  params: {
     id: string;
  };
}

export default function EditorPage({ params }: EditorPageProps) {
  const { id: projectId } = params;
  const { projects } = useProjects();
  const project = projects.find((p) => p.id === projectId);

  const {
    questions, allQuestions, isLoading, stats, filters, setFilters,
    createQuestion, updateQuestion, deleteQuestion, reorderQuestions, duplicateQuestion, moveQuestion,
  } = useQuestions(projectId);

  const { generateForm, isGenerating, generatedForm } = useGoogleForm();
  const { exportProject, isExporting } = useExport();

  const {
    isQuestionEditorOpen, editingQuestionId, openQuestionEditor,
    closeQuestionEditor, isExportModalOpen, openExportModal, closeExportModal,
    isParseRunning,
  } = useUiStore();

  const editingQuestion = editingQuestionId
    ? allQuestions.find((q) => q.id === editingQuestionId)
    : null;

  const [showGeneratePanel, setShowGeneratePanel] = useState(false);
  const [activeTab, setActiveTab] = useState<"editor" | "stats">("editor");

  // Keyboard shortcuts
  useKeyboard([
    { key: "e", meta: true, handler: () => openQuestionEditor() },
    { key: "g", meta: true, handler: () => setShowGeneratePanel(true) },
    { key: "e", meta: true, shift: true, handler: openExportModal },
  ]);

  const handleSaveQuestion = async (data: QuestionFormValues) => {
    // The form uses "" to mean "not set", but the API only accepts a real
    // enum value or null — normalise before sending or the backend 422s.
    const payload: Partial<Question> = {
      question_text: data.question_text,
      option_a: data.option_a,
      option_b: data.option_b,
      option_c: data.option_c,
      option_d: data.option_d,
      option_e: data.option_e || "",
      correct_answer: data.correct_answer as Question["correct_answer"],
      marks: data.marks,
      negative_marks: data.negative_marks,
      difficulty: data.difficulty ? data.difficulty : null,
      topic: data.topic ? data.topic : null,
      explanation: data.explanation ? data.explanation : null,
    };

    if (editingQuestionId) {
      await updateQuestion({ questionId: editingQuestionId, data: payload });
    } else {
      await createQuestion(payload);
    }
  };

  if (isLoading && !allQuestions.length) return <PageLoading label="Loading questions…" />;

  return (
    <>
      <Header
        title={project?.name ?? "Editor"}
        subtitle={`${stats.total} question${stats.total !== 1 ? "s" : ""} · ${stats.totalMarks} marks`}
        showSearch
        actions={
          <div className="flex items-center gap-2">
            {/* Stats badges */}
            {stats.invalid > 0 && (
              <Badge variant="warning" className="hidden sm:flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" />
                {stats.invalid} issue{stats.invalid !== 1 ? "s" : ""}
              </Badge>
            )}
            {stats.invalid === 0 && stats.total > 0 && (
              <Badge variant="success" className="hidden sm:flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                All valid
              </Badge>
            )}

            <Button variant="outline" size="sm" asChild>
              <Link href={`/projects/${projectId}/preview`}>
                <Eye className="h-4 w-4" />
                <span className="hidden sm:inline">Preview</span>
              </Link>
            </Button>
            <Button variant="outline" size="sm" onClick={openExportModal}>
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">Export</span>
            </Button>
            <Button
              size="sm"
              onClick={() => setShowGeneratePanel(true)}
              className="shadow-glow-violet"
            >
              <Sparkles className="h-4 w-4" />
              <span className="hidden sm:inline">Generate form</span>
            </Button>
          </div>
        }
      />

      <motion.div
        variants={pageVariants}
        initial="hidden"
        animate="visible"
        className="flex h-[calc(100vh-56px)]"
      >
        {/* ─── Main editor area ─── */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {/* Parse progress bar */}
          <AnimatePresence>
            {isParseRunning && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
              >
                <ParseProgress />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Search + filters */}
          {allQuestions.length > 0 && (
            <motion.div variants={fadeUp}>
              <QuestionSearch
                search={filters.search}
                onSearchChange={(v) => setFilters({ search: v })}
                topic={filters.topic}
                onTopicChange={(v) => setFilters({ topic: v })}
                difficulty={filters.difficulty}
                onDifficultyChange={(v) =>
                  setFilters({ difficulty: v as typeof filters.difficulty })
                }
                topics={stats.topics}
                totalCount={allQuestions.length}
                filteredCount={questions.length}
              />
            </motion.div>
          )}

          {/* Questions */}
          {questions.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title="No questions yet"
              description="Add a question manually or go back to import from a question bank."
              action={{
                label: "Add question",
                onClick: () => openQuestionEditor(),
                icon: Plus,
              }}
            />
          ) : (
            <QuestionList
              questions={questions}
              onEdit={openQuestionEditor}
              onDelete={deleteQuestion}
              onDuplicate={duplicateQuestion}
              onReorder={reorderQuestions}
              onMove={moveQuestion}
            />
          )}

          {/* Add question button */}
          {allQuestions.length > 0 && (
            <motion.div variants={fadeUp}>
              <Button
                variant="outline"
                className="w-full border-dashed"
                onClick={() => openQuestionEditor()}
              >
                <Plus className="h-4 w-4" />
                Add question
              </Button>
            </motion.div>
          )}
        </div>

        {/* ─── Right: Generate panel (slides in) ─── */}
        <AnimatePresence>
          {showGeneratePanel && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 380, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "tween", ease: [0.4, 0, 0.2, 1], duration: 0.25 }}
              className="shrink-0 border-l border-border bg-card overflow-y-auto"
            >
              <div className="p-5 space-y-5">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold text-sm text-foreground">Generate Google Form</h3>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={() => setShowGeneratePanel(false)}
                  >
                    ×
                  </Button>
                </div>

                {generatedForm ? (
                  <FormSuccessCard form={generatedForm} />
                ) : (
                  <FormSettingsPanel
                    defaultTitle={project?.name}
                    totalQuestions={stats.total}
                    totalMarks={stats.totalMarks}
                    onGenerate={async (settings) => {
                      await generateForm({ projectId, settings });
                    }}
                    isGenerating={isGenerating}
                  />
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </motion.div>

      {/* ─── Modals ─── */}
      <QuestionEditor
        question={editingQuestion ?? null}
        open={isQuestionEditorOpen}
        onOpenChange={closeQuestionEditor}
        onSave={handleSaveQuestion}
      />

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
