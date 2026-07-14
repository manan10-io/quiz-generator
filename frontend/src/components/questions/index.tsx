"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  DndContext, closestCenter, KeyboardSensor, PointerSensor,
  useSensor, useSensors, type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext, verticalListSortingStrategy,
  useSortable, sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  GripVertical, Edit2, Copy, Trash2, ChevronUp, ChevronDown,
  AlertTriangle, CheckCircle2, Search, SlidersHorizontal, X,
  Plus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/common";
import { questionFormSchema, type QuestionFormValues } from "@/lib/validators";
import { cn, getDifficultyColor, formatMarks } from "@/lib/utils";
import { DIFFICULTY_OPTIONS, ANSWER_OPTIONS } from "@/lib/constants";
import { questionItemVariants } from "@/lib/animations";
import type { Question } from "@/types";

// ─── Option pill ──────────────────────────────────────────────────────────────

function OptionPill({
  letter,
  text,
  isCorrect,
}: {
  letter: string;
  text: string;
  isCorrect: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs border",
        isCorrect
          ? "bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300"
          : "bg-muted/40 border-border text-muted-foreground"
      )}
    >
      <span className={cn("font-semibold", isCorrect ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground")}>
        {letter}.
      </span>
      <span className="truncate">{text}</span>
      {isCorrect && <CheckCircle2 className="h-3 w-3 text-emerald-500 shrink-0 ml-auto" />}
    </div>
  );
}

// ─── Question Card ────────────────────────────────────────────────────────────

interface QuestionCardProps {
  question: Question;
  onEdit: () => void;
  onDelete: () => void;
  onDuplicate: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst: boolean;
  isLast: boolean;
}

