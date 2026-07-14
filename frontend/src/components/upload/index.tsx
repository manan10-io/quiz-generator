"use client";

import { useState, useCallback } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import {
  ClipboardPaste, Upload, Image as ImageIcon,
  File, X, CheckCircle2, AlertCircle, Loader2,
} from "lucide-react";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Progress } from "@/components/ui/progress";
import { cn, formatFileSize } from "@/lib/utils";
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE_BYTES, PARSE_STATUS_MESSAGES } from "@/lib/constants";
import { useUiStore } from "@/store/uiStore";
import { tabContentVariants } from "@/lib/animations";

// ─── Text Paste Area ──────────────────────────────────────────────────────────

interface TextPasteAreaProps {
  value: string;
  onChange: (v: string) => void;
}

export function TextPasteArea({ value, onChange }: TextPasteAreaProps) {
  const lineCount = value ? value.split("\n").length : 0;

  return (
    <div className="relative group">
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={`Paste your MCQ text here. Supports formats like:

1. What is AI?
A. Apple  B. Artificial Intelligence  C. Animal Intelligence  D. Automatic Input
Answer: B

Q1) What is the capital of India?
(A) Mumbai  (B) Delhi  (C) Kolkata  (D) Chennai
Ans: B

Supports English, Hindi (हिंदी), Gujarati (ગુજરાતી), and mixed languages.`}
        className="min-h-[320px] font-mono text-sm resize-none bg-muted/30 leading-relaxed"
        spellCheck={false}
      />
      {value && (
        <div className="absolute bottom-3 right-3 flex items-center gap-3 text-xs text-muted-foreground">
          <span>{lineCount} lines</span>
          <span>{value.length} chars</span>
          <button
            onClick={() => onChange("")}
            className="hover:text-foreground transition-colors rounded p-0.5 hover:bg-muted"
            title="Clear"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

// ─── File Drop Zone ───────────────────────────────────────────────────────────

interface FileDropZoneProps {
  onFile: (file: File) => void;
  accept?: Record<string, string[]>;
  label?: string;
}

export function FileDropZone({
  onFile,
  accept = ACCEPTED_FILE_TYPES,
  label = "Drop PDF, DOCX, TXT, or CSV here",
}: FileDropZoneProps) {
  const [droppedFile, setDroppedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      setError(null);
      if (rejected.length > 0) {
        const msg = rejected[0].errors[0]?.message ?? "File not accepted";
        setError(msg);
        return;
      }
      if (accepted[0]) {
        setDroppedFile(accepted[0]);
        onFile(accepted[0]);
      }
    },
    [onFile]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    maxSize: MAX_FILE_SIZE_BYTES,
    multiple: false,
  });

  const clearFile = () => {
    setDroppedFile(null);
    setError(null);
  };

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          "relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 cursor-pointer transition-all duration-200",
          isDragActive
            ? "border-primary bg-accent/60 scale-[1.01]"
            : droppedFile
            ? "border-emerald-400 bg-emerald-50/50 dark:bg-emerald-950/30"
            : "border-border hover:border-primary/50 hover:bg-muted/40 bg-muted/20"
        )}
      >
        <input {...getInputProps()} />
        <AnimatePresence mode="wait">
          {droppedFile ? (
            <motion.div
              key="file"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex flex-col items-center gap-3 text-center"
            >
              <div className="h-12 w-12 rounded-2xl bg-emerald-100 dark:bg-emerald-900 flex items-center justify-center">
                <CheckCircle2 className="h-6 w-6 text-emerald-600 dark:text-emerald-400" />
              </div>
              <div>
                <p className="font-medium text-foreground text-sm">{droppedFile.name}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {formatFileSize(droppedFile.size)}
                </p>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="flex flex-col items-center gap-3 text-center"
            >
              <div className={cn(
                "h-12 w-12 rounded-2xl flex items-center justify-center transition-colors",
                isDragActive ? "bg-primary/20" : "bg-muted"
              )}>
                <Upload className={cn("h-6 w-6", isDragActive ? "text-primary" : "text-muted-foreground")} />
              </div>
              <div>
                <p className="font-medium text-foreground text-sm">
                  {isDragActive ? "Drop it here!" : label}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  or click to browse · max {MAX_FILE_SIZE_BYTES / 1024 / 1024}MB
                </p>
              </div>
              <div className="flex flex-wrap gap-1.5 justify-center">
                {["PDF", "DOCX", "TXT", "CSV"].map((ext) => (
                  <span
                    key={ext}
                    className="text-[10px] bg-accent text-accent-foreground px-2 py-0.5 rounded-md font-medium"
                  >
                    .{ext.toLowerCase()}
                  </span>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Clear file */}
      {droppedFile && (
        <Button variant="ghost" size="sm" onClick={clearFile} className="w-full text-muted-foreground">
          <X className="h-3.5 w-3.5" />
          Remove file
        </Button>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center gap-2 text-xs text-destructive bg-destructive/10 rounded-lg px-3 py-2">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          {error}
        </div>
      )}
    </div>
  );
}

// ─── Image / OCR Drop Zone ────────────────────────────────────────────────────

interface ImageDropZoneProps {
  onFile: (file: File) => void;
}

export function ImageDropZone({ onFile }: ImageDropZoneProps) {
  const IMAGE_TYPES = {
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/webp": [".webp"],
    "image/gif": [".gif"],
  };

  return (
    <div className="space-y-4">
      <FileDropZone
        onFile={onFile}
        accept={IMAGE_TYPES}
        label="Drop an image or screenshot here"
      />
      <div className="rounded-xl border border-border bg-muted/30 p-4 space-y-2">
        <p className="text-xs font-medium text-foreground">OCR information</p>
        <div className="grid grid-cols-3 gap-2">
          {["English", "Hindi (हिंदी)", "Gujarati (ગુ.)"].map((lang) => (
            <div key={lang} className="text-xs bg-card border border-border rounded-lg px-2.5 py-2 text-center text-muted-foreground">
              {lang}
            </div>
          ))}
        </div>
        <p className="text-xs text-muted-foreground">
          Scanned papers and screenshots are automatically preprocessed before OCR for best accuracy.
        </p>
      </div>
    </div>
  );
}

// ─── Parse Progress ───────────────────────────────────────────────────────────

export function ParseProgress() {
  const { isParseRunning, parseProgress, parseMessage } = useUiStore();

  if (!isParseRunning) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="rounded-xl border border-primary/20 bg-accent/40 p-4"
    >
      <div className="flex items-center gap-3 mb-3">
        <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />
        <p className="text-sm font-medium text-foreground">{parseMessage}</p>
        <span className="ml-auto text-xs font-mono text-primary">{parseProgress}%</span>
      </div>
      <Progress value={parseProgress} className="h-1.5" />
    </motion.div>
  );
}

// ─── Input Tabs (master component) ────────────────────────────────────────────

interface InputTabsProps {
  text: string;
  onTextChange: (v: string) => void;
  onFile: (file: File) => void;
}

export function InputTabs({ text, onTextChange, onFile }: InputTabsProps) {
  return (
    <Tabs defaultValue="text" className="w-full">
      <TabsList className="w-full mb-4">
        <TabsTrigger value="text" className="flex-1 gap-1.5">
          <ClipboardPaste className="h-3.5 w-3.5" />
          Paste text
        </TabsTrigger>
        <TabsTrigger value="file" className="flex-1 gap-1.5">
          <File className="h-3.5 w-3.5" />
          Upload file
        </TabsTrigger>
        <TabsTrigger value="image" className="flex-1 gap-1.5">
          <ImageIcon className="h-3.5 w-3.5" />
          Image / OCR
        </TabsTrigger>
      </TabsList>

      <AnimatePresence mode="wait">
        <TabsContent value="text" asChild>
          <motion.div
            variants={tabContentVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <TextPasteArea value={text} onChange={onTextChange} />
          </motion.div>
        </TabsContent>

        <TabsContent value="file" asChild>
          <motion.div
            variants={tabContentVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <FileDropZone onFile={onFile} />
          </motion.div>
        </TabsContent>

        <TabsContent value="image" asChild>
          <motion.div
            variants={tabContentVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <ImageDropZone onFile={onFile} />
          </motion.div>
        </TabsContent>
      </AnimatePresence>
    </Tabs>
  );
}
