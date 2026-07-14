"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  FileText, Sheet, Table, Braces, AlignLeft,
  GraduationCap, Zap, Gamepad2, Download, FileType,
  CheckCircle2, Loader2,
} from "lucide-react";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { EXPORT_FORMATS } from "@/lib/constants";
import type { ExportFormat } from "@/types";
import { staggerContainer, fadeUp } from "@/lib/animations";

const ICON_MAP: Record<string, React.ElementType> = {
  FileText, Sheet, Table, Braces, AlignLeft,
  GraduationCap, Zap, Gamepad2, FileType,
};

const CATEGORY_ORDER = ["Document", "Spreadsheet", "Data", "LMS"];

interface ExportModalProps {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onExport: (format: ExportFormat) => Promise<void>;
  projectName: string;
}

export function ExportModal({
  open,
  onOpenChange,
  onExport,
  projectName,
}: ExportModalProps) {
  const [exportingFormat, setExportingFormat] = useState<ExportFormat | null>(null);
  const [doneFormats, setDoneFormats] = useState<Set<ExportFormat>>(new Set());

  const handleExport = async (format: ExportFormat) => {
    setExportingFormat(format);
    try {
      await onExport(format);
      setDoneFormats((prev) => new Set([...prev, format]));
      setTimeout(() => {
        setDoneFormats((prev) => {
          const next = new Set(prev);
          next.delete(format);
          return next;
        });
      }, 3000);
    } finally {
      setExportingFormat(null);
    }
  };

  const grouped = CATEGORY_ORDER.map((category) => ({
    category,
    formats: EXPORT_FORMATS.filter((f) => f.category === category),
  }));

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Export — {projectName}</DialogTitle>
        </DialogHeader>

        <div className="py-2 space-y-5">
          {grouped.map(({ category, formats }) => (
            <div key={category}>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {category}
              </p>
              <motion.div
                variants={staggerContainer}
                initial="hidden"
                animate="visible"
                className="grid grid-cols-2 sm:grid-cols-3 gap-2"
              >
                {formats.map(({ format, label, description, icon }) => {
                  const Icon = ICON_MAP[icon] ?? FileText;
                  const isExporting = exportingFormat === format;
                  const isDone = doneFormats.has(format);

                  return (
                    <motion.button
                      key={format}
                      variants={fadeUp}
                      onClick={() => handleExport(format)}
                      disabled={!!exportingFormat}
                      className={cn(
                        "relative flex flex-col items-start gap-2 rounded-xl border p-3.5 text-left transition-all duration-150",
                        isDone
                          ? "border-emerald-300 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/30"
                          : isExporting
                          ? "border-primary/40 bg-accent/40"
                          : "border-border bg-card hover:border-primary/50 hover:bg-accent/30 hover:shadow-card"
                      )}
                    >
                      <div className="flex items-center justify-between w-full">
                        <div className={cn(
                          "h-8 w-8 rounded-lg flex items-center justify-center",
                          isDone ? "bg-emerald-100 dark:bg-emerald-900" : "bg-muted"
                        )}>
                          {isExporting ? (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          ) : isDone ? (
                            <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                          ) : (
                            <Icon className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                        {!isExporting && !isDone && (
                          <Download className="h-3.5 w-3.5 text-muted-foreground/40" />
                        )}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-foreground">{label}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5 leading-tight">
                          {description}
                        </p>
                      </div>
                    </motion.button>
                  );
                })}
              </motion.div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
