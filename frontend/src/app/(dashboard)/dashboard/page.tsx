"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useSession } from "next-auth/react";
import { FilePlus, Sparkles, ArrowRight } from "lucide-react";
import { Header } from "@/components/layout/Header";
import { Button } from "@/components/ui/button";
import { StatCards, DifficultyChart, RecentProjects } from "@/components/dashboard";
import { pageVariants, staggerContainer, fadeUp } from "@/lib/animations";
import { useDashboard, useProjects } from "@/hooks";

export default function DashboardPage() {
  const { data: session } = useSession();
  const { data: stats, isLoading: statsLoading } = useDashboard();
  const { projects, isLoading: projectsLoading } = useProjects();

  const firstName = session?.user?.name?.split(" ")[0] ?? "there";
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <>
      <Header
        title={`${greeting}, ${firstName} 👋`}
        subtitle="Here's what's happening with your quizzes"
        actions={
          <Button variant="outline" size="sm" asChild>
            <Link href="/projects/new">
              <FilePlus className="h-4 w-4" />
              New project
            </Link>
          </Button>
        }
      />

      <motion.div
        variants={pageVariants}
        initial="hidden"
        animate="visible"
        className="p-5 space-y-6"
      >
        {/* ─── Stat cards ─── */}
        <StatCards stats={stats} isLoading={statsLoading} />

        {/* ─── Quick actions ─── */}
        <motion.div variants={staggerContainer} className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {[
            {
              href: "/projects/new",
              icon: FilePlus,
              label: "New project",
              desc: "Import a question bank",
              color: "text-violet-500",
              bg: "bg-violet-50 dark:bg-violet-950",
            },
            {
              href: "/projects",
              icon: Sparkles,
              label: "My projects",
              desc: "View all projects",
              color: "text-sky-500",
              bg: "bg-sky-50 dark:bg-sky-950",
            },
            {
              href: "/history",
              icon: ArrowRight,
              label: "History",
              desc: "Generated forms & exports",
              color: "text-emerald-500",
              bg: "bg-emerald-50 dark:bg-emerald-950",
            },
          ].map(({ href, icon: Icon, label, desc, color, bg }) => (
            <motion.div key={href} variants={fadeUp}>
              <Link
                href={href}
                className="flex items-center gap-3 rounded-2xl border border-border bg-card p-4 shadow-card hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200 group"
              >
                <div className={`h-9 w-9 rounded-xl ${bg} flex items-center justify-center shrink-0`}>
                  <Icon className={`h-4.5 w-4.5 ${color}`} />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                    {label}
                  </p>
                  <p className="text-xs text-muted-foreground truncate">{desc}</p>
                </div>
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* ─── Main content grid ─── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2">
            <RecentProjects
              projects={projects}
              isLoading={projectsLoading}
            />
          </div>
          <div>
            <DifficultyChart
              distribution={stats?.difficulty_distribution}
              isLoading={statsLoading}
            />
          </div>
        </div>
      </motion.div>
    </>
  );
}
