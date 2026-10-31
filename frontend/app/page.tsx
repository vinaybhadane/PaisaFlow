"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  Menu,
  X,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  RefreshCw,
  Sliders,
  UploadCloud,
  CheckCircle2,
  Check,
  Plus,
} from "lucide-react";
import { motion, type Variants } from "motion/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

const BASELINE_DINING_SPEND = 6200;

const steps = [
  {
    num: "01",
    title: "Bring your data",
    desc: "Start with a synthetic CSV or PDF statement, or instantly launch one of the built-in demo profiles.",
    icon: UploadCloud,
    shape: "rounded-[36px] sm:rounded-full",
  },
  {
    num: "02",
    title: "Review the picture",
    desc: "Examine extracted transactions, merchant matches, and confidence-calibrated categories before committing.",
    icon: CheckCircle2,
    shape: "rounded-tl-[36px] rounded-br-[36px] rounded-tr-xl rounded-bl-xl",
  },
  {
    num: "03",
    title: "Let the model adapt",
    desc: "Corrections and recurring patterns automatically update the living money model with clear provenance.",
    icon: RefreshCw,
    shape: "rounded-tr-[36px] rounded-bl-[36px] rounded-tl-xl rounded-br-xl",
  },
  {
    num: "04",
    title: "Plan what comes next",
    desc: "Simulate what-if decisions and converse with the Gemini AI Coach using 100% deterministic numbers.",
    icon: Sliders,
    shape: "rounded-[36px]",
  },
];

const faqs = [
  {
    tag: "SECURITY & PRIVACY",
    q: "Is my real financial data safe?",
    a: "PaisaFlow operates strictly on synthetic financial data in this hackathon release. It never connects to real bank accounts, payment APIs, SMS inboxes, or credit bureaus. Your real financial information is never requested or stored.",
  },
  {
    tag: "CADENCE ENGINE",
    q: "How are recurring subscriptions detected?",
    a: "Recurring commitments are identified by a calendar-aware cadence detection engine that accounts for month-length differences and weekend posting shifts. An LLM is never used to detect payments or invent recurring dates.",
  },
  {
    tag: "AI INTEGRITY",
    q: "Does the AI Coach calculate my money or balances?",
    a: "No. In accordance with PaisaFlow non-negotiable principles, Gemini is used strictly for conversational language assistance. All balances, cash flows, savings rates, and scenario projections are calculated deterministically by backend Python Decimal algorithms.",
  },
  {
    tag: "USER CONTROL",
    q: "Can I correct categorization mistakes?",
    a: "Yes. Every transaction category can be corrected with one click. When correcting, you can choose to apply a permanent personalized rule for that merchant, which will take precedence over generic system rules.",
  },
];

function formatINR(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}

// Animation variants
const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 35 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.7, ease: "easeOut" },
  },
};

const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.05,
    },
  },
};

