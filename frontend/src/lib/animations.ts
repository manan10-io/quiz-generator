import type { Variants, Transition } from "framer-motion";

// ─── Shared transitions ───────────────────────────────────────────────────────

export const spring: Transition = {
  type: "spring",
  stiffness: 500,
  damping: 35,
};

export const smooth: Transition = {
  type: "tween",
  ease: [0.25, 0.46, 0.45, 0.94],
  duration: 0.3,
};

export const snappy: Transition = {
  type: "tween",
  ease: [0.4, 0, 0.2, 1],
  duration: 0.2,
};

// ─── Page transitions ─────────────────────────────────────────────────────────

export const pageVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { ...smooth, staggerChildren: 0.06 },
  },
  exit: { opacity: 0, y: -8, transition: { duration: 0.15 } },
};

// ─── Stagger container ────────────────────────────────────────────────────────

export const staggerContainer: Variants = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.05, delayChildren: 0.05 },
  },
};

// ─── Fade up (child) ─────────────────────────────────────────────────────────

export const fadeUp: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: {
    opacity: 1,
    y: 0,
    transition: smooth,
  },
};

// ─── Fade in ─────────────────────────────────────────────────────────────────

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.25 } },
};

// ─── Scale in ────────────────────────────────────────────────────────────────

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.94 },
  visible: {
    opacity: 1,
    scale: 1,
    transition: spring,
  },
};

// ─── Slide in from right ──────────────────────────────────────────────────────

export const slideInRight: Variants = {
  hidden: { opacity: 0, x: 24 },
  visible: { opacity: 1, x: 0, transition: smooth },
  exit: { opacity: 0, x: 24, transition: { duration: 0.15 } },
};

// ─── Slide in from left ───────────────────────────────────────────────────────

export const slideInLeft: Variants = {
  hidden: { opacity: 0, x: -24 },
  visible: { opacity: 1, x: 0, transition: smooth },
};

// ─── Card hover ───────────────────────────────────────────────────────────────

export const cardHover = {
  rest: { y: 0, boxShadow: "0 1px 3px rgba(0,0,0,0.06)" },
  hover: {
    y: -2,
    boxShadow: "0 8px 24px rgba(0,0,0,0.10)",
    transition: snappy,
  },
};

// ─── Question card (list item) ────────────────────────────────────────────────

export const questionItemVariants: Variants = {
  hidden: { opacity: 0, x: -12, scale: 0.98 },
  visible: {
    opacity: 1,
    x: 0,
    scale: 1,
    transition: { ...spring, damping: 30 },
  },
  exit: {
    opacity: 0,
    x: 12,
    scale: 0.96,
    transition: { duration: 0.18 },
  },
};

// ─── Modal / Dialog ───────────────────────────────────────────────────────────

export const modalVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96, y: 8 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: spring,
  },
  exit: {
    opacity: 0,
    scale: 0.96,
    y: 8,
    transition: { duration: 0.15 },
  },
};

export const backdropVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

// ─── Sidebar ──────────────────────────────────────────────────────────────────

export const sidebarVariants: Variants = {
  open: { width: 240, transition: snappy },
  closed: { width: 60, transition: snappy },
};

// ─── Progress bar ─────────────────────────────────────────────────────────────

export const progressBarVariants: Variants = {
  initial: { width: "0%" },
  animate: (pct: number) => ({
    width: `${pct}%`,
    transition: { ...smooth, duration: 0.5 },
  }),
};

// ─── Parsing "constellation" cards animation ───────────────────────────────────

export const parsingCardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.9 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      delay: i * 0.12,
      ...spring,
    },
  }),
};

// ─── Tab content ─────────────────────────────────────────────────────────────

export const tabContentVariants: Variants = {
  hidden: { opacity: 0, y: 6 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.2 } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.15 } },
};

// ─── Toast / Notification ────────────────────────────────────────────────────

export const toastVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: spring,
  },
  exit: {
    opacity: 0,
    y: -10,
    scale: 0.95,
    transition: { duration: 0.15 },
  },
};