export function QuestionCard({
  question,
  onEdit,
  onDelete,
  onDuplicate,
  onMoveUp,
  onMoveDown,
  isFirst,
  isLast,
}: QuestionCardProps) {
  const options = [
    { letter: "A", text: question.option_a },
    { letter: "B", text: question.option_b },
    { letter: "C", text: question.option_c },
    { letter: "D", text: question.option_d },
    ...(question.option_e ? [{ letter: "E", text: question.option_e }] : []),
  ].filter((o) => o.text);

  return (
    <div
      className={cn(
        "group rounded-2xl border bg-card shadow-card transition-all duration-150",
        !question.is_valid
          ? "border-amber-300 dark:border-amber-800"
          : "border-border hover:border-border/80 hover:shadow-card-hover"
      )}
    >
      <div className="flex gap-3 p-4">
        {/* Drag handle + number */}
        <div className="flex flex-col items-center gap-1 pt-0.5 shrink-0">
          <GripVertical className="h-4 w-4 text-muted-foreground/40 cursor-grab active:cursor-grabbing" />
          <span className="text-[11px] font-mono text-muted-foreground/60">
            {question.position + 1}
          </span>
        </div>

        {/* Question content */}
        <div className="flex-1 min-w-0">
          {/* Validation warnings */}
          {question.validation_errors.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {question.validation_errors.map((err) => (
                <span
                  key={err}
                  className="flex items-center gap-1 text-[10px] bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 rounded-md px-2 py-0.5"
                >
                  <AlertTriangle className="h-2.5 w-2.5" />
                  {err}
                </span>
              ))}
            </div>
          )}

          {/* Question text */}
          <p className="text-sm font-medium text-foreground leading-snug mb-3">
            {question.question_text}
          </p>

          {/* Options grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mb-3">
            {options.map(({ letter, text }) => (
              <OptionPill
                key={letter}
                letter={letter}
                text={text}
                isCorrect={question.correct_answer === letter}
              />
            ))}
          </div>
        </div>

        {/* Right: badges + actions */}
        <div className="flex flex-col items-end gap-2 shrink-0">
          {/* Tags */}
          <div className="flex flex-wrap gap-1.5 justify-end">
            {question.topic && (
              <Badge variant="accent" className="text-[10px]">
                {question.topic}
              </Badge>
            )}
            {question.difficulty && (
              <span
                className={cn(
                  "text-[10px] px-2 py-0.5 rounded-md font-medium border-0",
                  getDifficultyColor(question.difficulty)
                )}
              >
                {question.difficulty}
              </span>
            )}
          </div>
          <span className="text-[11px] text-muted-foreground">
            {formatMarks(question.marks)}
          </span>

          {/* Actions */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onMoveUp}
              disabled={isFirst}
              title="Move up"
            >
              <ChevronUp className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onMoveDown}
              disabled={isLast}
              title="Move down"
            >
              <ChevronDown className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={onEdit} title="Edit">
              <Edit2 className="h-3.5 w-3.5" />
            </Button>
            <Button variant="ghost" size="icon-sm" onClick={onDuplicate} title="Duplicate">
              <Copy className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={onDelete}
              title="Delete"
              className="text-destructive hover:text-destructive hover:bg-destructive/10"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </div>

      {/* Explanation bar */}
      {question.explanation && (
        <div className="border-t border-border px-4 py-2.5 bg-muted/30">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium text-foreground">Explanation: </span>
            {question.explanation}
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Sortable wrapper ─────────────────────────────────────────────────────────

function SortableQuestion({
  question,
  ...props
}: Omit<QuestionCardProps, "onMoveUp" | "onMoveDown" | "isFirst" | "isLast"> & {
  question: Question;
  onMoveUp: () => void;
  onMoveDown: () => void;
  isFirst: boolean;
  isLast: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: question.id });

  // dnd-kit's ref/listeners live on a plain <div> (its HTML `onDrag` clashes
  // with framer-motion's PanInfo-based `onDrag` if spread onto motion.div).
  // The outer motion.div is kept purely for the list entrance animation.
  return (
    <motion.div variants={questionItemVariants}>
      <div
        ref={setNodeRef}
        style={{
          transform: CSS.Transform.toString(transform),
          transition,
          opacity: isDragging ? 0.5 : 1,
          zIndex: isDragging ? 50 : undefined,
        }}
        {...attributes}
        {...listeners}
      >
        <QuestionCard question={question} {...props} />
      </div>
    </motion.div>
  );
}

// ─── Question List ────────────────────────────────────────────────────────────

interface QuestionListProps {
  questions: Question[];
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
  onReorder: (activeId: string, overId: string) => void;
  onMove: (id: string, dir: "up" | "down") => void;
}

export function QuestionList({
  questions,
  onEdit,
  onDelete,
  onDuplicate,
  onReorder,
  onMove,
}: QuestionListProps) {
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      onReorder(String(active.id), String(over.id));
    }
  };

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext
          items={questions.map((q) => q.id)}
          strategy={verticalListSortingStrategy}
        >
          <motion.div
            initial="hidden"
            animate="visible"
            className="space-y-3"
          >
            <AnimatePresence mode="popLayout">
              {questions.map((q, idx) => (
                <SortableQuestion
                  key={q.id}
                  question={q}
                  onEdit={() => onEdit(q.id)}
                  onDelete={() => setDeleteTarget(q.id)}
                  onDuplicate={() => onDuplicate(q.id)}
                  onMoveUp={() => onMove(q.id, "up")}
                  onMoveDown={() => onMove(q.id, "down")}
                  isFirst={idx === 0}
                  isLast={idx === questions.length - 1}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        </SortableContext>
      </DndContext>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete question?"
        description="This action cannot be undone. The question will be permanently removed from this project."
        confirmLabel="Delete"
        onConfirm={() => {
          if (deleteTarget) {
            onDelete(deleteTarget);
            setDeleteTarget(null);
          }
        }}
      />
    </>
  );
}

// ─── Question Editor Modal ────────────────────────────────────────────────────

interface QuestionEditorProps {
  question?: Question | null;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onSave: (data: QuestionFormValues) => Promise<void>;
}

export function QuestionEditor({
  question,
  open,
  onOpenChange,
  onSave,
}: QuestionEditorProps) {
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<QuestionFormValues>({
    resolver: zodResolver(questionFormSchema),
    defaultValues: question
      ? {
          question_text: question.question_text,
          option_a: question.option_a,
          option_b: question.option_b,
          option_c: question.option_c,
          option_d: question.option_d,
          option_e: question.option_e ?? "",
          correct_answer: (question.correct_answer as QuestionFormValues["correct_answer"]) ?? "",
          marks: question.marks,
          negative_marks: question.negative_marks,
          difficulty: (question.difficulty as QuestionFormValues["difficulty"]) ?? "",
          topic: question.topic ?? "",
          explanation: question.explanation ?? "",
        }
      : {
          marks: 1,
          negative_marks: 0,
          correct_answer: "" as QuestionFormValues["correct_answer"],
          difficulty: "",
          topic: "",
          explanation: "",
        },
  });

  const onSubmit = async (data: QuestionFormValues) => {
    await onSave(data);
    onOpenChange(false);
    reset();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {question ? "Edit question" : "Add question"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5 py-2">
          {/* Question text */}
          <div className="space-y-1.5">
            <Label>Question *</Label>
            <Textarea
              {...register("question_text")}
              placeholder="Enter the question text…"
              className="min-h-[80px]"
            />
            {errors.question_text && (
              <p className="text-xs text-destructive">{errors.question_text.message}</p>
            )}
          </div>

          {/* Options */}
          <div className="space-y-2">
            <Label>Options *</Label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {(["A", "B", "C", "D", "E"] as const).map((letter) => {
                const key = `option_${letter.toLowerCase()}` as keyof QuestionFormValues;
                return (
                  <div key={letter} className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs font-semibold text-muted-foreground">
                      {letter}.
                    </span>
                    <Input
                      {...register(key as never)}
                      placeholder={letter === "E" ? `Option ${letter} (optional)` : `Option ${letter}`}
                      className="pl-7"
                    />
                  </div>
                );
              })}
            </div>
          </div>

          {/* Correct answer + Marks */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <Label>Correct answer *</Label>
              <Select
                value={watch("correct_answer")}
                onValueChange={(v) =>
                  setValue("correct_answer", v as QuestionFormValues["correct_answer"])
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {ANSWER_OPTIONS.map(({ value, label }) => (
                    <SelectItem key={value} value={value}>
                      Option {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.correct_answer && (
                <p className="text-xs text-destructive">{errors.correct_answer.message}</p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label>Marks</Label>
              <Input
                type="number"
                step="0.5"
                min="0"
                {...register("marks", { valueAsNumber: true })}
              />
            </div>

            <div className="space-y-1.5">
              <Label>Negative marks</Label>
              <Input
                type="number"
                step="0.25"
                min="0"
                {...register("negative_marks", { valueAsNumber: true })}
              />
            </div>
          </div>

          {/* Topic + Difficulty */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label>Topic</Label>
              <Input
                {...register("topic")}
                placeholder="e.g. Physics, Algebra…"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Difficulty</Label>
              <Select
                value={watch("difficulty") ?? ""}
                onValueChange={(v) =>
                  setValue("difficulty", v as QuestionFormValues["difficulty"])
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select…" />
                </SelectTrigger>
                <SelectContent>
                  {DIFFICULTY_OPTIONS.map(({ value, label }) => (
                    <SelectItem key={value} value={value}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Explanation */}
          <div className="space-y-1.5">
            <Label>Explanation (optional)</Label>
            <Textarea
              {...register("explanation")}
              placeholder="Optional explanation or rationale for the correct answer…"
              className="min-h-[60px]"
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving…" : question ? "Save changes" : "Add question"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ─── Question Search Bar ──────────────────────────────────────────────────────

interface QuestionSearchProps {
  search: string;
  onSearchChange: (v: string) => void;
  topic: string;
  onTopicChange: (v: string) => void;
  difficulty: string;
  onDifficultyChange: (v: string) => void;
  topics: string[];
  totalCount: number;
  filteredCount: number;
}

export function QuestionSearch({
  search,
  onSearchChange,
  topic,
  onTopicChange,
  difficulty,
  onDifficultyChange,
  topics,
  totalCount,
  filteredCount,
}: QuestionSearchProps) {
  const hasFilters = search || topic || difficulty;

  return (
    <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center">
      {/* Search input */}
      <div className="relative flex-1">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search questions…"
          className="pl-8 h-8 text-sm"
        />
        {search && (
          <button
            onClick={() => onSearchChange("")}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {/* Topic filter */}
      <Select value={topic || "_all"} onValueChange={(v) => onTopicChange(v === "_all" ? "" : v)}>
        <SelectTrigger className="h-8 text-xs w-[140px]">
          <SelectValue placeholder="All topics" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="_all">All topics</SelectItem>
          {topics.map((t) => (
            <SelectItem key={t} value={t}>
              {t}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Difficulty filter */}
      <Select value={difficulty || "_all"} onValueChange={(v) => onDifficultyChange(v === "_all" ? "" : v)}>
        <SelectTrigger className="h-8 text-xs w-[130px]">
          <SelectValue placeholder="All difficulty" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="_all">All difficulty</SelectItem>
          {DIFFICULTY_OPTIONS.map(({ value, label }) => (
            <SelectItem key={value} value={value}>
              {label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* Count + clear */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
        {hasFilters ? (
          <>
            <span>
              {filteredCount} / {totalCount}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => {
                onSearchChange("");
                onTopicChange("");
                onDifficultyChange("");
              }}
              title="Clear filters"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </>
        ) : (
          <span>{totalCount} questions</span>
        )}
      </div>
    </div>
  );
}
