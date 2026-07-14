"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  TrendingUp, Folder, Sparkles, Target,
  AlertCircle, ChevronRight, Plus,
} from "lucide-react";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip as RTooltip,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { staggerContainer, fadeUp } from "@/lib/animations";
import type { DashboardStats, Project } from "@/types";
import { formatDate, getStatusColor, getStatusLabel } from "@/lib/utils";
import { cn } from "@/lib/utils";

// ─── Stat Cards ───────────────────────────────────────────────────────────────

interface StatCardsProps {
  stats?: DashboardStats;
  isLoading: boolean;
}

const STAT_CONFIG = [
  {
    key: "total_questions" as const,
    label: "Total questions",
    icon: Target,
    color: "text-violet-500",
    bg: "bg-violet-50 dark:bg-violet-950",
    format: (n: number) => n.toLocaleString("en-IN"),
    sub: (s: DashboardStats) => `+${s.questions_this_week} this week`,
    subColor: "text-emerald-600 dark:text-emerald-400",
  },
  {
    key: "total_projects" as const,
    label: "Projects",
    icon: Folder,
    color: "text-sky-500",
    bg: "bg-sky-50 dark:bg-sky-950",
    format: (n: number) => n.toString(),
    sub: () => "All time",
    subColor: "text-muted-foreground",
  },
  {
    key: "forms_generated" as const,
    label: "Forms generated",
    icon: Sparkles,
    color: "text-emerald-500",
    bg: "bg-emerald-50 dark:bg-emerald-950",
    format: (n: number) => n.toString(),
    sub: () => "Google Forms",
    subColor: "text-muted-foreground",
  },
  {
    key: "parse_accuracy" as const,
    label: "Parse accuracy",
    icon: TrendingUp,
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950",
    format: (n: number) => `${n}%`,
    sub: () => "AI confidence",
    subColor: "text-muted-foreground",
  },
];

export function StatCards({ stats, isLoading }: StatCardsProps) {
  return (
    <motion.div
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
      className="grid grid-cols-2 lg:grid-cols-4 gap-4"
    >
      {STAT_CONFIG.map(({ key, label, icon: Icon, color, bg, format, sub, subColor }) => (
        <motion.div
          key={key}
          variants={fadeUp}
          className="rounded-2xl border border-border bg-card p-5 shadow-card"
        >
          <div className="flex items-start justify-between mb-3">
            <div className={cn("h-9 w-9 rounded-xl flex items-center justify-center", bg)}>
              <Icon className={cn("h-4.5 w-4.5", color)} />
            </div>
          </div>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-7 w-20" />
              <Skeleton className="h-3.5 w-16" />
            </div>
          ) : (
            <>
              <p className="text-2xl font-bold text-foreground">
                {stats ? format(stats[key] as number) : "—"}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
              {stats && (
                <p className={cn("text-xs mt-1 font-medium", subColor)}>
                  {sub(stats)}
                </p>
              )}
            </>
          )}
        </motion.div>
      ))}
    </motion.div>
  );
}

// ─── Difficulty Chart ─────────────────────────────────────────────────────────

interface DifficultyChartProps {
  distribution?: Record<string, number>;
  isLoading: boolean;
}

const DIFF_COLORS = {
  easy: "#10b981",
  medium: "#f59e0b",
  hard: "#ef4444",
};

export function DifficultyChart({ distribution, isLoading }: DifficultyChartProps) {
  const data = distribution
    ? Object.entries(distribution).map(([name, value]) => ({ name, value }))
    : [];
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-card h-full">
      <h3 className="text-sm font-semibold text-foreground mb-4">Difficulty distribution</h3>
      {isLoading ? (
        <div className="space-y-3">
          {["easy", "medium", "hard"].map((d) => (
            <div key={d}>
              <Skeleton className="h-3 w-full mb-1" />
            </div>
          ))}
        </div>
      ) : total > 0 ? (
        <>
          <ResponsiveContainer width="100%" height={120}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={30}
                outerRadius={55}
                paddingAngle={3}
                dataKey="value"
              >
                {data.map((entry) => (
                  <Cell
                    key={entry.name}
                    fill={DIFF_COLORS[entry.name as keyof typeof DIFF_COLORS] ?? "#8b5cf6"}
                  />
                ))}
              </Pie>
              <RTooltip
                formatter={(val: number, name: string) => [
                  `${val} (${Math.round((val / total) * 100)}%)`,
                  name,
                ]}
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid hsl(var(--border))",
                  background: "hsl(var(--card))",
                  color: "hsl(var(--foreground))",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {data.map(({ name, value }) => (
              <div key={name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div
                    className="h-2 w-2 rounded-full"
                    style={{ background: DIFF_COLORS[name as keyof typeof DIFF_COLORS] }}
                  />
                  <span className="text-muted-foreground capitalize">{name}</span>
                </div>
                <span className="font-medium text-foreground">
                  {Math.round((value / total) * 100)}%
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
          <AlertCircle className="h-6 w-6 mb-2" />
          <p className="text-xs">No data yet</p>
        </div>
      )}
    </div>
  );
}

// ─── Recent Projects ──────────────────────────────────────────────────────────

interface RecentProjectsProps {
  projects: Project[];
  isLoading: boolean;
}

export function RecentProjects({ projects, isLoading }: RecentProjectsProps) {
  const recent = projects.slice(0, 5);

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Recent projects</h3>
        <Button variant="ghost" size="sm" asChild className="text-xs -mr-1">
          <Link href="/projects">
            View all
            <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex items-center gap-3">
              <Skeleton className="h-9 w-9 rounded-xl" />
              <div className="flex-1 space-y-1.5">
                <Skeleton className="h-3.5 w-40" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
          ))}
        </div>
      ) : recent.length > 0 ? (
        <div className="space-y-1">
          {recent.map((project) => (
            <Link
              key={project.id}
              href={`/projects/${project.id}/editor`}
              className="flex items-center gap-3 rounded-xl p-2.5 hover:bg-muted/60 transition-colors group"
            >
              <div className="h-9 w-9 rounded-xl bg-accent flex items-center justify-center shrink-0">
                <Folder className="h-4.5 w-4.5 text-accent-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate group-hover:text-primary transition-colors">
                  {project.name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {project.question_count} questions · {formatDate(project.updated_at)}
                </p>
              </div>
              <Badge
                className={cn("text-[10px] shrink-0", getStatusColor(project.status))}
              >
                {getStatusLabel(project.status)}
              </Badge>
            </Link>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <div className="h-10 w-10 rounded-xl bg-muted flex items-center justify-center">
            <Folder className="h-5 w-5 text-muted-foreground" />
          </div>
          <p className="text-sm text-muted-foreground">No projects yet</p>
          <Button size="sm" asChild>
            <Link href="/projects/new">
              <Plus className="h-3.5 w-3.5" />
              Create first project
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}
