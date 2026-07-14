"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Sparkles, Zap, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fadeUp, staggerContainer, parsingCardVariants } from "@/lib/animations";
import { signIn } from "next-auth/react";

const DEMO_QUESTIONS = [
  { num: 1, text: "What is the speed of light in vacuum?", answer: "B", topic: "Physics" },
  { num: 2, text: "Which planet is the largest in the Solar System?", answer: "A", topic: "Science" },
  { num: 3, text: "What is the chemical formula of water?", answer: "C", topic: "Chemistry" },
];

const DEMO_TEXT = `1. What is the speed of light in vacuum?
A. 3 × 10⁶ m/s
B. 3 × 10⁸ m/s
C. 3 × 10¹⁰ m/s
D. 3 × 10⁴ m/s
Answer: B

2. Which planet is the largest in the Solar System?
A. Jupiter
B. Saturn
C. Neptune
D. Uranus
Ans: A`;

export function Hero() {
  const [isAnimating, setIsAnimating] = useState(false);
  const [visibleCards, setVisibleCards] = useState<number[]>([]);
  const [typedText, setTypedText] = useState("");

  // Typewriter effect for demo text
  useEffect(() => {
    let i = 0;
    const timer = setInterval(() => {
      setTypedText(DEMO_TEXT.slice(0, i));
      i++;
      if (i > DEMO_TEXT.length) {
        clearInterval(timer);
        setTimeout(() => {
          setIsAnimating(true);
          // Stagger cards in
          DEMO_QUESTIONS.forEach((_, idx) => {
            setTimeout(
              () => setVisibleCards((prev) => [...prev, idx]),
              idx * 300
            );
          });
        }, 600);
      }
    }, 18);
    return () => clearInterval(timer);
  }, []);

  return (
    <section className="relative overflow-hidden pt-20 pb-24 hero-gradient">
      {/* Background grid */}
      <div className="absolute inset-0 dot-grid opacity-40" />

      <div className="relative max-w-6xl mx-auto px-4">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="text-center mb-16"
        >
          {/* Pill badge */}
          <motion.div variants={fadeUp} className="flex justify-center mb-6">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-accent text-accent-foreground px-3 py-1 text-xs font-medium border border-accent/50">
              <Sparkles className="h-3 w-3" />
              AI-powered · Google Forms · One click
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            variants={fadeUp}
            className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground tracking-tight mb-6 leading-[1.1]"
          >
            Turn any question bank into a{" "}
            <span className="gradient-text">Google Quiz</span>
            {" "}in seconds
          </motion.h1>

          <motion.p
            variants={fadeUp}
            className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8 leading-relaxed"
          >
            Paste or upload MCQ text, PDFs, images, or scanned papers.
            QuizGen AI extracts every question, detects answers, and generates
            a fully configured Google Form quiz with answer keys — automatically.
          </motion.p>

          {/* CTA buttons */}
          <motion.div
            variants={fadeUp}
            className="flex flex-col sm:flex-row gap-3 justify-center"
          >
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
              Continue with Google
            </Button>
            <Button size="xl" variant="outline" asChild>
              <a href="#how-it-works">
                See how it works
                <ArrowRight className="h-4 w-4" />
              </a>
            </Button>
          </motion.div>

          {/* Trust signals */}
          <motion.div
            variants={fadeUp}
            className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-8 text-xs text-muted-foreground"
          >
            {["No credit card", "7 input formats", "10 export types", "Hindi & Gujarati OCR"].map(
              (item) => (
                <span key={item} className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  {item}
                </span>
              )
            )}
          </motion.div>
        </motion.div>

        {/* ─── Live demo widget ─── */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.5 }}
          className="max-w-4xl mx-auto"
        >
          <div className="rounded-2xl border border-border bg-card shadow-card overflow-hidden">
            {/* Window chrome */}
            <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border bg-muted/50">
              <div className="h-2.5 w-2.5 rounded-full bg-red-400" />
              <div className="h-2.5 w-2.5 rounded-full bg-amber-400" />
              <div className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
              <span className="text-xs text-muted-foreground ml-2 font-mono">
                QuizGen AI — Live demo
              </span>
              {isAnimating && (
                <span className="ml-auto flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                  <Zap className="h-3 w-3" />
                  Parsed in 1.2s
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 min-h-[280px]">
              {/* Input side */}
              <div className="border-r border-border p-5">
                <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                  Input — paste any MCQ text
                </p>
                <pre className="text-xs text-foreground/80 font-mono leading-relaxed whitespace-pre-wrap break-words">
                  {typedText}
                  <span className="inline-block w-0.5 h-3.5 bg-primary animate-pulse align-middle ml-0.5" />
                </pre>
              </div>

              {/* Output side */}
              <div className="p-5 bg-muted/20">
                <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                  Output — extracted questions
                </p>
                <div className="space-y-2.5">
                  <AnimatePresence>
                    {visibleCards.map((idx) => {
                      const q = DEMO_QUESTIONS[idx];
                      return (
                        <motion.div
                          key={idx}
                          variants={parsingCardVariants}
                          initial="hidden"
                          animate="visible"
                          custom={idx}
                          className="rounded-xl border border-border bg-card p-3 shadow-card"
                        >
                          <div className="flex items-start justify-between gap-2 mb-1.5">
                            <span className="text-xs font-semibold text-primary">
                              Q{q.num}
                            </span>
                            <span className="text-[10px] bg-accent text-accent-foreground px-1.5 py-0.5 rounded-md font-medium">
                              {q.topic}
                            </span>
                          </div>
                          <p className="text-xs text-foreground mb-2 leading-snug">
                            {q.text}
                          </p>
                          <div className="flex items-center gap-1.5">
                            <span className="text-[10px] bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 px-1.5 py-0.5 rounded border border-emerald-200 dark:border-emerald-800 font-medium">
                              ✓ Answer: {q.answer}
                            </span>
                            <span className="text-[10px] text-muted-foreground">
                              1 mark
                            </span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </AnimatePresence>
                  {!isAnimating && visibleCards.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-40 text-center gap-2">
                      <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
                      <p className="text-xs text-muted-foreground">
                        Waiting for input…
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