export default function HomePage() {
  const heroRef = useRef<HTMLElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoLoaded, setVideoLoaded] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [reduction, setReduction] = useState(25);
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  // Handle navbar scroll effect
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // GSAP ScrollTrigger for Parallax and video depth
  useEffect(() => {
    if (typeof window === "undefined") return;
    gsap.registerPlugin(ScrollTrigger);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    if (heroRef.current && videoRef.current) {
      const parallaxTween = gsap.to(videoRef.current, {
        yPercent: 18,
        ease: "none",
        scrollTrigger: {
          trigger: heroRef.current,
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });

      return () => {
        parallaxTween.kill();
        ScrollTrigger.getAll().forEach((st) => st.kill());
      };
    }
  }, []);

  // Ensure video autoplays safely
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.playbackRate = 0.95;
      videoRef.current.play().catch(() => {
        // Autoplay policy prevented playback
      });
    }
  }, []);

  const scrollToSection = (id: string) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      element.scrollIntoView({
        behavior: prefersReducedMotion ? "auto" : "smooth",
      });
    }
  };

  const scenario = useMemo(() => {
    const newSpend = BASELINE_DINING_SPEND * (1 - reduction / 100);
    const monthlyDifference = BASELINE_DINING_SPEND - newSpend;
    return {
      newSpend,
      monthlyDifference,
      annualizedDifference: monthlyDifference * 12,
    };
  }, [reduction]);

  return (
    <main className="min-h-screen bg-black text-white selection:bg-white/20 selection:text-white">
      {/* 1. MINIMAL TRANSPARENT NAVIGATION BAR */}
      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? "border-b border-white/10 bg-black/80 backdrop-blur-xl py-4"
            : "border-b border-transparent bg-transparent py-6"
        }`}
      >
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 sm:px-8">
          {/* Left: PaisaFlow Logo (Pure white inverted on dark) and Wordmark */}
          <Link
            href="/"
            className="group flex items-center gap-3 focus-visible:outline-none"
            aria-label="PaisaFlow home"
          >
            <div className="relative flex h-9 w-9 items-center justify-center rounded-xl border border-white/15 bg-white/5 backdrop-blur-md transition-all duration-200 group-hover:border-white/40 group-hover:bg-white/10">
              <Image
                src="/PaisaFlow-white.png"
                alt="PaisaFlow Logo"
                width={32}
                height={32}
                unoptimized
                priority
                className="h-7 w-7 object-contain transition-transform duration-200 group-hover:scale-105"
              />
            </div>
            <span className="text-sm font-bold tracking-[0.22em] text-white uppercase">
              PAISAFLOW
            </span>
          </Link>

          {/* Center Navigation Links */}
          <nav className="hidden items-center gap-10 text-sm font-medium tracking-wide text-neutral-400 md:flex">
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="transition-colors duration-200 hover:text-white cursor-pointer"
            >
              Home
            </button>
            <button
              onClick={() => scrollToSection("problem")}
              className="transition-colors duration-200 hover:text-white cursor-pointer"
            >
              Story
            </button>
            <button
              onClick={() => scrollToSection("how-it-works")}
              className="transition-colors duration-200 hover:text-white cursor-pointer"
            >
              Workflow
            </button>
            <button
              onClick={() => scrollToSection("what-if-demo")}
              className="transition-colors duration-200 hover:text-white cursor-pointer"
            >
              Simulator
            </button>
            <button
              onClick={() => scrollToSection("faq")}
              className="transition-colors duration-200 hover:text-white cursor-pointer"
            >
              FAQ
            </button>
          </nav>

          {/* Right Actions: Log in + Get Started Button */}
          <div className="hidden items-center gap-6 md:flex">
            <Link
              href="/login"
              className="text-sm font-medium text-neutral-300 transition-colors duration-200 hover:text-white"
            >
              Log in
            </Link>
            <Link
              href="/login"
              className="rounded-full bg-white px-5 py-2 text-xs font-semibold text-black transition-all duration-200 hover:bg-neutral-200 hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_20px_rgba(255,255,255,0.15)]"
            >
              Get Started
            </Link>
          </div>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="flex h-10 w-10 items-center justify-center rounded-lg text-neutral-300 transition-colors hover:text-white md:hidden"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* Mobile Navigation Dropdown */}
        {mobileMenuOpen && (
          <div className="border-b border-white/10 bg-black/95 px-6 py-6 backdrop-blur-2xl md:hidden">
            <nav className="flex flex-col gap-4 text-base font-medium text-neutral-300">
              <button
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: "smooth" });
                  setMobileMenuOpen(false);
                }}
                className="text-left py-2 hover:text-white"
              >
                Home
              </button>
              <button
                onClick={() => scrollToSection("problem")}
                className="text-left py-2 hover:text-white"
              >
                Story
              </button>
              <button
                onClick={() => scrollToSection("how-it-works")}
                className="text-left py-2 hover:text-white"
              >
                Workflow
              </button>
              <button
                onClick={() => scrollToSection("what-if-demo")}
                className="text-left py-2 hover:text-white"
              >
                Interactive Simulator
              </button>
              <button
                onClick={() => scrollToSection("faq")}
                className="text-left py-2 hover:text-white"
              >
                Questions & Answers
              </button>
              <div className="mt-4 flex flex-col gap-3 pt-4 border-t border-white/10">
                <Link
                  href="/login"
                  className="rounded-xl border border-white/20 py-2.5 text-center text-sm font-medium text-white"
                >
                  Log in
                </Link>
                <Link
                  href="/login"
                  className="rounded-xl bg-white py-2.5 text-center text-sm font-semibold text-black"
                >
                  Get Started
                </Link>
              </div>
            </nav>
          </div>
        )}
      </header>

      {/* 2. FULL-SCREEN CINEMATIC VIDEO HERO SECTION (60-70% VISIBLE) */}
      <section
        ref={heroRef}
        className="relative flex min-h-screen items-center justify-center overflow-hidden bg-black px-6 pt-24 pb-16 sm:px-8"
      >
        {/* Looping Full-Screen Video Background */}
        <video
          ref={videoRef}
          autoPlay
          muted
          loop
          playsInline
          preload="auto"
          poster="/landingBG_poster.jpg"
          onLoadedData={() => setVideoLoaded(true)}
          className={`absolute inset-0 h-full w-full object-cover z-0 transition-opacity duration-1000 ${
            videoLoaded ? "opacity-100" : "opacity-60"
          }`}
        >
          <source src="/landingBG.mp4" type="video/mp4" />
          Your browser does not support the video tag.
        </video>

        {/* Subtle Dark Overlays for 60-70% Video Visibility and High Readability */}
        <div className="absolute inset-0 z-[1] bg-black/20 pointer-events-none" />
        <div className="absolute inset-0 z-[2] bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.55)_100%)] pointer-events-none" />
        <div className="absolute inset-x-0 bottom-0 h-44 z-[2] bg-gradient-to-t from-black via-black/70 to-transparent pointer-events-none" />

        {/* Hero Content Container */}
        <motion.div
          initial={{ opacity: 0, y: 35 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
          className="relative z-10 mx-auto max-w-5xl text-center"
        >
          {/* Small Top Label */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/[0.06] px-4 py-1.5 text-xs font-semibold tracking-[0.25em] text-neutral-200 backdrop-blur-md mb-6 sm:mb-8"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-white animate-pulse" />
            PERSONAL FINANCE, REIMAGINED
          </motion.div>

          {/* Main Headline with Screen Blending Effect */}
          <motion.h1
            initial={{ opacity: 0, y: 25 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.85, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="font-medium tracking-[-0.04em] text-white drop-shadow-[0_4px_30px_rgba(0,0,0,0.95)]"
            style={{
              fontSize: "clamp(2.75rem, 6.8vw, 5.5rem)",
              lineHeight: "1.05",
              mixBlendMode: "screen",
              textShadow:
                "0 0 35px rgba(255, 255, 255, 0.45), 0 4px 24px rgba(0, 0, 0, 0.9)",
            }}
          >
            Find the money
            <br />
            leaving quietly.
          </motion.h1>

          {/* Supporting Text */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto mt-6 max-w-2xl text-base sm:text-lg font-normal leading-relaxed text-neutral-200 sm:mt-8 drop-shadow-[0_2px_12px_rgba(0,0,0,0.8)]"
          >
            Understand your spending, uncover recurring payments, and make smarter
            financial decisions with an AI-powered personal finance coach.
          </motion.p>

          {/* Primary & Secondary Call to Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="mt-9 flex flex-wrap items-center justify-center gap-4 sm:mt-11"
          >
            <button
              onClick={() => scrollToSection("problem")}
              className="cursor-pointer rounded-full bg-white px-8 py-3.5 text-sm font-semibold text-black transition-all duration-200 hover:bg-neutral-200 hover:scale-[1.02] active:scale-[0.98] shadow-[0_0_30px_rgba(255,255,255,0.25)]"
            >
              Explore PaisaFlow
            </button>
            <Link
              href="/login"
              className="rounded-full border border-white/30 bg-white/[0.08] px-8 py-3.5 text-sm font-medium text-white backdrop-blur-md transition-all duration-200 hover:border-white/50 hover:bg-white/[0.15] hover:scale-[1.02] active:scale-[0.98]"
            >
              Get Started
            </Link>
          </motion.div>

          {/* Trust and Privacy Disclosures (With Lucide SVG Icons, Zero Emojis) */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            className="mt-12 flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-xs text-neutral-400"
          >
            <span className="flex items-center gap-2">
              <Check className="h-3.5 w-3.5 text-white shrink-0" /> 100% Synthetic data
            </span>
            <span className="flex items-center gap-2">
              <Check className="h-3.5 w-3.5 text-white shrink-0" /> Deterministic arithmetic
            </span>
            <span className="flex items-center gap-2">
              <Check className="h-3.5 w-3.5 text-white shrink-0" /> Zero bank credentials
            </span>
          </motion.div>
        </motion.div>
      </section>

      {/* 3. PROBLEM & BENEFIT SECTION — SLIDES IN FROM LEFT ON SCROLL */}
      <section id="problem" className="relative border-t border-white/10 bg-[#050505] py-24 sm:py-32 overflow-hidden">
        <div className="mx-auto max-w-7xl px-6 sm:px-8">
          <motion.div
            initial={{ opacity: 0, x: -120 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
            className="max-w-4xl border-l-2 border-white/30 pl-6 sm:pl-10"
          >
            <motion.p
              initial={{ opacity: 0, x: -60 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="text-xs font-semibold uppercase tracking-[0.25em] text-neutral-400"
            >
              Beyond transaction lists
            </motion.p>
            <motion.h2
              initial={{ opacity: 0, x: -80 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.75, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
              className="mt-4 text-3xl font-medium tracking-tight text-white sm:text-5xl lg:text-6xl"
            >
              Knowing where money went is only the beginning.
            </motion.h2>
            <motion.p
              initial={{ opacity: 0, x: -60 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
              className="mt-6 text-base leading-relaxed text-neutral-300 sm:text-lg max-w-2xl"
            >
              Traditional banking apps give you raw statements and confusing categorization.
              PaisaFlow transforms your financial activity into an evolving, explainable model
              that shows you what actually changed and what lies ahead.
            </motion.p>
          </motion.div>
        </div>
      </section>

      {/* 4. A SIMPLE WORKFLOW — HIGH-VISUAL REDESIGN WITH CUSTOM SHAPES & MODERN TYPOGRAPHY */}
      <section id="how-it-works" className="relative border-t border-white/10 bg-[#050505] py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 sm:px-8">
          <div className="grid gap-16 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
            {/* Left Header Column with High-End Styling */}
            <motion.div
              initial={{ opacity: 0, x: -60 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.8, ease: "easeOut" }}
              className="lg:sticky lg:top-28"
            >
              <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-1.5 font-mono text-xs tracking-[0.25em] text-neutral-300 backdrop-blur-md">
                <Sparkles className="h-3.5 w-3.5 text-white" />
                A SIMPLE WORKFLOW
              </div>
              <h2 className="mt-6 text-3xl font-medium tracking-tight text-white sm:text-5xl lg:text-5xl leading-[1.12]">
                From scattered records to a clear next step.
              </h2>
              <p className="mt-6 text-base leading-relaxed text-neutral-300">
                You stay in complete control. Check extracted transactions, inspect evidence
                behind every recurring pattern, and simulate decisions before spending a rupee.
              </p>
              <div className="mt-10">
                <Link
                  href="/login"
                  className="group inline-flex items-center gap-3 rounded-full bg-white px-8 py-4 text-xs font-bold uppercase tracking-wider text-black transition-all hover:bg-neutral-200 hover:scale-[1.02] shadow-[0_0_30px_rgba(255,255,255,0.2)]"
                >
                  Get Started with PaisaFlow
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </div>
            </motion.div>

            {/* Right Column with Distinct Geometric Shaped Cards */}
            <motion.div
              variants={staggerContainer}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true, margin: "-60px" }}
              className="space-y-6"
            >
              {steps.map((step) => {
                const Icon = step.icon;
                return (
                  <motion.div
                    key={step.num}
                    variants={fadeInUp}
                    whileHover={{ x: 6, transition: { duration: 0.2 } }}
                    className={`relative flex flex-col sm:flex-row sm:items-center gap-6 border border-white/15 bg-gradient-to-r from-white/[0.06] to-transparent p-7 backdrop-blur-xl transition-all hover:border-white/40 hover:bg-white/[0.09] ${step.shape}`}
                  >
                    {/* Glowing Numbered Node */}
                    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-white/25 bg-white/10 text-white shadow-[0_0_20px_rgba(255,255,255,0.1)]">
                      <Icon className="h-6 w-6" />
                    </div>

                    {/* Step Content */}
                    <div className="flex-1">
                      <div className="flex items-center gap-3">
                        <span className="font-mono text-xs font-bold uppercase tracking-widest text-neutral-400">
                          Step {step.num}
                        </span>
                        <div className="h-px w-6 bg-white/20" />
                      </div>
                      <h3 className="mt-1.5 text-lg font-semibold text-white tracking-tight">
                        {step.title}
                      </h3>
                      <p className="mt-2 text-sm leading-relaxed text-neutral-300">
                        {step.desc}
                      </p>
                    </div>
                  </motion.div>
                );
              })}
            </motion.div>
          </div>
        </div>
      </section>

      {/* 5. INTERACTIVE DETERMINISTIC WHAT-IF SIMULATOR */}
      <section id="what-if-demo" className="relative border-t border-white/10 bg-[#050505] py-24 sm:py-32">
        <div className="mx-auto max-w-7xl px-6 sm:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="mx-auto max-w-3xl text-center"
          >
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-neutral-400">
              Interactive Simulator
            </p>
            <h2 className="mt-4 text-3xl font-medium tracking-tight text-white sm:text-5xl">
              Small changes become easy to visualize.
            </h2>
            <p className="mt-6 text-base leading-relaxed text-neutral-400">
              Explore an illustrative dining spend reduction scenario. This preview uses
              deterministic Decimal arithmetic and never touches real records.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 35 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-60px" }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="mx-auto mt-14 grid max-w-4xl gap-8 rounded-3xl border border-white/15 bg-[#0A0A0A] p-7 shadow-[0_20px_80px_-40px_rgba(0,0,0,0.8)] sm:p-10 md:grid-cols-[1fr_0.9fr]"
          >
            {/* Control Panel */}
            <div className="flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <label htmlFor="dining-slider" className="text-sm font-medium text-white">
                    Reduce dining spend by
                  </label>
                  <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1 font-mono text-xs font-bold text-white">
                    {reduction}%
                  </span>
                </div>

                <input
                  id="dining-slider"
                  type="range"
                  min="0"
                  max="60"
                  step="5"
                  value={reduction}
                  onChange={(e) => setReduction(Number(e.target.value))}
                  className="mt-6 w-full accent-white cursor-pointer"
                />

                <div className="mt-2 flex justify-between font-mono text-[11px] text-neutral-500">
                  <span>0%</span>
                  <span>30%</span>
                  <span>60%</span>
                </div>

                <div className="mt-8 rounded-2xl border border-white/10 bg-black/50 p-4">
                  <p className="text-xs text-neutral-400">Baseline dining spend</p>
                  <p className="mt-1 text-xl font-medium text-white">
                    {formatINR(BASELINE_DINING_SPEND)} / month
                  </p>
                  <p className="mt-2 text-[11px] leading-relaxed text-neutral-500">
                    Calculated using synthetic demo records. In the live app, your real
                    categorized expenses form the baseline.
                  </p>
                </div>
              </div>

              <div className="mt-6 flex items-center gap-2 text-xs text-neutral-500">
                <span className="text-neutral-400">
                  Deterministic calculation logic: difference = baseline * (reduction / 100)
                </span>
              </div>
            </div>

            {/* Results Card */}
            <div className="flex flex-col justify-between rounded-2xl border border-white/15 bg-white/[0.04] p-6 backdrop-blur-md">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">
                  Potential Monthly Difference
                </p>
                <p className="mt-2 text-4xl font-semibold tracking-tight text-white">
                  {formatINR(scenario.monthlyDifference)}
                </p>

                <div className="my-6 border-t border-white/10" />

                <div className="space-y-3.5 text-sm">
                  <div className="flex justify-between">
                    <span className="text-neutral-400">New monthly spend</span>
                    <span className="font-medium text-white">{formatINR(scenario.newSpend)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-neutral-400">Illustrative 12-month effect</span>
                    <span className="font-semibold text-white">
                      {formatINR(scenario.annualizedDifference)}
                    </span>
                  </div>
                </div>
              </div>

              <p className="mt-8 text-[11px] leading-relaxed text-neutral-500">
                Assumes the same reduction is maintained for 12 months. This is an illustrative
                simulation, not financial advice or a return guarantee.
              </p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* 8. PRIVACY AND TRUST SECTION */}
      <section id="privacy" className="relative border-t border-white/10 bg-black py-24 sm:py-32">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease: "easeOut" }}
          className="mx-auto max-w-4xl px-6 text-center sm:px-8"
        >
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-white/20 bg-white/5 text-white">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h2 className="mt-6 text-3xl font-medium tracking-tight text-white sm:text-4xl">
            Clarity starts with trust.
          </h2>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-neutral-400">
            PaisaFlow operates strictly on synthetic financial data. It never initiates real
            bank transfers, requests payment credentials, or performs automatic subscription
            cancellations. All financial arithmetic is deterministic; AI language models are
            employed exclusively to explain validated results.
          </p>
        </motion.div>
      </section>

      {/* 7. FAQ SECTION (MODERN INTERACTIVE ACCORDION) */}
      <section id="faq" className="relative border-t border-white/10 bg-[#050505] py-24 sm:py-32 overflow-hidden">
        {/* Subtle ambient lighting */}
        <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-[500px] w-[500px] rounded-full bg-white/[0.02] blur-3xl" />

        <div className="relative mx-auto max-w-4xl px-6 sm:px-8">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className="text-center"
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-1.5 font-mono text-xs tracking-[0.25em] text-neutral-300 backdrop-blur-md mb-4">
              <Sparkles className="h-3.5 w-3.5 text-white" />
              QUESTIONS & ANSWERS
            </div>
            <h2 className="text-3xl font-medium tracking-tight text-white sm:text-5xl">
              Frequently asked questions.
            </h2>
            <p className="mt-4 text-sm text-neutral-400 max-w-lg mx-auto">
              Everything you need to know about our deterministic financial calculations, privacy principles, and Gemini AI Coach.
            </p>
          </motion.div>

          <div className="mt-14 space-y-4">
            {faqs.map((faq, index) => {
              const isOpen = openFaqIndex === index;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.08 }}
                  className={`group rounded-3xl border transition-all duration-300 overflow-hidden ${
                    isOpen
                      ? "border-white/30 bg-[#0E0E0E] shadow-[0_0_40px_rgba(255,255,255,0.06)]"
                      : "border-white/10 bg-[#0A0A0A] hover:border-white/20 hover:bg-[#0C0C0C]"
                  }`}
                >
                  <button
                    onClick={() => setOpenFaqIndex(isOpen ? null : index)}
                    className="flex w-full items-center justify-between gap-4 p-6 sm:p-7 text-left cursor-pointer"
                    aria-expanded={isOpen}
                  >
                    <div className="space-y-1.5">
                      <span className="font-mono text-[10px] font-bold tracking-[0.2em] uppercase text-neutral-400">
                        {faq.tag}
                      </span>
                      <h3 className="text-base sm:text-lg font-semibold text-white tracking-tight">
                        {faq.q}
                      </h3>
                    </div>
                    <div
                      className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition-all duration-300 ${
                        isOpen
                          ? "border-white bg-white text-black rotate-45"
                          : "border-white/20 bg-white/5 text-neutral-300 group-hover:border-white/40 group-hover:text-white"
                      }`}
                    >
                      <Plus className="h-4 w-4" />
                    </div>
                  </button>

                  {isOpen && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3, ease: "easeOut" }}
                      className="border-t border-white/10 px-6 sm:px-7 pb-7 pt-4"
                    >
                      <p className="text-sm leading-relaxed text-neutral-300 sm:text-base font-normal">
                        {faq.a}
                      </p>
                    </motion.div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 8. MINIMAL MONOCHROME FOOTER */}
      <footer className="border-t border-white/10 bg-black py-12">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-6 px-6 sm:px-8 md:flex-row">
          <div className="flex items-center gap-3">
            <Image
              src="/PaisaFlow-white.png"
              alt="PaisaFlow Logo"
              width={30}
              height={30}
              unoptimized
              className="h-7 w-7 object-contain"
            />
            <span className="text-xs font-bold uppercase tracking-[0.2em] text-white">
              PAISAFLOW
            </span>
          </div>

          <p className="text-xs text-neutral-400">
            Your Money. Your Flow. Your Future.
          </p>

          <div className="flex items-center gap-6 text-xs text-neutral-500">
            <Link href="/login" className="hover:text-neutral-300 transition-colors">
              Live Dashboard
            </Link>
            <button
              onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
              className="hover:text-neutral-300 transition-colors cursor-pointer"
            >
              Back to top ↑
            </button>
            <span>Synthetic demo only</span>
          </div>
        </div>
      </footer>
    </main>
  );
}
