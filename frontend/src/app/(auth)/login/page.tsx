"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  Sparkles, CheckCircle2, AlertCircle, ArrowLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { LoadingSpinner } from "@/components/common";
import { APP_NAME, APP_TAGLINE } from "@/lib/constants";
import { fadeUp, staggerContainer } from "@/lib/animations";
import Link from "next/link";

const BENEFITS = [
  "Supports PDF, DOCX, images, paste text",
  "AI-powered question extraction",
  "Multi-language OCR (English, Hindi, Gujarati)",
  "Generates Google Form quiz in one click",
  "10 export formats including Moodle & Kahoot",
];

function LoginContent() {
  const { status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isSigningIn, setIsSigningIn] = useState(false);
  const error = searchParams.get("error");

  useEffect(() => {
    if (status === "authenticated") router.push("/dashboard");
  }, [status, router]);

  const handleSignIn = async () => {
    setIsSigningIn(true);
    try {
      await signIn("google", { callbackUrl: "/dashboard" });
    } finally {
      setIsSigningIn(false);
    }
  };

  if (status === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" label="Loading…" />
      </div>
    );
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* ─── Left: Login form ─── */}
      <div className="flex flex-col items-center justify-center px-6 py-12 bg-background">
        <motion.div
          variants={staggerContainer}
          initial="hidden"
          animate="visible"
          className="w-full max-w-sm space-y-8"
        >
          {/* Back link */}
          <motion.div variants={fadeUp}>
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Back to home
            </Link>
          </motion.div>

          {/* Logo + title */}
          <motion.div variants={fadeUp} className="space-y-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary shadow-glow-violet">
              <Sparkles className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-foreground">{APP_NAME}</h1>
              <p className="text-muted-foreground text-sm mt-1">
                Sign in with Google to start generating quizzes
              </p>
            </div>
          </motion.div>

          {/* Error message */}
          {error && (
            <motion.div
              variants={fadeUp}
              className="flex items-center gap-2 rounded-xl border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
            >
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error === "OAuthCallback"
                ? "Authentication failed. Please try again."
                : "An error occurred. Please try again."}
            </motion.div>
          )}

          {/* Sign in button */}
          <motion.div variants={fadeUp}>
            <Button
              size="xl"
              className="w-full"
              onClick={handleSignIn}
              disabled={isSigningIn}
            >
              {isSigningIn ? (
                <LoadingSpinner size="sm" />
              ) : (
                <svg className="h-5 w-5" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
              )}
              {isSigningIn ? "Signing in…" : "Continue with Google"}
            </Button>
          </motion.div>

          {/* Privacy note */}
          <motion.p variants={fadeUp} className="text-xs text-muted-foreground text-center">
            By signing in, you agree to let QuizGen AI create Google Forms in
            your account. We only access forms you explicitly generate.
          </motion.p>

          {/* Benefits */}
          <motion.div variants={staggerContainer} className="space-y-2.5 pt-2">
            {BENEFITS.map((benefit) => (
              <motion.div
                key={benefit}
                variants={fadeUp}
                className="flex items-center gap-2.5 text-sm text-muted-foreground"
              >
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                {benefit}
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </div>

      {/* ─── Right: Decorative panel ─── */}
      <div className="hidden lg:flex flex-col items-center justify-center bg-muted/40 border-l border-border relative overflow-hidden px-12">
        {/* Background dots */}
        <div className="absolute inset-0 dot-grid opacity-60" />
        {/* Gradient orbs */}
        <div className="absolute top-1/4 left-1/4 h-64 w-64 rounded-full bg-primary/10 blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 h-48 w-48 rounded-full bg-violet-400/10 blur-3xl" />

        <div className="relative z-10 max-w-md space-y-6">
          <div className="rounded-2xl border border-border bg-card p-6 shadow-card-hover space-y-4">
            {/* Mock parse output */}
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Parsed questions
              </span>
              <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                ✓ 48 found
              </span>
            </div>
            {[
              { q: "What is the speed of light?", ans: "B", topic: "Physics" },
              { q: "Which gas is most abundant in Earth's atmosphere?", ans: "C", topic: "Chemistry" },
              { q: "Who wrote the Indian Constitution?", ans: "A", topic: "History" },
            ].map((item, i) => (
              <div
                key={i}
                className="flex items-start gap-3 rounded-xl border border-border bg-muted/40 p-3"
              >
                <span className="text-xs font-mono text-primary font-semibold mt-0.5">
                  Q{i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-foreground leading-snug mb-1.5 truncate">
                    {item.q}
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 px-1.5 py-0.5 rounded font-medium">
                      ✓ {item.ans}
                    </span>
                    <span className="text-[10px] bg-accent text-accent-foreground px-1.5 py-0.5 rounded font-medium">
                      {item.topic}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <p className="text-sm text-center text-muted-foreground">
            From any question bank to a live Google quiz —{" "}
            <span className="text-foreground font-medium">in seconds.</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <LoadingSpinner size="lg" label="Loading…" />
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
