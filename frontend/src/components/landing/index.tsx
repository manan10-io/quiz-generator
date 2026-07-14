"use client";

import { motion } from "framer-motion";
import { signIn } from "next-auth/react";
import {
  FileText, Image, Zap, BrainCircuit, SlidersHorizontal,
  Download, Globe, Shield, Sparkles, ArrowRight,
  ClipboardPaste, CheckCheck, Settings2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { staggerContainer, fadeUp } from "@/lib/animations";

// ─── Feature Grid ─────────────────────────────────────────────────────────────

const FEATURES = [
  {
    icon: ClipboardPaste,
    title: "7 input formats",
    desc: "Paste text, upload PDF, DOCX, TXT, CSV, images, or screenshots — all supported.",
    color: "text-violet-500",
    bg: "bg-violet-50 dark:bg-violet-950",
  },
  {
    icon: BrainCircuit,
    title: "AI-powered parsing",
    desc: "Detects questions, options, answers, marks, topics, and difficulty automatically.",
    color: "text-sky-500",
    bg: "bg-sky-50 dark:bg-sky-950",
  },
  {
    icon: Image,
    title: "Multi-language OCR",
    desc: "Extract text from scanned PDFs and images in English, Hindi, and Gujarati.",
    color: "text-emerald-500",
    bg: "bg-emerald-50 dark:bg-emerald-950",
  },
  {
    icon: SlidersHorizontal,
    title: "Rich question editor",
    desc: "Edit, reorder with drag-and-drop, set marks, topics, difficulty, and explanations.",
    color: "text-amber-500",
    bg: "bg-amber-50 dark:bg-amber-950",
  },
  {
    icon: Globe,
    title: "Google Forms quiz",
    desc: "Generates a quiz with answer keys, marks, quiz mode, shuffle — all pre-configured.",
    color: "text-red-500",
    bg: "bg-red-50 dark:bg-red-950",
  },
  {
    icon: Download,
    title: "10 export formats",
    desc: "PDF, DOCX, Excel, CSV, JSON, Moodle XML, Quizizz CSV, Kahoot CSV, and more.",
    color: "text-indigo-500",
    bg: "bg-indigo-50 dark:bg-indigo-950",
  },
  {
    icon: Zap,
    title: "Instant validation",
    desc: "Flags missing answers, duplicate questions, empty options, and numbering errors.",
    color: "text-orange-500",
    bg: "bg-orange-50 dark:bg-orange-950",
  },
  {
    icon: Shield,
    title: "Private & secure",
    desc: "Your questions never leave your Google account. OAuth2 with offline access.",
    color: "text-teal-500",
    bg: "bg-teal-50 dark:bg-teal-950",
  },
];

export function FeatureGrid() {
  return (
    <section className="py-20 px-4 bg-muted/30">
      <div className="max-w-6xl mx-auto">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          className="text-center mb-12"
        >
          <motion.p variants={fadeUp} className="text-xs font-semibold text-primary uppercase tracking-widest mb-3">
            Features
          </motion.p>
          <motion.h2 variants={fadeUp} className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Everything teachers need
          </motion.h2>
          <motion.p variants={fadeUp} className="text-muted-foreground max-w-lg mx-auto">
            From a raw question bank to a live Google quiz — every step is automated.
          </motion.p>
        </motion.div>

        <motion.div
          variants={staggerContainer}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "-80px" }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          {FEATURES.map(({ icon: Icon, title, desc, color, bg }) => (
            <motion.div
              key={title}
              variants={fadeUp}
              className="rounded-2xl border border-border bg-card p-5 hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200"
            >
              <div className={`h-10 w-10 rounded-xl ${bg} flex items-center justify-center mb-4`}>
                <Icon className={`h-5 w-5 ${color}`} />
              </div>
              <h3 className="font-semibold text-foreground mb-1.5 text-sm">{title}</h3>
              <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  );
}

// ─── How It Works ─────────────────────────────────────────────────────────────

const STEPS = [
  {
    num: "01",
    icon: ClipboardPaste,
    title: "Import your questions",
    desc: "Paste MCQ text, upload a PDF/DOCX/image, or drop a scanned paper. QuizGen handles any format — even messy OCR output.",
    highlights: ["Paste or drag-drop", "PDF with text layer", "Scanned images (OCR)", "Hindi & Gujarati text"],
  },
  {
    num: "02",
    icon: BrainCircuit,
    title: "AI extracts & cleans",
    desc: "The parser detects questions, options, correct answers, marks, and topics. AI repairs broken lines, merges split questions, and removes duplicates.",
    highlights: ["7 format patterns", "AI repair", "Answer detection", "Duplicate removal"],
  },
  {
    num: "03",
    icon: Settings2,
    title: "Review & edit",
    desc: "Preview all extracted questions in a beautiful card view. Edit anything, reorder with drag-and-drop, and fix any flagged warnings before generating.",
    highlights: ["Drag-drop reorder", "Inline edit", "Warning flags", "Search & filter"],
  },
  {
    num: "04",
    icon: CheckCheck,
    title: "Generate Google Form",
    desc: "One click generates a fully configured Google Form quiz with answer keys, marks, quiz mode enabled, shuffle options, and your confirmation message.",
    highlights: ["Quiz mode", "Answer keys", "Marks per question", "Shuffle options"],
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-20 px-4">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-14"
        >
          <p className="text-xs font-semibold text-primary uppercase tracking-widest mb-3">
            How it works
          </p>
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            From messy text to live quiz in 4 steps
          </h2>
        </motion.div>

        <div className="relative">
          {/* Connecting line */}
          <div className="absolute left-[39px] top-10 bottom-10 w-px bg-border hidden md:block" />

          <div className="space-y-8">
            {STEPS.map(({ num, icon: Icon, title, desc, highlights }, i) => (
              <motion.div
                key={num}
                initial={{ opacity: 0, x: -16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ delay: i * 0.1 }}
                className="flex gap-6 relative"
              >
                {/* Step number circle */}
                <div className="flex-shrink-0 flex h-20 w-20 items-center justify-center rounded-2xl bg-card border border-border shadow-card relative z-10">
                  <div className="text-center">
                    <Icon className="h-5 w-5 text-primary mx-auto mb-1" />
                    <span className="text-[10px] font-mono text-muted-foreground">{num}</span>
                  </div>
                </div>

                {/* Content */}
                <div className="flex-1 pt-2">
                  <h3 className="text-base font-semibold text-foreground mb-1.5">{title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed mb-3">{desc}</p>
                  <div className="flex flex-wrap gap-2">
                    {highlights.map((h) => (
                      <span
                        key={h}
                        className="text-xs bg-accent text-accent-foreground px-2.5 py-1 rounded-full font-medium"
                      >
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

// ─── CTA Section ──────────────────────────────────────────────────────────────

export function CTASection() {
  return (
    <section className="py-20 px-4 bg-muted/30">
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="max-w-2xl mx-auto text-center"
      >
        <div className="inline-flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 mb-6">
          <Sparkles className="h-7 w-7 text-primary" />
        </div>
        <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
          Start generating quizzes today
        </h2>
        <p className="text-muted-foreground mb-8 text-lg">
          Sign in with Google and generate your first quiz in under 60 seconds.
          No setup required.
        </p>
        <Button
          size="xl"
          onClick={() => signIn("google", { callbackUrl: "/dashboard" })}
          className="shadow-glow-violet"
        >
          <svg className="h-4 w-4" viewBox="0 0 24 24">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
          </svg>
          Get started free
          <ArrowRight className="h-4 w-4" />
        </Button>
        <p className="text-xs text-muted-foreground mt-4">
          Your Google account data stays private. We only store what you create.
        </p>
      </motion.div>
    </section>
  );
}
