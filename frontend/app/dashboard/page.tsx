"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import {
  CategoryItem,
  CategorySpendingResponse,
  CoachConversationSummary,
  CoachMessage,
  FinancialForecastResponse,
  FinancialInsight,
  ImportCandidate,
  ImportPreviewData,
  LivingProfileData,
  MonthlyTrendItem,
  paisaApi,
  RecurringCommitmentItem,
  SavedScenario,
  setActiveUserId,
  SimulationRunResponse,
  TransactionItem,
} from "@/lib/api";
import {
  auth,
  loginWithGoogle,
  logoutFirebase,
  onAuthStateChanged,
  type FirebaseUser,
} from "@/lib/firebase";
import {
  LayoutDashboard,
  UploadCloud,
  CreditCard,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Compass,
  Sliders,
  Bot,
  AlertTriangle,
  Sparkles,
  MessageSquare,
  BarChart3,
  FileText,
  CheckCircle2,
  Check,
  Search,
  Filter,
  ArrowRight,
  LogOut,
  Download,
  X,
  Calendar,
  Send,
  Layers,
  ShieldCheck,
  User as UserIcon,
} from "lucide-react";
import { FloatingTooltip } from "@/components/unlumen-ui/floating-tooltip";

function formatCurrency(val: string | number) {
  const num = typeof val === "string" ? parseFloat(val) : val;
  if (isNaN(num)) return "₹0.00";
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(num);
}

function renderFormattedMessage(text: string, isUser = false) {
  if (!text) return null;
  const lines = text.split("\n");

  return (
    <div className="space-y-1.5">
      {lines.map((line, lineIdx) => {
        if (!line.trim()) {
          return <div key={lineIdx} className="h-1.5" />;
        }
        const parts = line.split(/(\*\*.*?\*\*)/g);
        return (
          <p key={lineIdx} className="leading-relaxed">
            {parts.map((part, partIdx) => {
              if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
                const boldText = part.slice(2, -2);
                return (
                  <strong
                    key={partIdx}
                    className={isUser ? "font-bold text-black" : "font-bold text-white"}
                  >
                    {boldText}
                  </strong>
                );
              }
              return <span key={partIdx}>{part}</span>;
            })}
          </p>
        );
      })}
    </div>
  );
}

function GoogleLogo({ className }: { className?: string }) {
  return (
    <svg className={className || "h-4 w-4"} viewBox="0 0 24 24">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
      />
    </svg>
  );
}

const DEFAULT_WELCOME_MESSAGE: CoachMessage = {
  id: "welcome-default",
  conversation_id: "default",
  sender: "coach",
  content:
    "Hello! I am your **PaisaFlow AI Financial Coach**, powered live by **Google Gemini 3.5 Flash Lite**.\n\nI analyze your cash flow, recurring commitments, and savings rate grounded exclusively in your uploaded financial statements with deterministic Decimal arithmetic.\n\nAsk me any question below, or select a suggested prompt to explore your statement.",
  created_at: new Date().toISOString(),
  is_live_gemini: true,
  warnings: ["PaisaFlow is a personal finance intelligence coach. Not certified SEBI advice."],
};

