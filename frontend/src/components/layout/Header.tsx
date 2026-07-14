"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Search, Bell, Plus, Command } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useUiStore } from "@/store/uiStore";
import { useQuestionsStore } from "@/store/questionsStore";
import { cn } from "@/lib/utils";

interface HeaderProps {
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  showSearch?: boolean;
}

export function Header({
  title,
  subtitle,
  actions,
  showSearch = false,
}: HeaderProps) {
  const router = useRouter();
  const [searchValue, setSearchValue] = useState("");
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const { isDirty, lastSaved } = useQuestionsStore();

  // Cmd+K to focus search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  return (
    <header className="sticky top-0 z-10 flex h-14 items-center justify-between gap-4 border-b border-border bg-card/80 backdrop-blur-sm px-5">
      {/* Left: Title or search */}
      <div className="flex items-center gap-3 min-w-0 flex-1">
        {title && (
          <div className="min-w-0">
            <h1 className="text-sm font-semibold text-foreground truncate">
              {title}
            </h1>
            {subtitle && (
              <p className="text-xs text-muted-foreground truncate">{subtitle}</p>
            )}
          </div>
        )}

        {showSearch && (
          <div
            className={cn(
              "relative flex items-center transition-all duration-200",
              isSearchFocused ? "w-72" : "w-56"
            )}
          >
            <Search className="absolute left-2.5 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            <Input
              ref={searchRef}
              placeholder="Search questions…"
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onFocus={() => setIsSearchFocused(true)}
              onBlur={() => setIsSearchFocused(false)}
              className="pl-8 pr-16 h-8 text-sm bg-muted/50 border-border/60"
            />
            <kbd className="absolute right-2.5 hidden sm:flex items-center gap-0.5 rounded border border-border bg-background px-1.5 py-0.5 text-[10px] text-muted-foreground font-mono">
              <Command className="h-2.5 w-2.5" />K
            </kbd>
          </div>
        )}
      </div>

      {/* Center: Autosave indicator */}
      <AnimatePresence>
        {isDirty && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-xs text-muted-foreground hidden md:block"
          >
            Unsaved changes
          </motion.span>
        )}
        {!isDirty && lastSaved && (
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="text-xs text-emerald-600 dark:text-emerald-400 hidden md:block"
          >
            ✓ Saved
          </motion.span>
        )}
      </AnimatePresence>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {actions}
        <Button
          asChild
          size="sm"
          className="hidden sm:flex"
        >
          <Link href="/projects/new">
            <Plus className="h-4 w-4" />
            New project
          </Link>
        </Button>
      </div>
    </header>
  );
}
