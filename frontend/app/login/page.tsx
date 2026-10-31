"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { ShieldCheck, ArrowLeft, AlertCircle } from "lucide-react";
import { motion } from "motion/react";
import { auth, loginWithGoogle, onAuthStateChanged, type FirebaseUser } from "@/lib/firebase";
import { setActiveUserId } from "@/lib/api";

function GoogleLogo() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z"
      />
      <path
        fill="#34A853"
        d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
      />
      <path
        fill="#FBBC05"
        d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.98 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
      />
      <path
        fill="#EA4335"
        d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
      />
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState<boolean>(false);
  const [checkingAuth, setCheckingAuth] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // If already logged in, redirect straight to dashboard
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user: FirebaseUser | null) => {
      if (user) {
        setActiveUserId(user.uid, user.email, user.displayName);
        router.replace("/dashboard");
      } else {
        setCheckingAuth(false);
      }
    });
    return () => unsubscribe();
  }, [router]);

  const handleGoogleLogin = async () => {
    setError(null);
    setLoading(true);
    try {
      const user = await loginWithGoogle();
      setActiveUserId(user.uid, user.email, user.displayName);
      router.replace("/dashboard");
    } catch (err: unknown) {
      console.error("Firebase Google login error:", err);
      const msg = err instanceof Error ? err.message : "Authentication cancelled or failed";
      setError(msg);
      setLoading(false);
    }
  };

  if (checkingAuth) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
          <p className="font-mono text-xs uppercase tracking-widest text-neutral-400">Verifying session...</p>
        </div>
      </div>
    );
  }

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-black px-6 py-12 text-white selection:bg-white/20 selection:text-white">
      {/* Ambient background glows */}
      <div className="pointer-events-none absolute -top-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-white/[0.04] blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 left-1/2 h-96 w-96 -translate-x-1/2 rounded-full bg-white/[0.02] blur-3xl" />

      {/* Top back link */}
      <div className="absolute top-6 left-6 z-20">
        <Link
          href="/"
          className="group inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-medium text-neutral-400 backdrop-blur-md transition-all hover:border-white/30 hover:bg-white/10 hover:text-white"
        >
          <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-1" />
          Back to home
        </Link>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 25 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full max-w-md"
      >
        {/* Card Header */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center gap-3 group">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/20 bg-white/5 backdrop-blur-md transition-all group-hover:border-white/40 group-hover:bg-white/10">
              <Image
                src="/PaisaFlow-white.png"
                alt="PaisaFlow Logo"
                width={36}
                height={36}
                unoptimized
                priority
                className="h-8 w-8 object-contain"
              />
            </div>
            <span className="text-base font-bold tracking-[0.25em] text-white uppercase">
              PAISAFLOW
            </span>
          </Link>

          <h1 className="mt-8 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
            Welcome to PaisaFlow
          </h1>
          <p className="mt-2 text-xs text-neutral-400 leading-relaxed max-w-sm mx-auto">
            Sign in to access your living financial model and converse with your PaisaFlow AI financial coach.
          </p>
        </div>

        {/* Login Box */}
        <div className="mt-8 rounded-3xl border border-white/15 bg-[#0A0A0A]/90 p-8 shadow-[0_0_50px_rgba(0,0,0,0.8)] backdrop-blur-xl">
          {error && (
            <div className="mb-6 flex items-start gap-3 rounded-2xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-200">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-4">
            <button
              onClick={handleGoogleLogin}
              disabled={loading}
              className="group relative flex w-full items-center justify-center gap-3 rounded-full border border-white/20 bg-white py-3.5 px-6 text-sm font-semibold text-black transition-all hover:bg-neutral-200 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 cursor-pointer shadow-[0_0_25px_rgba(255,255,255,0.15)]"
            >
              {loading ? (
                <div className="h-5 w-5 animate-spin rounded-full border-2 border-black/30 border-t-black" />
              ) : (
                <>
                  <GoogleLogo />
                  <span>Continue with Google</span>
                </>
              )}
            </button>
          </div>

          <div className="mt-8 border-t border-white/10 pt-6">
            <div className="flex items-center gap-2 text-xs text-neutral-400">
              <ShieldCheck className="h-4 w-4 text-white shrink-0" />
              <span>Privacy & Synthetic Data Guarantee</span>
            </div>
            <p className="mt-2 text-[11px] leading-relaxed text-neutral-500">
              PaisaFlow processes all figures deterministically from uploaded statements. Real bank credentials, UPI PINs, and passwords are never requested or stored.
            </p>
          </div>
        </div>

        {/* Footer info */}
        <p className="mt-8 text-center font-mono text-[11px] uppercase tracking-wider text-neutral-400">
          Personal Finance • AI Coach • Living Money Model
        </p>
      </motion.div>
    </main>
  );
}