export default function DashboardPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<
    "overview" | "imports" | "transactions" | "recurring" | "insights" | "forecast" | "simulator" | "coach"
  >("overview");

  // Firebase Authentication State
  const [user, setUser] = useState<FirebaseUser | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(true);

  // Living Profile & Overview State
  const [profile, setProfile] = useState<LivingProfileData | null>(null);

  // Transactions State
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [transactionsTotal, setTransactionsTotal] = useState<number>(0);
  const [transactionsPage, setTransactionsPage] = useState<number>(1);
  const [transactionsSearch, setTransactionsSearch] = useState<string>("");
  const [selectedFilterCategory, setSelectedFilterCategory] = useState<string>("");
  const [categories, setCategories] = useState<CategoryItem[]>([]);

  // Category Correction Modal State
  const [correctingTx, setCorrectingTx] = useState<TransactionItem | null>(null);
  const [newCategoryId, setNewCategoryId] = useState<string>("");
  const [createFutureRule, setCreateFutureRule] = useState<boolean>(true);
  const [futureScopeType, setFutureScopeType] = useState<string>("exact_merchant");
  const [correctionLoading, setCorrectionLoading] = useState<boolean>(false);

  // Transaction Explanation Modal State
  const [explainingTx, setExplainingTx] = useState<{
    tx: TransactionItem;
    explanation: Record<string, unknown>;
  } | null>(null);
  const [explainingLoading, setExplainingLoading] = useState<boolean>(false);

  // Statement Ingestion State
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState<boolean>(false);
  const [importPreview, setImportPreview] = useState<ImportPreviewData | null>(null);
  const [importConfirming, setImportConfirming] = useState<boolean>(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);

  // Recurring Commitments State
  const [commitments, setCommitments] = useState<RecurringCommitmentItem[]>([]);
  const [reviewingCommitmentId, setReviewingCommitmentId] = useState<string | null>(null);
  const [detectingSubscriptions, setDetectingSubscriptions] = useState<boolean>(false);

  // Insights, Spending & Forecasting State
  const [insights, setInsights] = useState<FinancialInsight[]>([]);
  const [spending, setSpending] = useState<CategorySpendingResponse | null>(null);
  const [trends, setTrends] = useState<MonthlyTrendItem[]>([]);
  const [forecast, setForecast] = useState<FinancialForecastResponse | null>(null);
  const [forecastHorizon, setForecastHorizon] = useState<number>(6);
  const [savedScenarios, setSavedScenarios] = useState<SavedScenario[]>([]);

  // What-If Simulator Form State
  const [scenarioType, setScenarioType] = useState<string>("reduce_category_percentage");
  const [categoryName, setCategoryName] = useState<string>("Food & Dining");
  const [reductionPercentage, setReductionPercentage] = useState<number>(25);
  const [fixedAmount, setFixedAmount] = useState<string>("2000");
  const [simulationResult, setSimulationResult] = useState<SimulationRunResponse | null>(null);
  const [simulating, setSimulating] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);

  // AI Coach State
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [conversationList, setConversationList] = useState<CoachConversationSummary[]>([]);
  const [coachMessages, setCoachMessages] = useState<CoachMessage[]>([DEFAULT_WELCOME_MESSAGE]);
  const [coachInput, setCoachInput] = useState<string>("");
  const [coachLoading, setCoachLoading] = useState<boolean>(false);
  const [starterPrompts, setStarterPrompts] = useState<string[]>([
    "Where is most of my money going based on my statement?",
    "Which recurring subscriptions or bills were detected?",
    "Can I afford an unexpected ₹10,000 expense this month?",
    "How can I improve my savings rate from my current cash flow?",
  ]);

  // AI Coach Auto-Scroll Ref
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (activeTab === "coach") {
      scrollToBottom();
    }
  }, [coachMessages, coachLoading, activeTab, scrollToBottom]);

  // Overall Loading & Error States
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // =========================================================================
  // DATA LOADING (100% FROM STATEMENT)
  // =========================================================================

  const loadAllData = useCallback(async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [
        profileRes,
        txsRes,
        catsRes,
        commitmentsRes,
        insightsRes,
        spendingRes,
        trendsRes,
        forecastRes,
        scenariosRes,
        convsRes,
        promptsRes,
      ] = await Promise.allSettled([
        paisaApi.getProfile(),
        paisaApi.getTransactions(1, 20),
        paisaApi.getCategories(),
        paisaApi.getRecurringCommitments(),
        paisaApi.getInsights(),
        paisaApi.getSpendingCategories(),
        paisaApi.getSpendingTrends(6),
        paisaApi.getForecast(forecastHorizon),
        paisaApi.listScenarios(),
        paisaApi.listCoachConversations(),
        paisaApi.getCoachPrompts(),
      ]);

      if (profileRes.status === "fulfilled") setProfile(profileRes.value);
      if (txsRes.status === "fulfilled") {
        setTransactions(txsRes.value.items || []);
        setTransactionsTotal(txsRes.value.total || 0);
      }
      if (catsRes.status === "fulfilled") setCategories(catsRes.value.categories || []);
      if (commitmentsRes.status === "fulfilled") setCommitments(commitmentsRes.value || []);
      if (insightsRes.status === "fulfilled") setInsights(insightsRes.value || []);
      if (spendingRes.status === "fulfilled") setSpending(spendingRes.value);
      if (trendsRes.status === "fulfilled") setTrends(trendsRes.value || []);
      if (forecastRes.status === "fulfilled") setForecast(forecastRes.value);
      if (scenariosRes.status === "fulfilled") setSavedScenarios(scenariosRes.value || []);
      if (promptsRes.status === "fulfilled" && promptsRes.value.prompts && promptsRes.value.prompts.length > 0) {
        setStarterPrompts(promptsRes.value.prompts);
      }
      if (convsRes.status === "fulfilled" && convsRes.value.length > 0) {
        setConversationList(convsRes.value);
        const latestConv = convsRes.value[0];
        setActiveConversationId(latestConv.id);
        const detail = await paisaApi.getCoachConversation(latestConv.id);
        if (detail && detail.messages && detail.messages.length > 0) {
          setCoachMessages(detail.messages);
        }
      } else {
        setCoachMessages([DEFAULT_WELCOME_MESSAGE]);
        setActiveConversationId(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load statement data";
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  }, [forecastHorizon]);

  // Firebase Auth Observer (Dashboard opens ONLY when user is logged in)
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      setAuthLoading(false);
      if (firebaseUser) {
        setUser(firebaseUser);
        setActiveUserId(firebaseUser.uid, firebaseUser.email, firebaseUser.displayName);
        loadAllData();
      } else {
        setUser(null);
        setActiveUserId(null);
        router.replace("/login");
      }
    });
    return () => unsubscribe();
  }, [loadAllData, router]);

  const handleGoogleSignIn = async () => {
    try {
      const loggedUser = await loginWithGoogle();
      setUser(loggedUser);
      setActiveUserId(loggedUser.uid, loggedUser.email, loggedUser.displayName);
      loadAllData();
    } catch (err) {
      console.error("Google sign-in error:", err);
    }
  };

  const handleSignOut = async () => {
    try {
      await logoutFirebase();
      setUser(null);
      setActiveUserId(null);
      router.replace("/login");
    } catch (err) {
      console.error("Sign out error:", err);
    }
  };

  // Statement Ingestion Handlers
  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;

    setUploading(true);
    setImportMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", uploadFile);
      const res = await paisaApi.uploadStatement(formData);
      const preview = await paisaApi.getImportPreview(res.id);
      setImportPreview(preview);
      const candidatesCount =
        preview.total_candidates ??
        preview.valid_count ??
        preview.total_rows ??
        (preview.candidates?.length || preview.valid_rows?.length || 0);
      setImportMessage(`Statement parsed: ${candidatesCount} transactions extracted.`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      setImportMessage(`Error: ${msg}`);
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!importPreview) return;
    setImportConfirming(true);
    try {
      await paisaApi.confirmImport(importPreview.import_id);
      setImportMessage("Statement committed. Financial model updated with statement records.");
      setImportPreview(null);
      setUploadFile(null);
      await loadAllData();
      setActiveTab("overview");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Confirmation failed";
      setImportMessage(`Error confirming statement: ${msg}`);
    } finally {
      setImportConfirming(false);
    }
  };

  // Transaction Correction Handlers
  const handleSaveCorrection = async () => {
    if (!correctingTx || !newCategoryId) return;
    setCorrectionLoading(true);
    try {
      await paisaApi.updateTransaction(correctingTx.id, {
        category_id: newCategoryId,
        create_future_rule: createFutureRule,
      });
      if (createFutureRule) {
        await paisaApi.createTransactionRule(correctingTx.id, {
          category_id: newCategoryId,
          scope_type: futureScopeType,
        });
      }
      setCorrectingTx(null);
      setNewCategoryId("");
      await loadAllData();
    } catch (err) {
      console.error("Correction failed:", err);
    } finally {
      setCorrectionLoading(false);
    }
  };

  const handleExplainTx = async (tx: TransactionItem) => {
    setExplainingLoading(true);
    try {
      const res = await paisaApi.getTransactionExplanation(tx.id);
      setExplainingTx({ tx, explanation: res });
    } catch (err) {
      console.error("Explanation error:", err);
    } finally {
      setExplainingLoading(false);
    }
  };

  // Review Recurring Commitments
  const handleReviewCommitment = async (commitmentId: string, status: "confirm" | "reject") => {
    setReviewingCommitmentId(commitmentId);
    try {
      await paisaApi.reviewRecurringCommitment(commitmentId, status);
      await loadAllData();
    } catch (err) {
      console.error("Commitment review error:", err);
    } finally {
      setReviewingCommitmentId(null);
    }
  };

  const handleDetectSubscriptions = async () => {
    setDetectingSubscriptions(true);
    try {
      const detected = await paisaApi.detectSubscriptions();
      setCommitments(detected);
      await loadAllData();
    } catch (err) {
      console.error("Subscription detection error:", err);
    } finally {
      setDetectingSubscriptions(false);
    }
  };

  // What-If Simulation Handlers
  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    try {
      const params: Record<string, unknown> = {};
      if (scenarioType === "reduce_category_percentage") {
        params.category_name = categoryName;
        params.reduction_percentage = reductionPercentage;
      } else if (scenarioType === "reduce_category_fixed") {
        params.category_name = categoryName;
        params.reduction_fixed_amount = parseFloat(fixedAmount) || 0;
      }

      const res = await paisaApi.runSimulation({
        scenario_type: scenarioType,
        input_parameters: params,
      });
      setSimulationResult(res);
    } catch (err) {
      console.error("Simulation run error:", err);
    } finally {
      setSimulating(false);
    }
  };

  const handleSaveScenario = async () => {
    if (!simulationResult) return;
    setSaving(true);
    try {
      await paisaApi.saveScenario({
        title: simulationResult.title,
        scenario_type: simulationResult.scenario_type,
        input_parameters: {
          scenario_type: scenarioType,
          category_name: categoryName,
          reduction_pct: reductionPercentage,
          fixed_amount: fixedAmount,
        },
        baseline_result: simulationResult.baseline,
        scenario_result: simulationResult.scenario,
        assumptions: { items: simulationResult.assumptions },
      });
      const updated = await paisaApi.listScenarios();
      setSavedScenarios(updated);
    } catch (err) {
      console.error("Save scenario error:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteScenario = async (id: string) => {
    try {
      await paisaApi.deleteScenario(id);
      setSavedScenarios(savedScenarios.filter((s) => s.id !== id));
    } catch (err) {
      console.error("Delete scenario error:", err);
    }
  };

  // AI Financial Coach Chat Handlers (Live Gemini 3.5 Flash Lite)
  const handleSendCoachMessage = async (queryText?: string) => {
    const textToSend = queryText || coachInput;
    if (!textToSend.trim() || coachLoading) return;

    const userMsg: CoachMessage = {
      id: `user-${Date.now()}`,
      conversation_id: activeConversationId || "temp",
      sender: "user",
      content: textToSend,
      created_at: new Date().toISOString(),
    };

    setCoachMessages((prev) => [...prev, userMsg]);
    if (!queryText) setCoachInput("");
    setCoachLoading(true);

    try {
      const resp = await paisaApi.sendCoachMessage(
        textToSend,
        activeConversationId || undefined
      );

      const coachMsg: CoachMessage = {
        id: `coach-${Date.now()}`,
        conversation_id: resp.conversation_id,
        sender: "coach",
        content: resp.content,
        created_at: new Date().toISOString(),
        grounded_facts: resp.grounded_facts,
        assumptions: resp.assumptions,
        warnings: resp.warnings,
        is_live_gemini: resp.is_live_gemini,
      };

      setCoachMessages((prev) => [...prev, coachMsg]);
      setActiveConversationId(resp.conversation_id);

      const convs = await paisaApi.listCoachConversations();
      setConversationList(convs);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Coach service unavailable";
      setCoachMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          conversation_id: activeConversationId || "temp",
          sender: "coach",
          content: `I encountered an issue connecting to Gemini 3.5 Flash Lite: ${msg}. Please ensure your statement has been uploaded.`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setCoachLoading(false);
    }
  };

  const handleSelectConversation = async (convId: string) => {
    setActiveConversationId(convId);
    setCoachLoading(true);
    try {
      const detail = await paisaApi.getCoachConversation(convId);
      setCoachMessages(detail.messages || []);
    } catch (err) {
      console.error("Load conversation error:", err);
    } finally {
      setCoachLoading(false);
    }
  };

  const handleNewConversation = () => {
    setActiveConversationId(null);
    setCoachMessages([DEFAULT_WELCOME_MESSAGE]);
  };

  const handleDeleteConversation = async (convId: string) => {
    try {
      await paisaApi.deleteCoachConversation(convId);
      setConversationList((prev) => prev.filter((c) => c.id !== convId));
      if (activeConversationId === convId) {
        handleNewConversation();
      }
    } catch (err) {
      console.error("Delete conversation error:", err);
    }
  };

  // Has User Ingested Statement Data?
  const hasStatementData =
    transactionsTotal > 0 || parseFloat(profile?.current_period_summary?.income_total || "0") > 0;

  // Gate: Strictly render dashboard only when authenticated
  if (authLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-black text-white">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />
          <p className="font-mono text-xs uppercase tracking-widest text-neutral-400">Verifying session...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-black text-white selection:bg-white/20 selection:text-white overflow-x-hidden">
      {/* 1. TOP HEADER NAVIGATION (CINEMATIC DARK THEME) */}
      <header className="sticky top-0 z-40 border-b border-white/10 bg-black/85 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          {/* Logo & Product Title */}
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/15 bg-white/5 backdrop-blur-md">
                <Image
                  src="/PaisaFlow.png"
                  alt="PaisaFlow Logo"
                  width={32}
                  height={32}
                  className="h-7 w-7 object-contain brightness-0 invert"
                />
              </div>
              <span className="text-base font-bold tracking-[0.2em] text-white uppercase">
                PAISAFLOW
              </span>
            </Link>
            <span className="hidden text-xs font-mono uppercase tracking-wider text-neutral-400 sm:inline-block">
              / Living Money Model & AI Coach
            </span>
          </div>

          {/* Right Header: Google Firebase Authentication */}
          <div className="flex items-center gap-3">
            {authLoading ? (
              <div className="h-8 w-24 animate-pulse rounded-full bg-white/10" />
            ) : user ? (
              <div className="flex items-center gap-3 rounded-full border border-white/15 bg-white/5 p-1.5 pl-3">
                <div className="flex items-center gap-2">
                  {user.photoURL ? (
                    <Image
                      src={user.photoURL}
                      alt={user.displayName || "User"}
                      width={24}
                      height={24}
                      unoptimized
                      className="h-6 w-6 rounded-full border border-white/20"
                    />
                  ) : (
                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-white/20 text-xs font-bold text-white">
                      {(user.displayName || user.email || "U")[0].toUpperCase()}
                    </div>
                  )}
                  <span className="hidden text-xs font-medium text-neutral-200 sm:inline max-w-[140px] truncate">
                    {user.displayName || user.email}
                  </span>
                </div>
                <button
                  onClick={handleSignOut}
                  className="rounded-full bg-white/10 p-1.5 text-neutral-300 hover:bg-white/20 hover:text-white transition cursor-pointer"
                  title="Sign Out"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={handleGoogleSignIn}
                className="inline-flex items-center gap-2.5 rounded-full bg-white px-4 py-2 text-xs font-semibold text-black hover:bg-neutral-200 transition shadow-[0_0_20px_rgba(255,255,255,0.15)] cursor-pointer"
              >
                <GoogleLogo className="h-4 w-4" />
                <span>Sign in with Google</span>
              </button>
            )}
          </div>
        </div>

        {/* Navigation Tabs (Flex-Wrap, Zero Horizontal Scroll) */}
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-2 px-6 pb-3 pt-1">
          {[
            { id: "overview", label: "Overview", icon: LayoutDashboard },
            { id: "imports", label: "Statement Import", icon: UploadCloud },
            { id: "transactions", label: "Transactions", icon: CreditCard },
            { id: "recurring", label: "Subscriptions & Bills", icon: RefreshCw },
            { id: "insights", label: "Insights & Spending", icon: TrendingUp },
            { id: "forecast", label: "Forecast", icon: Compass },
            { id: "simulator", label: "What-If Simulator", icon: Sliders },
            { id: "coach", label: "Gemini 3.5 Coach", icon: Bot },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-medium transition cursor-pointer ${
                  isActive
                    ? "bg-white text-black font-semibold shadow-[0_0_20px_rgba(255,255,255,0.15)]"
                    : "border border-white/10 bg-white/[0.04] text-neutral-400 hover:border-white/25 hover:bg-white/[0.08] hover:text-white"
                }`}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </header>

      {/* 2. MAIN DASHBOARD CONTENT */}
      <main className="mx-auto max-w-7xl px-6 py-8">
        {loading ? (
          <div className="flex h-72 flex-col items-center justify-center gap-4">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-white border-t-transparent" />
            <p className="font-mono text-xs text-neutral-400 tracking-wider">
              Computing deterministic financial model from statement records...
            </p>
          </div>
        ) : errorMessage ? (
          <div className="rounded-2xl border border-red-500/30 bg-red-950/20 p-6 text-red-300">
            <h3 className="font-semibold text-base">Backend Connection Issue</h3>
            <p className="mt-1 text-sm text-red-400">{errorMessage}</p>
            <p className="mt-3 text-xs text-neutral-400">
              Ensure the FastAPI backend is running on http://127.0.0.1:8000
            </p>
            <button
              onClick={loadAllData}
              className="mt-4 rounded-full bg-white px-4 py-1.5 text-xs font-semibold text-black hover:bg-neutral-200 transition"
            >
              Retry
            </button>
          </div>
        ) : (
          <div>
            {/* Zero Fake Data Notice Banner if No Statement Ingested */}
            {!hasStatementData && activeTab !== "imports" && (
              <div className="mb-8 rounded-3xl border border-white/20 bg-gradient-to-r from-white/[0.08] via-[#0A0A0A] to-black p-8 backdrop-blur-xl">
                <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
                  <div className="max-w-2xl">
                    <span className="font-mono text-xs font-bold uppercase tracking-widest text-neutral-400">
                      Zero Fake Information Guarantee
                    </span>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                      Upload your bank statement to initialize your model.
                    </h2>
                    <p className="mt-3 text-sm leading-relaxed text-neutral-300">
                      PaisaFlow does not fabricate accounts or balances. Every income figure,
                      subscription, category percentage, and AI coach answer is derived 100%
                      from your actual uploaded statement records.
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 shrink-0">
                    <button
                      onClick={() => setActiveTab("imports")}
                      className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-xs font-bold uppercase tracking-wider text-black hover:bg-neutral-200 transition shadow-[0_0_25px_rgba(255,255,255,0.2)] cursor-pointer"
                    >
                      <UploadCloud className="h-4 w-4" />
                      <span>Upload Statement</span>
                    </button>
                    <a
                      href="/sample_statement.csv"
                      download="sample_statement.csv"
                      className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-5 py-3 text-xs font-medium text-white hover:bg-white/10 transition"
                    >
                      <Download className="h-4 w-4" />
                      <span>Sample Statement (.csv)</span>
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 1: OVERVIEW */}
            {/* ========================================================================= */}
            {activeTab === "overview" && (
              <div className="space-y-8">
                {/* KPI Metrics Grid with Ambient Highlights */}
                <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
                  {/* Total Inflow */}
                  <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-[#131313] to-[#080808] p-6 shadow-xl hover:border-emerald-500/30 transition-all duration-300">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium tracking-wide text-neutral-400">Total Inflow</span>
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
                        <TrendingUp className="h-4 w-4" />
                      </div>
                    </div>
                    <p className="mt-3 text-3xl font-bold tracking-tight text-white">
                      {formatCurrency(profile?.current_period_summary?.income_total || 0)}
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-xs">
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                        <CheckCircle2 className="h-3 w-3" /> Inflow
                      </span>
                      <span className="text-[11px] text-neutral-500 truncate">
                        {transactionsTotal > 0 ? "Verified from statement credits" : "Awaiting statement upload"}
                      </span>
                    </div>
                  </div>

                  {/* Total Outflow */}
                  <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-[#131313] to-[#080808] p-6 shadow-xl hover:border-rose-500/30 transition-all duration-300">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium tracking-wide text-neutral-400">Total Outflow</span>
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-rose-500/20 bg-rose-500/10 text-rose-400">
                        <TrendingDown className="h-4 w-4" />
                      </div>
                    </div>
                    <p className="mt-3 text-3xl font-bold tracking-tight text-white">
                      {formatCurrency(profile?.current_period_summary?.expense_net || 0)}
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-xs">
                      <span className="inline-flex items-center gap-1 rounded-full bg-rose-500/10 px-2 py-0.5 text-[10px] font-semibold text-rose-400 border border-rose-500/20">
                        <CreditCard className="h-3 w-3" /> Outflow
                      </span>
                      <span className="text-[11px] text-neutral-500 truncate">
                        {transactionsTotal > 0 ? "Statement debits & adjustments" : "Awaiting statement upload"}
                      </span>
                    </div>
                  </div>

                  {/* Net Surplus */}
                  <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-[#131313] to-[#080808] p-6 shadow-xl hover:border-indigo-500/30 transition-all duration-300">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium tracking-wide text-neutral-400">Net Surplus</span>
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-500/20 bg-indigo-500/10 text-indigo-400">
                        <CreditCard className="h-4 w-4" />
                      </div>
                    </div>
                    <p className="mt-3 text-3xl font-bold tracking-tight text-white">
                      {formatCurrency(profile?.current_period_summary?.net_cash_flow || 0)}
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-xs">
                      <span className="inline-flex items-center gap-1 rounded-full bg-indigo-500/10 px-2 py-0.5 text-[10px] font-semibold text-indigo-400 border border-indigo-500/20">
                        <Check className="h-3 w-3" /> Deterministic
                      </span>
                      <span className="text-[11px] text-neutral-500 truncate">
                        {transactionsTotal > 0 ? "Net monthly cash delta" : "Zero until statements committed"}
                      </span>
                    </div>
                  </div>

                  {/* Cash Flow Savings Rate */}
                  <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-b from-[#131313] to-[#080808] p-6 shadow-xl hover:border-cyan-500/30 transition-all duration-300">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium tracking-wide text-neutral-400">Savings Rate</span>
                      <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-500/20 bg-cyan-500/10 text-cyan-400">
                        <Sparkles className="h-4 w-4" />
                      </div>
                    </div>
                    <p className="mt-3 text-3xl font-bold tracking-tight text-white">
                      {profile?.current_period_summary?.savings_rate
                        ? `${profile.current_period_summary.savings_rate}%`
                        : "0.0%"}
                    </p>
                    <div className="mt-4 flex items-center gap-2 text-xs">
                      <span className="inline-flex items-center gap-1 rounded-full bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-400 border border-cyan-500/20">
                        <Layers className="h-3 w-3" /> Ratio
                      </span>
                      <span className="text-[11px] text-neutral-500 truncate">
                        {transactionsTotal > 0 ? "Surplus / Inflow ratio" : "Calculated from statement"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Living Facts from Statement */}
                <div className="rounded-3xl border border-white/15 bg-gradient-to-b from-[#0F0F0F] to-[#070707] p-7 shadow-xl">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-white/10 pb-5">
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold text-white">Active Statement Facts</h3>
                        <span className="rounded-full border border-white/20 bg-white/5 px-2.5 py-0.5 text-[10px] font-medium text-neutral-300">
                          Living Money Model
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-neutral-400">
                        Extracted directly from your statement records with cryptographic provenance.
                      </p>
                    </div>
                    <span className="font-mono text-xs text-neutral-400">
                      {profile?.active_facts?.length || 0} active verified facts
                    </span>
                  </div>

                  {profile?.active_facts && profile.active_facts.length > 0 ? (
                    <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      {profile.active_facts.map((fact) => (
                        <div
                          key={fact.id}
                          className="relative overflow-hidden rounded-2xl border border-white/10 bg-[#141414]/80 p-5 hover:border-white/25 transition-all duration-200 group"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-xs uppercase tracking-wider text-neutral-400">
                              {fact.label || fact.fact_type.replace(/_/g, " ")}
                            </span>
                            <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-[10px] font-medium text-neutral-300">
                              {fact.source_type}
                            </span>
                          </div>
                          <p className="mt-3 text-2xl font-bold tracking-tight text-white">
                            {formatCurrency(fact.amount)}
                          </p>
                          <div className="mt-2.5 flex items-center gap-1.5 text-xs text-neutral-400">
                            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                            <span className="truncate">
                              {fact.confidence ? `Confidence: ${fact.confidence}` : "Inferred from uploaded statement."}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-8 flex flex-col items-center justify-center p-8 text-center border border-dashed border-white/15 rounded-2xl bg-white/[0.01]">
                      <FileText className="h-8 w-8 text-neutral-500 mb-3" />
                      <p className="text-sm font-medium text-neutral-300">No statement facts yet</p>
                      <p className="mt-1 text-xs text-neutral-500 max-w-md">
                        Upload your bank statement (CSV or PDF) to populate verified financial facts.
                      </p>
                      <button
                        onClick={() => setActiveTab("imports")}
                        className="mt-4 rounded-full bg-white px-5 py-2 text-xs font-semibold text-black hover:bg-neutral-200 transition cursor-pointer"
                      >
                        Upload Statement Now
                      </button>
                    </div>
                  )}
                </div>

                {/* Quick Action Navigation Cards */}
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div
                    onClick={() => setActiveTab("imports")}
                    className="group cursor-pointer rounded-2xl border border-white/10 bg-gradient-to-b from-[#111111] to-[#080808] p-6 transition-all duration-300 hover:border-white/30 hover:shadow-[0_0_25px_rgba(255,255,255,0.05)] flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white">
                          <UploadCloud className="h-5 w-5" />
                        </div>
                        <ArrowRight className="h-4 w-4 text-neutral-600 group-hover:text-white group-hover:translate-x-1 transition duration-200" />
                      </div>
                      <h4 className="mt-4 font-semibold text-base text-white group-hover:text-neutral-200">
                        Import Financial Statement
                      </h4>
                      <p className="mt-1.5 text-xs text-neutral-400 leading-relaxed">
                        Upload CSV or PDF statements to extract real transactions and update your model.
                      </p>
                    </div>
                  </div>

                  <div
                    onClick={() => setActiveTab("simulator")}
                    className="group cursor-pointer rounded-2xl border border-white/10 bg-gradient-to-b from-[#111111] to-[#080808] p-6 transition-all duration-300 hover:border-white/30 hover:shadow-[0_0_25px_rgba(255,255,255,0.05)] flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white">
                          <Sliders className="h-5 w-5" />
                        </div>
                        <ArrowRight className="h-4 w-4 text-neutral-600 group-hover:text-white group-hover:translate-x-1 transition duration-200" />
                      </div>
                      <h4 className="mt-4 font-semibold text-base text-white group-hover:text-neutral-200">
                        Run What-If Simulation
                      </h4>
                      <p className="mt-1.5 text-xs text-neutral-400 leading-relaxed">
                        Hypothesize expense cuts or new EMIs without altering your real records.
                      </p>
                    </div>
                  </div>

                  <div
                    onClick={() => setActiveTab("coach")}
                    className="group cursor-pointer rounded-2xl border border-white/10 bg-gradient-to-b from-[#111111] to-[#080808] p-6 transition-all duration-300 hover:border-white/30 hover:shadow-[0_0_25px_rgba(255,255,255,0.05)] flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white">
                          <Bot className="h-5 w-5" />
                        </div>
                        <ArrowRight className="h-4 w-4 text-neutral-600 group-hover:text-white group-hover:translate-x-1 transition duration-200" />
                      </div>
                      <h4 className="mt-4 font-semibold text-base text-white group-hover:text-neutral-200">
                        Ask Gemini 3.5 Flash Lite
                      </h4>
                      <p className="mt-1.5 text-xs text-neutral-400 leading-relaxed">
                        Conversational coaching grounded in your exact Decimal statement numbers.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 2: STATEMENT IMPORT WORKFLOW */}
            {/* ========================================================================= */}
            {activeTab === "imports" && (
              <div className="space-y-6">
                <div>
                  <h2 className="text-2xl font-semibold tracking-tight text-white">
                    Statement Ingestion & Normalization
                  </h2>
                  <p className="mt-1 text-sm text-neutral-400">
                    Upload CSV or text-based PDF statements. Transactions are normalized, duplicates
                    flagged, and previewed before committing.
                  </p>
                </div>

                {/* Upload Card */}
                <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-8">
                  <h3 className="font-semibold text-base text-white">Upload Statement File</h3>
                  <form onSubmit={handleFileUpload} className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-center">
                    <input
                      type="file"
                      accept=".csv,.pdf"
                      onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                      className="text-xs text-neutral-400 file:mr-4 file:rounded-full file:border file:border-white/20 file:bg-white/10 file:px-4 file:py-2 file:text-xs file:font-semibold file:text-white hover:file:bg-white/20 cursor-pointer"
                    />
                    <button
                      type="submit"
                      disabled={!uploadFile || uploading}
                      className="rounded-full bg-white px-6 py-2.5 text-xs font-semibold text-black hover:bg-neutral-200 disabled:opacity-50 transition cursor-pointer"
                    >
                      {uploading ? "Parsing Statement..." : "Parse & Preview"}
                    </button>
                    <a
                      href="/sample_statement.csv"
                      download="sample_statement.csv"
                      className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white transition"
                    >
                      <Download className="h-3.5 w-3.5" />
                      <span>Download Sample Statement</span>
                    </a>
                  </form>

                  {importMessage && (
                    <div className="mt-4 rounded-xl border border-white/15 bg-white/[0.04] p-3 text-xs text-neutral-200">
                      {importMessage}
                    </div>
                  )}
                </div>

                {/* Pre-Commit Preview Table */}
                {importPreview && (() => {
                  const candidatesList = importPreview.candidates || importPreview.valid_rows || [];
                  const totalCount =
                    importPreview.total_candidates ??
                    importPreview.valid_count ??
                    importPreview.total_rows ??
                    candidatesList.length;
                  const duplicateCount = importPreview.duplicate_count ?? 0;

                  return (
                    <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-7 space-y-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-white/10 pb-4">
                        <div>
                          <h3 className="font-semibold text-lg text-white">Import Preview</h3>
                          <p className="text-xs text-neutral-400">
                            {totalCount} candidate{totalCount === 1 ? "" : "s"} extracted, {duplicateCount} duplicate{duplicateCount === 1 ? "" : "s"} detected.
                          </p>
                        </div>
                        <button
                          onClick={handleConfirmImport}
                          disabled={importConfirming || candidatesList.length === 0}
                          className="rounded-full bg-white px-6 py-2 text-xs font-semibold text-black hover:bg-neutral-200 disabled:opacity-50 transition shadow-[0_0_20px_rgba(255,255,255,0.2)] cursor-pointer"
                        >
                          {importConfirming ? "Committing..." : "Confirm & Commit to Model"}
                        </button>
                      </div>

                      <div className="w-full overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead className="border-b border-white/10 text-neutral-400 uppercase tracking-wider font-mono">
                            <tr>
                              <th className="py-2.5 px-3">Date</th>
                              <th className="py-2.5 px-3">Description</th>
                              <th className="py-2.5 px-3">Merchant</th>
                              <th className="py-2.5 px-3">Direction</th>
                              <th className="py-2.5 px-3 text-right">Amount</th>
                              <th className="py-2.5 px-3">Status</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-white/5">
                            {candidatesList.length === 0 ? (
                              <tr>
                                <td colSpan={6} className="py-8 text-center text-neutral-500">
                                  No transaction candidates found in statement.
                                </td>
                              </tr>
                            ) : (
                              candidatesList.map((row: ImportCandidate, idx: number) => {
                                const isDuplicate =
                                  row.is_duplicate ||
                                  (row.duplicate_status && row.duplicate_status !== "unique");
                                const merchantDisplay =
                                  row.resolved_merchant || row.merchant_name || "—";

                                return (
                                  <tr key={row.row_id || idx} className="hover:bg-white/[0.02]">
                                    <td className="py-2.5 px-3 font-mono text-neutral-300">
                                      {row.transaction_date}
                                    </td>
                                    <td className="py-2.5 px-3 text-white max-w-[220px] truncate">
                                      {row.original_description}
                                    </td>
                                    <td className="py-2.5 px-3 text-neutral-300">
                                      {merchantDisplay}
                                    </td>
                                    <td className="py-2.5 px-3">
                                      <span
                                        className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                          row.direction === "credit"
                                            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                            : "bg-neutral-800 text-neutral-300"
                                        }`}
                                      >
                                        {row.direction}
                                      </span>
                                    </td>
                                    <td className="py-2.5 px-3 text-right font-semibold text-white">
                                      {formatCurrency(row.amount)}
                                    </td>
                                    <td className="py-2.5 px-3">
                                      <span
                                        className={`rounded-full border px-2 py-0.5 text-[10px] ${
                                          isDuplicate
                                            ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                                            : "border-white/15 bg-white/5 text-neutral-300"
                                        }`}
                                      >
                                        {isDuplicate ? "Duplicate" : "New"}
                                      </span>
                                    </td>
                                  </tr>
                                );
                              })
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 3: TRANSACTIONS LEDGER */}
            {/* ========================================================================= */}
            {activeTab === "transactions" && (
              <div className="space-y-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-white">Transactions Ledger</h2>
                    <p className="mt-1 text-sm text-neutral-400">
                      All normalized transactions derived from your statement uploads.
                    </p>
                  </div>
                  <span className="font-mono text-xs text-neutral-400">
                    {transactionsTotal} records total
                  </span>
                </div>

                {/* Filter and Search Bar */}
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
                  <div className="relative flex-1">
                    <Search className="absolute left-3.5 top-3 h-4 w-4 text-neutral-500" />
                    <input
                      type="text"
                      placeholder="Search transactions by merchant or description..."
                      value={transactionsSearch}
                      onChange={(e) => setTransactionsSearch(e.target.value)}
                      className="w-full rounded-xl border border-white/15 bg-[#0A0A0A] py-2.5 pl-10 pr-4 text-xs text-white placeholder-neutral-500 focus:border-white focus:outline-none"
                    />
                  </div>

                  <select
                    value={selectedFilterCategory}
                    onChange={(e) => setSelectedFilterCategory(e.target.value)}
                    className="rounded-xl border border-white/15 bg-[#0A0A0A] px-4 py-2.5 text-xs text-white focus:border-white focus:outline-none cursor-pointer"
                  >
                    <option value="">All Categories</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Transactions Table */}
                <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] overflow-hidden">
                  <div className="w-full overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="border-b border-white/10 bg-white/[0.02] text-neutral-400 uppercase tracking-wider font-mono">
                        <tr>
                          <th className="py-3 px-4">Date</th>
                          <th className="py-3 px-4">Description</th>
                          <th className="py-3 px-4">Category</th>
                          <th className="py-3 px-4">Direction</th>
                          <th className="py-3 px-4 text-right">Amount</th>
                          <th className="py-3 px-4 text-center">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {transactions.length > 0 ? (
                          transactions.map((tx) => (
                            <tr key={tx.id} className="hover:bg-white/[0.02] transition">
                              <td className="py-3 px-4 font-mono text-neutral-300">{tx.transaction_date}</td>
                              <td className="py-3 px-4 text-white font-medium max-w-[260px] truncate">
                                {tx.normalized_description || tx.original_description}
                              </td>
                              <td className="py-3 px-4">
                                <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-[11px] text-neutral-300">
                                  {tx.category_name || "Uncategorized"}
                                </span>
                              </td>
                              <td className="py-3 px-4">
                                <span
                                  className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                                    tx.direction === "credit"
                                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                      : "bg-neutral-800 text-neutral-300"
                                  }`}
                                >
                                  {tx.direction}
                                </span>
                              </td>
                              <td className="py-3 px-4 text-right font-semibold text-white">
                                {formatCurrency(tx.amount)}
                              </td>
                              <td className="py-3 px-4 text-center">
                                <div className="flex items-center justify-center gap-2">
                                  <button
                                    onClick={() => {
                                      setCorrectingTx(tx);
                                      setNewCategoryId(tx.category_id || "");
                                    }}
                                    className="rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-[10px] text-neutral-300 hover:bg-white/15 hover:text-white transition cursor-pointer"
                                  >
                                    Correct
                                  </button>
                                  <button
                                    onClick={() => handleExplainTx(tx)}
                                    className="rounded-lg border border-white/15 bg-white/5 px-2 py-1 text-[10px] text-neutral-400 hover:text-white transition cursor-pointer"
                                  >
                                    Why?
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))
                        ) : (
                          <tr>
                            <td colSpan={6} className="py-12 text-center text-neutral-500">
                              No statement transactions found. Upload a statement to populate this ledger.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Correction Modal */}
                {correctingTx && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
                    <div className="w-full max-w-md rounded-3xl border border-white/20 bg-[#0A0A0A] p-6 text-white shadow-2xl">
                      <div className="flex items-center justify-between border-b border-white/10 pb-4">
                        <h3 className="font-semibold text-base">Correct Category</h3>
                        <button
                          onClick={() => setCorrectingTx(null)}
                          className="text-neutral-400 hover:text-white cursor-pointer"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>

                      <div className="mt-4 space-y-4">
                        <div>
                          <p className="text-xs text-neutral-400">Transaction</p>
                          <p className="mt-1 font-semibold text-sm">
                            {correctingTx.normalized_description || correctingTx.original_description}
                          </p>
                          <p className="text-xs text-neutral-400 mt-1">
                            {formatCurrency(correctingTx.amount)} on {correctingTx.transaction_date}
                          </p>
                        </div>

                        <div>
                          <label className="text-xs font-medium text-neutral-300">Select Category</label>
                          <select
                            value={newCategoryId}
                            onChange={(e) => setNewCategoryId(e.target.value)}
                            className="mt-1.5 w-full rounded-xl border border-white/20 bg-[#121212] px-3.5 py-2.5 text-xs text-white focus:border-white focus:outline-none"
                          >
                            <option value="">-- Choose Category --</option>
                            {categories.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.name}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="flex items-center gap-2.5 pt-2">
                          <input
                            type="checkbox"
                            id="futureRule"
                            checked={createFutureRule}
                            onChange={(e) => setCreateFutureRule(e.target.checked)}
                            className="rounded border-white/20 accent-white"
                          />
                          <label htmlFor="futureRule" className="text-xs text-neutral-300 cursor-pointer">
                            Apply personalized rule for future imports
                          </label>
                        </div>
                      </div>

                      <div className="mt-6 flex justify-end gap-2.5 border-t border-white/10 pt-4">
                        <button
                          onClick={() => setCorrectingTx(null)}
                          className="rounded-full border border-white/20 bg-white/5 px-4 py-1.5 text-xs font-medium text-neutral-300 hover:bg-white/10"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={handleSaveCorrection}
                          disabled={correctionLoading || !newCategoryId}
                          className="rounded-full bg-white px-5 py-1.5 text-xs font-semibold text-black hover:bg-neutral-200 disabled:opacity-50"
                        >
                          {correctionLoading ? "Saving..." : "Save Correction"}
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Explanation Modal */}
                {explainingTx && (
                  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4">
                    <div className="w-full max-w-lg rounded-3xl border border-white/20 bg-[#0A0A0A] p-6 text-white shadow-2xl">
                      <div className="flex items-center justify-between border-b border-white/10 pb-4">
                        <h3 className="font-semibold text-base">Provenance & Classification Proof</h3>
                        <button
                          onClick={() => setExplainingTx(null)}
                          className="text-neutral-400 hover:text-white cursor-pointer"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>

                      <div className="mt-4 space-y-4 text-xs leading-relaxed">
                        <div>
                          <p className="text-neutral-400">Transaction</p>
                          <p className="font-semibold text-sm text-white mt-0.5">
                            {explainingTx.tx.normalized_description || explainingTx.tx.original_description}
                          </p>
                        </div>

                        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Method:</span>
                            <span className="font-mono text-white">
                              {explainingTx.tx.transaction_type || "rule_pattern"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Confidence:</span>
                            <span className="font-bold text-white">
                              {explainingTx.tx.confidence
                                ? `${(parseFloat(String(explainingTx.tx.confidence)) * 100).toFixed(0)}%`
                                : "90%"}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-neutral-400">Category:</span>
                            <span className="font-semibold text-white">
                              {explainingTx.tx.category_name || "Uncategorized"}
                            </span>
                          </div>
                        </div>

                        <p className="text-neutral-400 text-[11px]">
                          Classification was executed deterministically by the intelligence engine based on
                          normalized merchant token matching and user categorization rule priority.
                        </p>
                      </div>

                      <div className="mt-6 flex justify-end border-t border-white/10 pt-4">
                        <button
                          onClick={() => setExplainingTx(null)}
                          className="rounded-full bg-white px-5 py-1.5 text-xs font-semibold text-black hover:bg-neutral-200"
                        >
                          Close
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 4: RECURRING COMMITMENTS */}
            {/* ========================================================================= */}
            {activeTab === "recurring" && (
              <div className="space-y-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-white">
                      Subscriptions & Recurring Obligations
                    </h2>
                    <p className="mt-1 text-sm text-neutral-400">
                      Gemini AI subscription intelligence with automatic next billing date tracking.
                    </p>
                  </div>
                  <button
                    onClick={handleDetectSubscriptions}
                    disabled={detectingSubscriptions}
                    className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-medium text-white hover:bg-white/10 transition disabled:opacity-50 cursor-pointer shadow-sm"
                  >
                    <Sparkles className={`h-3.5 w-3.5 ${detectingSubscriptions ? "animate-spin text-amber-300" : "text-amber-400"}`} />
                    {detectingSubscriptions ? "Gemini Scanning..." : "AI Scan Subscriptions"}
                  </button>
                </div>

                {commitments.length > 0 ? (
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
                    {commitments.map((c) => (
                      <div
                        key={c.id}
                        className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-6 shadow-sm flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between">
                            <span className="rounded-full border border-white/15 bg-white/5 px-2.5 py-0.5 text-[10px] font-mono uppercase text-neutral-300">
                              {c.cadence}
                            </span>
                            <span
                              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                                c.status === "confirmed"
                                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                  : "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              }`}
                            >
                              {c.status}
                            </span>
                          </div>

                          <h3 className="mt-4 text-lg font-semibold text-white">{c.display_name}</h3>
                          <p className="mt-2 text-2xl font-bold text-white">{formatCurrency(c.typical_amount)}</p>
                          <p className="mt-1 text-xs text-neutral-400">
                            Monthly equivalent: {formatCurrency(c.monthly_planning_equivalent)}
                          </p>

                          {/* Next Predicted Debited Date */}
                          <div className="mt-4 rounded-2xl border border-white/10 bg-white/[0.02] p-3 space-y-1.5">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-neutral-400">Next Expected Date:</span>
                              <span className="font-mono font-semibold text-emerald-400">
                                {c.next_expected_date ? String(c.next_expected_date) : "Predicting..."}
                              </span>
                            </div>
                            {c.last_observed_date && (
                              <div className="flex items-center justify-between text-[11px]">
                                <span className="text-neutral-500">Last Debited:</span>
                                <span className="font-mono text-neutral-400">{String(c.last_observed_date)}</span>
                              </div>
                            )}
                          </div>

                          {c.evidence && typeof c.evidence === "object" && "price_shift" in c.evidence && (
                            <div className="mt-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-300">
                              Amount shift detected: {String((c.evidence as Record<string, unknown>).price_shift)}
                            </div>
                          )}
                        </div>

                        <div className="mt-6 flex items-center gap-2 border-t border-white/10 pt-4">
                          <button
                            onClick={() => handleReviewCommitment(c.id, "confirm")}
                            disabled={reviewingCommitmentId === c.id}
                            className="flex-1 rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-black hover:bg-neutral-200 transition"
                          >
                            Confirm
                          </button>
                          <button
                            onClick={() => handleReviewCommitment(c.id, "reject")}
                            disabled={reviewingCommitmentId === c.id}
                            className="flex-1 rounded-full border border-white/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-neutral-300 hover:bg-white/10 transition"
                          >
                            Reject
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center p-12 text-center border border-dashed border-white/15 rounded-3xl">
                    <Sparkles className="h-8 w-8 text-amber-400/80 mb-3" />
                    <p className="text-base font-medium text-white">No recurring obligations detected yet</p>
                    <p className="mt-1.5 text-xs text-neutral-400 max-w-md">
                      Upload your statement or click below to have Gemini AI analyze your transaction descriptions, extract subscriptions, and automatically predict their next billing dates.
                    </p>
                    <button
                      onClick={handleDetectSubscriptions}
                      disabled={detectingSubscriptions}
                      className="mt-5 inline-flex items-center gap-2 rounded-full bg-white px-5 py-2 text-xs font-semibold text-black hover:bg-neutral-200 transition disabled:opacity-50 cursor-pointer"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      {detectingSubscriptions ? "Scanning with Gemini..." : "Scan Statement for Subscriptions"}
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 5: INSIGHTS & SPENDING */}
            {/* ========================================================================= */}
            {activeTab === "insights" && (
              <div className="space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold tracking-tight text-white">
                    Insights & Spending Breakdown
                  </h2>
                  <p className="mt-1 text-sm text-neutral-400">
                    Category concentration and trend intelligence derived from your statements.
                  </p>
                </div>

                {spending ? (
                  <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                    {/* Needs vs Wants */}
                    <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-7">
                      <h3 className="font-semibold text-base text-white">Needs vs. Wants Distribution</h3>
                      <div className="mt-6 flex h-3 w-full overflow-hidden rounded-full bg-white/10">
                        <div
                          style={{ width: `${Number(spending.essential_percentage || 50)}%` }}
                          className="bg-white"
                          title="Essential Needs"
                        />
                        <div
                          style={{ width: `${Number(spending.discretionary_percentage || 50)}%` }}
                          className="bg-neutral-600"
                          title="Discretionary Wants"
                        />
                      </div>
                      <div className="mt-4 flex justify-between text-xs text-neutral-400">
                        <span className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-white" />
                          Essential: {formatCurrency(spending.essential_spend)} ({Number(spending.essential_percentage || 0).toFixed(0)}%)
                        </span>
                        <span className="flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full bg-neutral-600" />
                          Discretionary: {formatCurrency(spending.discretionary_spend)} ({Number(spending.discretionary_percentage || 0).toFixed(0)}%)
                        </span>
                      </div>
                    </div>

                    {/* Top Categories */}
                    <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-7">
                      <h3 className="font-semibold text-base text-white">Top Spending Categories</h3>
                      <div className="mt-4 space-y-3">
                        {spending.categories?.slice(0, 5).map((cat, idx) => (
                          <div key={idx} className="flex items-center justify-between text-xs py-1">
                            <span className="text-neutral-300">{cat.category_name}</span>
                            <span className="font-semibold text-white">{formatCurrency(cat.current_spend)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-neutral-500 border border-dashed border-white/15 rounded-3xl">
                    Upload your statement to analyze category concentrations.
                  </div>
                )}

                {/* Algorithmic Insights Feed */}
                <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-7">
                  <h3 className="font-semibold text-base text-white mb-4">Algorithmic Financial Observations</h3>
                  <div className="space-y-3">
                    {insights.length > 0 ? (
                      insights.map((ins, idx) => (
                        <div key={idx} className="rounded-2xl border border-white/10 bg-white/[0.02] p-4 text-xs">
                          <p className="font-semibold text-white">{ins.title}</p>
                          <p className="mt-1 text-neutral-400 leading-relaxed">{ins.explanation}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-xs text-neutral-500">
                        Insights are generated automatically once statement transactions are committed.
                      </p>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 6: FORECAST */}
            {/* ========================================================================= */}
            {activeTab === "forecast" && (
              <div className="space-y-6">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h2 className="text-2xl font-semibold tracking-tight text-white">Multi-Month Cash Flow Forecast</h2>
                    <p className="mt-1 text-sm text-neutral-400">
                      Deterministic forward run-rate projections based on statement commitments.
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 p-1 text-xs">
                    {[1, 3, 6].map((h) => (
                      <button
                        key={h}
                        onClick={() => setForecastHorizon(h)}
                        className={`rounded-full px-3 py-1 font-medium transition cursor-pointer ${
                          forecastHorizon === h ? "bg-white text-black" : "text-neutral-400 hover:text-white"
                        }`}
                      >
                        {h}M
                      </button>
                    ))}
                  </div>
                </div>

                {forecast?.months && forecast.months.length > 0 ? (
                  <div className="grid grid-cols-1 gap-5 sm:grid-cols-3">
                    {forecast.months.map((p, idx) => (
                      <div key={idx} className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-6 space-y-3">
                        <span className="font-mono text-xs uppercase tracking-wider text-neutral-400">
                          {p.target_month_label || p.target_month}
                        </span>
                        <p className="text-2xl font-bold text-white">{formatCurrency(p.expected_total_expenses)}</p>
                        <div className="text-xs text-neutral-400 space-y-1 pt-2 border-t border-white/10">
                          <div className="flex justify-between">
                            <span>Income:</span>
                            <span className="text-white font-medium">{formatCurrency(p.expected_income)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span>Recurring:</span>
                            <span className="text-white font-medium">{formatCurrency(p.expected_recurring_expenses)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-neutral-500 border border-dashed border-white/15 rounded-3xl">
                    Forecast projections require uploaded statement transactions.
                  </div>
                )}
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 7: WHAT-IF SIMULATOR */}
            {/* ========================================================================= */}
            {activeTab === "simulator" && (
              <div className="space-y-8">
                <div>
                  <h2 className="text-2xl font-semibold tracking-tight text-white">What-If Simulation Engine</h2>
                  <p className="mt-1 text-sm text-neutral-400">
                    Test financial decisions across 3, 6, and 12-month horizons without altering transaction records.
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
                  {/* Scenario Form */}
                  <form onSubmit={handleRunSimulation} className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-7 space-y-5">
                    <h3 className="font-semibold text-base text-white">Configure Hypothetical Scenario</h3>

                    <div>
                      <label className="text-xs text-neutral-400 font-medium">Scenario Template</label>
                      <select
                        value={scenarioType}
                        onChange={(e) => setScenarioType(e.target.value)}
                        className="mt-1.5 w-full rounded-xl border border-white/20 bg-[#121212] px-3.5 py-2.5 text-xs text-white focus:border-white focus:outline-none"
                      >
                        <option value="reduce_category_percentage">Reduce Category by Percentage</option>
                        <option value="reduce_category_fixed">Reduce Category by Fixed Amount</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs text-neutral-400 font-medium">Target Category</label>
                      <input
                        type="text"
                        value={categoryName}
                        onChange={(e) => setCategoryName(e.target.value)}
                        className="mt-1.5 w-full rounded-xl border border-white/20 bg-[#121212] px-3.5 py-2.5 text-xs text-white focus:border-white focus:outline-none"
                      />
                    </div>

                    {scenarioType === "reduce_category_percentage" ? (
                      <div>
                        <div className="flex justify-between text-xs text-neutral-400">
                          <span>Reduction Percentage</span>
                          <span className="font-bold text-white">{reductionPercentage}%</span>
                        </div>
                        <input
                          type="range"
                          min="5"
                          max="80"
                          step="5"
                          value={reductionPercentage}
                          onChange={(e) => setReductionPercentage(Number(e.target.value))}
                          className="mt-3 w-full accent-white"
                        />
                      </div>
                    ) : (
                      <div>
                        <label className="text-xs text-neutral-400 font-medium">Monthly Reduction (INR)</label>
                        <input
                          type="number"
                          value={fixedAmount}
                          onChange={(e) => setFixedAmount(e.target.value)}
                          className="mt-1.5 w-full rounded-xl border border-white/20 bg-[#121212] px-3.5 py-2.5 text-xs text-white focus:border-white focus:outline-none"
                        />
                      </div>
                    )}

                    <button
                      type="submit"
                      disabled={simulating}
                      className="w-full rounded-full bg-white py-3 text-xs font-semibold text-black hover:bg-neutral-200 transition shadow-[0_0_20px_rgba(255,255,255,0.15)] cursor-pointer"
                    >
                      {simulating ? "Calculating..." : "Run Simulation"}
                    </button>
                  </form>

                  {/* Simulation Results Card */}
                  <div className="rounded-3xl border border-white/15 bg-[#0A0A0A] p-7 flex flex-col justify-between">
                    {simulationResult ? (
                      <div className="space-y-4">
                        <span className="font-mono text-xs uppercase tracking-wider text-neutral-400">
                          Simulation Impact
                        </span>
                        <h4 className="text-xl font-semibold text-white">{simulationResult.title}</h4>
                        <p className="text-sm text-neutral-300 leading-relaxed">
                          {simulationResult.notes?.[0] || simulationResult.assumptions?.[0] || "Calculated using living money model baseline."}
                        </p>

                        <div className="grid grid-cols-3 gap-3 pt-4 border-t border-white/10 text-center">
                          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                            <span className="text-[10px] text-neutral-400">3-Month Delta</span>
                            <p className="mt-1 font-bold text-sm text-white">
                              {formatCurrency(simulationResult.period_impacts?.three_month_impact || 0)}
                            </p>
                          </div>
                          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                            <span className="text-[10px] text-neutral-400">6-Month Delta</span>
                            <p className="mt-1 font-bold text-sm text-white">
                              {formatCurrency(simulationResult.period_impacts?.six_month_impact || 0)}
                            </p>
                          </div>
                          <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                            <span className="text-[10px] text-neutral-400">12-Month Delta</span>
                            <p className="mt-1 font-bold text-sm text-white">
                              {formatCurrency(simulationResult.period_impacts?.twelve_month_impact || 0)}
                            </p>
                          </div>
                        </div>

                        <div className="pt-4 flex justify-end">
                          <button
                            onClick={handleSaveScenario}
                            disabled={saving}
                            className="rounded-full border border-white/20 bg-white/5 px-5 py-2 text-xs font-medium text-white hover:bg-white/15 transition cursor-pointer"
                          >
                            {saving ? "Saving..." : "Save Scenario"}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex h-full flex-col items-center justify-center text-center p-8 text-neutral-500">
                        <Sliders className="h-8 w-8 mb-3" />
                        <p className="text-sm">Configure and run a simulation to preview multi-horizon cash flow deltas.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ========================================================================= */}
            {/* TAB 8: GEMINI 3.5 FLASH LITE AI FINANCIAL COACH */}
            {/* ========================================================================= */}
            {activeTab === "coach" && (
              <div className="space-y-6">
                {/* Coach Header Bar */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-2xl font-bold tracking-tight text-white">
                        AI Financial Coach
                      </h2>
                      <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.15)]">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                        </span>
                        Gemini 3.5 Flash Lite Live
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-neutral-400">
                      Grounded strictly in your uploaded statement facts with deterministic Decimal arithmetic.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleNewConversation}
                      className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/5 px-4 py-2 text-xs font-semibold text-white hover:bg-white/15 hover:border-white/30 transition cursor-pointer shadow-sm"
                    >
                      <RefreshCw className="h-3.5 w-3.5" />
                      <span>+ New Thread</span>
                    </button>
                  </div>
                </div>

                {/* Conversation Threads Pill Bar (if multiple threads exist) */}
                {conversationList && conversationList.length > 0 && (
                  <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-neutral-500 shrink-0">
                      History:
                    </span>
                    {conversationList.slice(0, 5).map((conv) => {
                      const isActive = activeConversationId === conv.id;
                      return (
                        <div
                          key={conv.id}
                          onClick={() => handleSelectConversation(conv.id)}
                          className={`group flex items-center gap-2 rounded-full border px-3.5 py-1.5 transition cursor-pointer shrink-0 ${
                            isActive
                              ? "border-white/40 bg-white/15 text-white font-medium shadow-[0_0_15px_rgba(255,255,255,0.08)]"
                              : "border-white/10 bg-white/[0.03] text-neutral-400 hover:border-white/25 hover:text-white"
                          }`}
                        >
                          <MessageSquare className="h-3 w-3 shrink-0" />
                          <span className="max-w-[140px] truncate text-xs">{conv.title}</span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteConversation(conv.id);
                            }}
                            className="text-neutral-500 hover:text-rose-400 transition"
                            title="Delete thread"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Suggested Exploration Prompts */}
                <div className="rounded-3xl border border-white/10 bg-gradient-to-b from-[#111111] to-[#090909] p-5 shadow-lg">
                  <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-neutral-400">
                    <Sparkles className="h-3.5 w-3.5 text-neutral-400" />
                    <span>Suggested Financial Inquiries:</span>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {starterPrompts.map((prompt, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendCoachMessage(prompt)}
                        disabled={coachLoading}
                        className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-2 text-xs text-neutral-300 hover:border-white/30 hover:bg-white/10 hover:text-white hover:shadow-[0_0_15px_rgba(255,255,255,0.05)] transition disabled:opacity-50 text-left cursor-pointer"
                      >
                        <MessageSquare className="h-3.5 w-3.5 shrink-0 text-neutral-500" />
                        <span>{prompt}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Chat Card (Fixed Viewport with Auto-Scroll) */}
                <div className="rounded-3xl border border-white/15 bg-gradient-to-b from-[#0D0D0D] to-[#050505] shadow-2xl flex flex-col h-[640px] overflow-hidden">
                  {/* Messages Stream */}
                  <div className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth">
                    {coachMessages.map((msg) => {
                      const isUser = msg.sender === "user";
                      return (
                        <div
                          key={msg.id}
                          className={`flex gap-3.5 ${isUser ? "justify-end" : "justify-start"}`}
                        >
                          {/* Coach Avatar */}
                          {!isUser && (
                            <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-purple-500 via-indigo-500 to-pink-500 p-[1.5px] shadow-[0_0_15px_rgba(168,85,247,0.35)] shrink-0 mt-0.5">
                              <div className="h-full w-full rounded-full bg-black flex items-center justify-center">
                                <Sparkles className="h-4 w-4 text-purple-300" />
                              </div>
                            </div>
                          )}

                          {/* Message Bubble Container */}
                          <div
                            className={`flex flex-col ${isUser ? "items-end max-w-[80%]" : "items-start max-w-[85%]"}`}
                          >
                            <div
                              className={`rounded-2xl p-4 text-xs sm:text-sm leading-relaxed ${
                                isUser
                                  ? "rounded-tr-xs bg-white text-black font-medium shadow-md"
                                  : "rounded-tl-xs border border-white/10 bg-[#131313]/90 text-neutral-200 shadow-xl space-y-3"
                              }`}
                            >
                              {!isUser && (
                                <div className="flex items-center justify-between text-[10px] font-mono text-neutral-400 pb-1.5 border-b border-white/5">
                                  <span className="flex items-center gap-1.5 text-white font-semibold">
                                    <Sparkles className="h-3 w-3 text-purple-400" /> PaisaFlow AI Coach
                                  </span>
                                  <span className="text-neutral-500">
                                    {msg.created_at
                                      ? new Date(msg.created_at).toLocaleTimeString([], {
                                          hour: "2-digit",
                                          minute: "2-digit",
                                        })
                                      : "Live"}
                                  </span>
                                </div>
                              )}

                              <div>{renderFormattedMessage(msg.content, isUser)}</div>

                              {/* Grounded Statement Proof Facts Box */}
                              {!isUser && msg.grounded_facts && msg.grounded_facts.length > 0 && (
                                <div className="mt-3 rounded-xl border border-white/10 bg-black/60 p-3.5 space-y-2">
                                  <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider text-emerald-400 font-bold">
                                    <BarChart3 className="h-3.5 w-3.5" /> Verified Statement Proof Facts
                                  </div>
                                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                                    {msg.grounded_facts.map((fact, fIdx) => (
                                      <div
                                        key={fIdx}
                                        className="flex justify-between items-center rounded-lg bg-white/[0.04] border border-white/5 px-3 py-1.5 text-xs"
                                      >
                                        <span className="text-neutral-400">{fact.label}:</span>
                                        <span className="font-mono font-bold text-white">{fact.value}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Policy and Provenance Notice */}
                              {!isUser && (
                                <div className="flex items-center gap-1.5 text-[10px] text-neutral-500 pt-1.5 border-t border-white/5">
                                  <ShieldCheck className="h-3 w-3 text-neutral-400 shrink-0" />
                                  <span>Grounded in deterministic Python Decimal calculations. Not certified SEBI advice.</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {/* User Avatar */}
                          {isUser && (
                            <div className="h-8 w-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-xs font-bold text-white shrink-0 mt-0.5 overflow-hidden">
                              {user?.photoURL ? (
                                <Image
                                  src={user.photoURL}
                                  alt={user.displayName || "User"}
                                  width={32}
                                  height={32}
                                  className="h-full w-full object-cover"
                                />
                              ) : (
                                <UserIcon className="h-4 w-4 text-neutral-300" />
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}

                    {/* Reasoning Indicator */}
                    {coachLoading && (
                      <div className="flex gap-3.5 justify-start items-center">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-purple-500 via-indigo-500 to-pink-500 p-[1.5px] shadow-[0_0_15px_rgba(168,85,247,0.35)] shrink-0">
                          <div className="h-full w-full rounded-full bg-black flex items-center justify-center">
                            <Sparkles className="h-4 w-4 text-purple-300 animate-spin" />
                          </div>
                        </div>
                        <div className="rounded-2xl rounded-tl-xs border border-white/10 bg-[#131313]/90 px-4.5 py-3 flex items-center gap-3 shadow-lg">
                          <div className="flex items-center gap-1">
                            <span className="h-2 w-2 rounded-full bg-purple-400 animate-bounce [animation-delay:-0.3s]" />
                            <span className="h-2 w-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:-0.15s]" />
                            <span className="h-2 w-2 rounded-full bg-pink-400 animate-bounce" />
                          </div>
                          <span className="text-xs text-neutral-400 font-mono">
                            Gemini 3.5 Flash Lite is reasoning over statement numbers...
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Auto-Scroll Anchor */}
                    <div ref={messagesEndRef} className="h-2" />
                  </div>

                  {/* Docked Chat Input Bar */}
                  <div className="p-4 border-t border-white/10 bg-[#0A0A0A]/95 backdrop-blur-md">
                    <div className="relative flex items-center rounded-2xl border border-white/15 bg-[#141414] focus-within:border-white/40 focus-within:ring-2 focus-within:ring-white/10 transition px-4 py-2 gap-2 shadow-inner">
                      <input
                        type="text"
                        placeholder="Ask any question about your statement, expenses, or recurring bills..."
                        value={coachInput}
                        onChange={(e) => setCoachInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && handleSendCoachMessage()}
                        className="flex-1 bg-transparent text-xs sm:text-sm text-white placeholder-neutral-500 focus:outline-none"
                      />
                      <button
                        onClick={() => handleSendCoachMessage()}
                        disabled={coachLoading || !coachInput.trim()}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-white px-4 py-2 text-xs font-semibold text-black hover:bg-neutral-200 disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer shadow-[0_0_15px_rgba(255,255,255,0.15)]"
                      >
                        <Send className="h-3.5 w-3.5" />
                        <span>Send</span>
                      </button>
                    </div>
                    <div className="mt-2 flex items-center justify-between text-[11px] text-neutral-500 px-1 font-mono">
                      <span>Press Enter ↵ to send</span>
                      <span>PaisaFlow • Live Intelligence Engine</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
