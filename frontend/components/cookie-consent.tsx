"use client";

import { useEffect, useState } from "react";
import { ShieldCheck, X, FileText, Check } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";

export default function CookieConsent() {
  const [showBanner, setShowBanner] = useState(false);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem("paisaflow_cookie_consent");
    if (!consent) {
      const timer = setTimeout(() => {
        setShowBanner(true);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, []);

  const acceptConsent = () => {
    localStorage.setItem("paisaflow_cookie_consent", "accepted");
    setShowBanner(false);
  };

  return (
    <>
      {/* 1. Floating Cookie Consent Banner */}
      <AnimatePresence>
        {showBanner && (
          <motion.aside
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 30, scale: 0.95 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            aria-label="Privacy and cookies notice"
            className="fixed bottom-6 right-6 z-50 max-w-sm rounded-2xl border border-white/20 bg-black/90 p-5 shadow-2xl backdrop-blur-2xl sm:max-w-md"
          >
            <div className="flex items-start gap-3.5">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/20 bg-white/10 text-white">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div className="flex-1">
                <h4 className="text-sm font-semibold text-white">
                  Privacy & Session Storage
                </h4>
                <p className="mt-1.5 text-xs leading-relaxed text-neutral-300">
                  PaisaFlow uses local storage to preserve your synthetic persona sessions,
                  categorization rules, and dashboard preferences. No real personal data or
                  third-party tracking cookies are used.
                </p>
                <div className="mt-4 flex flex-wrap items-center gap-2.5">
                  <button
                    onClick={acceptConsent}
                    className="cursor-pointer rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-black transition-all hover:bg-neutral-200"
                  >
                    Accept All
                  </button>
                  <button
                    onClick={() => setShowModal(true)}
                    className="cursor-pointer rounded-full border border-white/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-neutral-300 transition-all hover:bg-white/10 hover:text-white"
                  >
                    Privacy Policy
                  </button>
                </div>
              </div>
              <button
                onClick={acceptConsent}
                aria-label="Dismiss notice"
                className="cursor-pointer text-neutral-400 hover:text-white transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* 2. Privacy Policy Modal */}
      <AnimatePresence>
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.3 }}
              className="relative max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-3xl border border-white/20 bg-[#0A0A0A] p-6 text-white shadow-2xl sm:p-8"
            >
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/20 bg-white/10 text-white">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">
                      PaisaFlow Privacy Policy & Charter
                    </h3>
                    <p className="text-xs text-neutral-400">
                      Effective Date: October 2026 · Version 1.0.0
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowModal(false)}
                  className="rounded-lg p-1.5 text-neutral-400 hover:bg-white/10 hover:text-white transition-colors cursor-pointer"
                  aria-label="Close modal"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mt-6 space-y-5 text-xs sm:text-sm leading-relaxed text-neutral-300">
                <section>
                  <h4 className="font-semibold text-white">1. Synthetic Financial Data Only</h4>
                  <p className="mt-1 text-neutral-400">
                    PaisaFlow is a demonstration and intelligence system operating exclusively
                    on synthetic financial personas and fictional statement records. It never
                    connects to real banking networks, SMS inboxes, email aggregators, payment
                    gateways, or credit information bureaus.
                  </p>
                </section>

                <section>
                  <h4 className="font-semibold text-white">2. No Credentials or Real PII</h4>
                  <p className="mt-1 text-neutral-400">
                    PaisaFlow never requests or stores bank login credentials, UPI PINs, OTPs,
                    card CVVs, or full account numbers. Any files uploaded to the statement
                    ingestion pipeline are processed in temporary memory and strictly validated.
                  </p>
                </section>

                <section>
                  <h4 className="font-semibold text-white">3. Deterministic Arithmetic Guarantee</h4>
                  <p className="mt-1 text-neutral-400">
                    All balances, savings rates, recurring obligations, forecasts, and what-if
                    simulations are computed using deterministic Python Decimal algorithms.
                    AI models (such as Google Gemini) are utilized exclusively for natural
                    language explanations and are never permitted to generate financial numbers.
                  </p>
                </section>

                <section>
                  <h4 className="font-semibold text-white">4. Local Storage & Session State</h4>
                  <p className="mt-1 text-neutral-400">
                    We store your active persona identifier, custom categorization rules, and
                    theme preferences in browser local storage. You may delete this data at any
                    time by resetting your browser state or clicking &ldquo;Reset Demo State&rdquo;.
                  </p>
                </section>
              </div>

              <div className="mt-8 flex justify-end border-t border-white/10 pt-4">
                <button
                  onClick={() => {
                    setShowModal(false);
                    acceptConsent();
                  }}
                  className="inline-flex items-center gap-2 rounded-full bg-white px-5 py-2 text-xs font-semibold text-black hover:bg-neutral-200 transition-colors cursor-pointer"
                >
                  <Check className="h-4 w-4" /> Got it, close policy
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
}

