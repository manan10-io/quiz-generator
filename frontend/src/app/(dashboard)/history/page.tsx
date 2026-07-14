"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  ExternalLink, Download, FileText, Clock,
  Sparkles, Trash2, Copy, CheckCircle2,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EmptyState } from "@/components/common";
import { useGoogleForm, useExport } from "@/hooks";
import { staggerContainer, fadeUp } from "@/lib/animations";
import { formatFullDate, formatFileSize, copyToClipboard, EXPORT_FORMAT_LABELS } from "@/lib/utils";
import { toast } from "sonner";
import { exportService } from "@/services";

export default function HistoryPage() {
  const { forms, isLoadingForms } = useGoogleForm();
  const { exportHistory } = useExport();

  const handleCopyFormUrl = async (url: string) => {
    await copyToClipboard(url);
    toast.success("Form URL copied!");
  };

  const handleDownload = async (recordId: string, fileName: string) => {
    try {
      const url = await exportService.getDownloadUrl(recordId);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      a.click();
    } catch {
      toast.error("Download failed");
    }
  };

  return (
    <>
      <Header title="History" subtitle="Generated forms and exports" />

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="p-5"
      >
        <Tabs defaultValue="forms">
          <TabsList className="mb-5">
            <TabsTrigger value="forms" className="gap-1.5">
              <Sparkles className="h-3.5 w-3.5" />
              Generated forms
              {forms.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-[10px] px-1.5 py-0">
                  {forms.length}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="exports" className="gap-1.5">
              <Download className="h-3.5 w-3.5" />
              Exports
              {exportHistory.length > 0 && (
                <Badge variant="secondary" className="ml-1 text-[10px] px-1.5 py-0">
                  {exportHistory.length}
                </Badge>
              )}
            </TabsTrigger>
          </TabsList>

          {/* ─── Forms tab ─── */}
          <TabsContent value="forms">
            {isLoadingForms ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="rounded-2xl border border-border bg-card p-5">
                    <div className="flex items-start gap-4">
                      <Skeleton className="h-10 w-10 rounded-xl" />
                      <div className="flex-1 space-y-2">
                        <Skeleton className="h-4 w-48" />
                        <Skeleton className="h-3 w-32" />
                        <Skeleton className="h-3 w-64" />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : forms.length === 0 ? (
              <EmptyState
                icon={Sparkles}
                title="No forms generated yet"
                description="Open a project and click 'Generate form' to create your first Google Form quiz."
                action={{
                  label: "Go to projects",
                  onClick: () => {},
                }}
              />
            ) : (
              <motion.div variants={staggerContainer} className="space-y-3">
                {forms.map((form) => (
                  <motion.div
                    key={form.id}
                    variants={fadeUp}
                    className="rounded-2xl border border-border bg-card p-5 shadow-card hover:shadow-card-hover transition-all duration-150"
                  >
                    <div className="flex items-start gap-4">
                      {/* Google Forms icon */}
                      <div className="h-10 w-10 rounded-xl bg-red-50 dark:bg-red-950 flex items-center justify-center shrink-0">
                        <svg className="h-5 w-5" viewBox="0 0 24 24">
                          <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                          <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                          <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                          <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                        </svg>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <h3 className="font-semibold text-foreground text-sm">{form.title}</h3>
                          <Badge variant="success" className="text-[10px] shrink-0">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Live
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                          <span>{form.question_count} questions</span>
                          <span>{form.total_marks} marks</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatFullDate(form.generated_at)}
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1.5 font-mono truncate">
                          {form.google_form_url}
                        </p>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border">
                      <Button size="sm" variant="outline" asChild>
                        <a href={form.google_form_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="h-3.5 w-3.5" />
                          Open form
                        </a>
                      </Button>
                      <Button size="sm" variant="outline" asChild>
                        <a href={form.google_form_edit_url} target="_blank" rel="noopener noreferrer">
                          Edit in Forms
                        </a>
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCopyFormUrl(form.google_form_url)}
                        className="ml-auto"
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copy URL
                      </Button>
                    </div>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </TabsContent>

          {/* ─── Exports tab ─── */}
          <TabsContent value="exports">
            {exportHistory.length === 0 ? (
              <EmptyState
                icon={Download}
                title="No exports yet"
                description="Export a project as PDF, DOCX, Excel, or other formats from the editor."
              />
            ) : (
              <motion.div variants={staggerContainer} className="space-y-2">
                {exportHistory.map((record) => (
                  <motion.div
                    key={record.id}
                    variants={fadeUp}
                    className="flex items-center gap-4 rounded-2xl border border-border bg-card p-4 shadow-card hover:shadow-card-hover transition-all"
                  >
                    <div className="h-9 w-9 rounded-xl bg-muted flex items-center justify-center shrink-0">
                      <FileText className="h-4.5 w-4.5 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">
                        {record.file_name}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
                        <Badge variant="secondary" className="text-[10px] uppercase">
                          {EXPORT_FORMAT_LABELS[record.format] ?? record.format}
                        </Badge>
                        {record.file_size && (
                          <span>{formatFileSize(record.file_size)}</span>
                        )}
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatFullDate(record.created_at)}
                        </span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleDownload(record.id, record.file_name)}
                    >
                      <Download className="h-3.5 w-3.5" />
                      Download
                    </Button>
                  </motion.div>
                ))}
              </motion.div>
            )}
          </TabsContent>
        </Tabs>
      </motion.div>
    </>
  );
}
