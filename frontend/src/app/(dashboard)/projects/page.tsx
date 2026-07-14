"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Folder, Search, Plus, MoreHorizontal, Edit2,
  Trash2, Copy, Grid3x3, List, Clock, Target,
} from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { EmptyState, PageLoading, ConfirmDialog } from "@/components/common";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { useProjects } from "@/hooks";
import { staggerContainer, fadeUp } from "@/lib/animations";
import {
  cn, formatDate, getStatusColor, getStatusLabel, truncate,
} from "@/lib/utils";
import type { Project } from "@/types";

function ProjectCard({ project, onDelete, onDuplicate }: {
  project: Project;
  onDelete: (id: string) => void;
  onDuplicate: (id: string) => void;
}) {
  return (
    <motion.div
      variants={fadeUp}
      layout
      className="group rounded-2xl border border-border bg-card shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200 overflow-hidden"
    >
      <Link href={`/projects/${project.id}/editor`} className="block p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="h-10 w-10 rounded-xl bg-accent flex items-center justify-center shrink-0">
            <Folder className="h-5 w-5 text-accent-foreground" />
          </div>
          <Badge className={cn("text-[10px] mt-0.5", getStatusColor(project.status))}>
            {getStatusLabel(project.status)}
          </Badge>
        </div>

        {/* Name */}
        <h3 className="font-semibold text-foreground text-sm mb-1 group-hover:text-primary transition-colors">
          {truncate(project.name, 52)}
        </h3>
        {project.description && (
          <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
            {project.description}
          </p>
        )}

        {/* Metadata */}
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Target className="h-3 w-3" />
            {project.question_count} questions
          </span>
          <span className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {formatDate(project.updated_at)}
          </span>
        </div>
      </Link>

      {/* Actions bar */}
      <div className="border-t border-border px-4 py-2.5 flex items-center justify-between">
        <Button variant="ghost" size="sm" asChild className="text-xs h-7">
          <Link href={`/projects/${project.id}/editor`}>
            <Edit2 className="h-3.5 w-3.5" />
            Edit
          </Link>
        </Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem asChild>
              <Link href={`/projects/${project.id}/editor`}>
                <Edit2 className="h-3.5 w-3.5" />
                Open editor
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href={`/projects/${project.id}/preview`}>
                Preview
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onDuplicate(project.id)}>
              <Copy className="h-3.5 w-3.5" />
              Duplicate
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => onDelete(project.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </motion.div>
  );
}

export default function ProjectsPage() {
  const { projects, isLoading, deleteProject, updateProject } = useProjects();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const filtered = projects.filter((p) => {
    const matchSearch = !search || p.name.toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <>
      <Header
        title="Projects"
        subtitle={`${projects.length} project${projects.length !== 1 ? "s" : ""}`}
        actions={
          <Button size="sm" asChild>
            <Link href="/projects/new">
              <Plus className="h-4 w-4" />
              New project
            </Link>
          </Button>
        }
      />

      <div className="p-5 space-y-5">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-2 items-start sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects…"
              className="pl-8 h-8 text-sm"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="h-8 w-[130px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All status</SelectItem>
              <SelectItem value="draft">Draft</SelectItem>
              <SelectItem value="ready">Ready</SelectItem>
              <SelectItem value="archived">Archived</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex border border-border rounded-lg overflow-hidden">
            {(["grid", "list"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                className={cn(
                  "px-2.5 py-1.5 transition-colors",
                  viewMode === mode
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {mode === "grid" ? (
                  <Grid3x3 className="h-4 w-4" />
                ) : (
                  <List className="h-4 w-4" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="rounded-2xl border border-border bg-card p-5 space-y-3">
                <Skeleton className="h-10 w-10 rounded-xl" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-3 w-1/2" />
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon={Folder}
            title={search ? "No projects found" : "No projects yet"}
            description={
              search
                ? `No projects match "${search}". Try a different search.`
                : "Create your first project to start generating Google Form quizzes."
            }
            action={{
              label: "Create project",
              onClick: () => {},
              icon: Plus,
            }}
          />
        ) : (
          <AnimatePresence mode="popLayout">
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              animate="visible"
              className={cn(
                viewMode === "grid"
                  ? "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
                  : "flex flex-col gap-2"
              )}
            >
              {filtered.map((project) => (
                <ProjectCard
                  key={project.id}
                  project={project}
                  onDelete={(id) => setDeleteTarget(id)}
                  onDuplicate={(id) => {}}
                />
              ))}
            </motion.div>
          </AnimatePresence>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(o) => !o && setDeleteTarget(null)}
        title="Delete project?"
        description="This will permanently delete the project and all its questions. This action cannot be undone."
        confirmLabel="Delete project"
        onConfirm={() => {
          if (deleteTarget) {
            deleteProject(deleteTarget);
            setDeleteTarget(null);
          }
        }}
      />
    </>
  );
}
