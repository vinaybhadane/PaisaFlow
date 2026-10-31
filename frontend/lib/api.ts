/**
 * API client for interacting with the PaisaFlow FastAPI backend.
 * Supports Vercel multiple-services deployment with BACKEND_URL service binding.
 */

export function getApiBaseUrl(): string {
  // 1. Explicitly configured via environment variable
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // 2. Server-side in Node.js (Vercel service binding)
  if (typeof window === "undefined") {
    if (process.env.BACKEND_URL) {
      return `${process.env.BACKEND_URL}/api/v1`;
    }
    return "http://127.0.0.1:8000/api/v1";
  }
  // 3. Client-side in local browser development
  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ) {
    return "http://127.0.0.1:8000/api/v1";
  }
  // 4. Client-side production on Vercel: use relative path routed via vercel.json rewrites
  return "/api/v1";
}

let currentUserId: string | null = null;
let currentUserEmail: string | null = null;
let currentUserName: string | null = null;

export function setActiveUserId(userId: string | null, email?: string | null, name?: string | null) {
  currentUserId = userId;
  currentUserEmail = email || null;
  currentUserName = name || null;
  if (typeof window !== "undefined") {
    if (userId) {
      localStorage.setItem("paisaflow_active_user_id", userId);
      if (email) localStorage.setItem("paisaflow_user_email", email);
      if (name) localStorage.setItem("paisaflow_user_name", name);
    } else {
      localStorage.removeItem("paisaflow_active_user_id");
      localStorage.removeItem("paisaflow_user_email");
      localStorage.removeItem("paisaflow_user_name");
    }
  }
}

export function getActiveUserId(): string | null {
  if (currentUserId) return currentUserId;
  if (typeof window !== "undefined") {
    currentUserId = localStorage.getItem("paisaflow_active_user_id");
    currentUserEmail = localStorage.getItem("paisaflow_user_email");
    currentUserName = localStorage.getItem("paisaflow_user_name");
  }
  return currentUserId;
}

export function getActiveUserProfile() {
  getActiveUserId();
  return {
    userId: currentUserId,
    email: currentUserEmail,
    displayName: currentUserName,
  };
}

export interface ApiResponse<T> {
  data: T;
  meta: {
    request_id: string;
    generated_at: string;
  };
}

export interface DemoPersona {
  user_id: string;
  display_name: string;
  email: string | null;
  persona_key: string;
  profile_label: string;
  is_synthetic: boolean;
}

export interface FinancialInsight {
  insight_type: string;
  title: string;
  explanation: string;
  metric_value: string;
  change_percentage: number | null;
  period: string;
  confidence: string;
  severity: "info" | "positive" | "warning";
  evidence: Record<string, unknown>;
}

export interface CategorySpendingItem {
  category_id: string | null;
  category_name: string;
  current_spend: string | number;
  previous_spend: string | number;
  change_amount: string | number;
  change_percentage: number | null;
  spend_percentage: number;
  is_essential: boolean;
  trend: "increasing" | "decreasing" | "stable";
}

export interface MerchantSpendingItem {
  merchant_name: string;
  merchant_id: string | null;
  total_amount: string | number;
  transaction_count: number;
  percentage_of_total: number;
}

export interface CategorySpendingResponse {
  period_start: string;
  period_end: string;
  currency: string;
  total_gross_expense: string;
  total_refunds: string;
  total_net_expense: string;
  essential_spend: string;
  discretionary_spend: string;
  essential_percentage: number;
  discretionary_percentage: number;
  categories: CategorySpendingItem[];
  top_merchants: MerchantSpendingItem[];
}

export interface MonthlyTrendItem {
  month: string;
  month_label: string;
  total_gross_expense: string;
  total_net_expense: string;
  total_income: string;
  savings_rate: number | null;
  essential_spend: string;
  discretionary_spend: string;
}

export interface ForecastMonthItem {
  month_index: number;
  target_month: string;
  target_month_label: string;
  expected_income: string;
  expected_recurring_expenses: string;
  expected_variable_expenses: string;
  expected_total_expenses: string;
  projected_net_cash_flow: string;
  projected_cumulative_savings: string;
  expected_available_money: string;
}

export interface FinancialForecastResponse {
  generated_date: string;
  horizon_months: number;
  currency: string;
  baseline_monthly_income: string;
  baseline_recurring_expenses: string;
  baseline_variable_expenses: string;
  baseline_monthly_expenses: string;
  baseline_net_cash_flow: string;
  data_coverage_status: string;
  is_forecastable: boolean;
  months: ForecastMonthItem[];
  assumptions: string[];
  notes: string[];
}

export interface ScenarioRunRequest {
  scenario_type: string;
  input_parameters: Record<string, unknown>;
  period_start?: string;
  period_end?: string;
}

export interface ScenarioPeriodImpacts {
  monthly_delta: string;
  three_month_impact: string;
  six_month_impact: string;
  twelve_month_impact: string;
}

export interface SimulationRunResponse {
  scenario_type: string;
  title: string;
  currency: string;
  baseline: Record<string, string>;
  scenario: Record<string, string>;
  delta: Record<string, string>;
  period_impacts: ScenarioPeriodImpacts;
  assumptions: string[];
  notes: string[];
  calculation_version: string;
}

export interface SavedScenario {
  id: string;
  user_id: string;
  title: string;
  scenario_type: string;
  input_parameters: Record<string, unknown>;
  baseline_result: Record<string, unknown>;
  scenario_result: Record<string, unknown>;
  assumptions: Record<string, unknown>;
  calculation_version: string;
  created_at: string;
}

export interface CoachMessage {
  id: string;
  conversation_id: string;
  sender: "user" | "coach";
  content: string;
  grounded_facts?: Array<{ label: string; value: string }>;
  assumptions?: string[];
  warnings?: string[];
  created_at: string;
  is_live_gemini?: boolean;
}

export interface CoachConversationSummary {
  id: string;
  user_id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface CoachConversationDetail {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: CoachMessage[];
}

export interface TransactionItem {
  id: string;
  user_id: string;
  account_id: string;
  transaction_date: string;
  posted_date?: string | null;
  original_description: string;
  normalized_description: string;
  merchant_name?: string | null;
  amount: string | number;
  currency: string;
  direction: "credit" | "debit";
  transaction_type: string;
  category_id?: string | null;
  category_name?: string | null;
  confidence?: string | null;
  review_status: string;
  duplicate_fingerprint?: string | null;
  is_excluded: boolean;
  notes?: string | null;
}

export interface PaginatedTransactions {
  items: TransactionItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CategoryItem {
  id: string;
  name: string;
  category_type: string;
  parent_id?: string | null;
  is_system: boolean;
  sort_order: number;
  subcategories?: CategoryItem[];
}

export interface ImportCandidate {
  row_id?: string;
  row_index?: number;
  index?: number;
  transaction_date: string;
  posted_date?: string | null;
  original_description: string;
  normalized_description?: string;
  merchant_name?: string | null;
  resolved_merchant?: string | null;
  amount: string | number;
  currency?: string;
  direction: string;
  transaction_type?: string;
  suggested_category?: string | null;
  confidence?: string | null;
  duplicate_status?: string;
  duplicate_fingerprint?: string | null;
  is_duplicate?: boolean;
  is_excluded?: boolean;
  raw_data?: Record<string, string>;
}

export interface ImportPreviewData {
  import_id: string;
  filename?: string;
  source_type?: string;
  status: string;
  total_rows?: number;
  valid_count?: number;
  rejected_count?: number;
  total_candidates?: number;
  duplicate_count: number;
  invalid_count?: number;
  valid_rows?: ImportCandidate[];
  candidates?: ImportCandidate[];
  rejected_rows?: unknown[];
  warnings?: string[];
}

export interface RecurringCommitmentItem {
  id: string;
  user_id: string;
  merchant_id?: string | null;
  display_name: string;
  cadence: string;
  typical_amount: string | number;
  monthly_planning_equivalent: string | number;
  annual_projected_cost: string | number;
  currency: string;
  confidence: string;
  status: "likely" | "confirmed" | "rejected" | "review_required";
  last_observed_date?: string | null;
  next_expected_date?: string | null;
  evidence?: Record<string, unknown> | null;
}

export interface FinancialFactItem {
  id: string;
  fact_type: string;
  label: string;
  amount: string | number;
  currency: string;
  source_type: string;
  effective_from: string;
  effective_to?: string | null;
  confidence: string;
}

export interface LivingProfileData {
  user_id: string;
  as_of_date: string;
  active_facts: FinancialFactItem[];
  current_period_summary: {
    period_start: string;
    period_end: string;
    income_total: string;
    expense_net: string;
    net_cash_flow: string;
    savings_rate?: string | null;
  };
  recurring_commitments: RecurringCommitmentItem[];
}

export async function fetchFromApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;
  const userId = getActiveUserId();

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  };

  if (!options.body || !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (userId) {
    headers["X-User-Id"] = userId;
    if (currentUserEmail) headers["X-User-Email"] = currentUserEmail;
    if (currentUserName) headers["X-User-Name"] = currentUserName;
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API Error [${response.status}]: ${errorText}`);
  }

  const json: ApiResponse<T> = await response.json();
  return json.data;
}

export const paisaApi = {
  // Demo Personas
  getPersonas: () => fetchFromApi<DemoPersona[]>("/profile/personas"),

  // Living Profile & Financial Summary
  getProfile: () => fetchFromApi<LivingProfileData>("/profile"),
  getFinancialSummary: (periodStart?: string, periodEnd?: string) => {
    let url = "/financial-summary";
    const params = [];
    if (periodStart) params.push(`period_start=${periodStart}`);
    if (periodEnd) params.push(`period_end=${periodEnd}`);
    if (params.length > 0) url += `?${params.join("&")}`;
    return fetchFromApi<Record<string, unknown>>(url);
  },

  // Insights & Spending
  getInsights: () => fetchFromApi<FinancialInsight[]>("/insights"),
  getSpendingCategories: () => fetchFromApi<CategorySpendingResponse>("/spending/categories"),
  getSpendingTrends: (months = 6) => fetchFromApi<MonthlyTrendItem[]>(`/spending/trends?months=${months}`),
  getTopMerchants: () => fetchFromApi<MerchantSpendingItem[]>("/spending/merchants"),

  // Forecasting
  getForecast: (horizon = 6) => fetchFromApi<FinancialForecastResponse>(`/forecast?horizon=${horizon}`),

  // What-If Simulations
  runSimulation: (req: ScenarioRunRequest) =>
    fetchFromApi<SimulationRunResponse>("/simulations/run", {
      method: "POST",
      body: JSON.stringify(req),
    }),
  saveScenario: (data: {
    title: string;
    scenario_type: string;
    input_parameters: Record<string, unknown>;
    baseline_result: Record<string, unknown>;
    scenario_result: Record<string, unknown>;
    assumptions: Record<string, unknown>;
  }) =>
    fetchFromApi<SavedScenario>("/simulations", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  listScenarios: () => fetchFromApi<SavedScenario[]>("/simulations"),
  deleteScenario: (id: string) =>
    fetchFromApi<{ status: string; id: string }>(`/simulations/${id}`, {
      method: "DELETE",
    }),

  // AI Financial Coach
  sendCoachMessage: (message: string, conversation_id?: string) =>
    fetchFromApi<CoachMessage>("/coach/messages", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id }),
    }),
  listCoachConversations: () => fetchFromApi<CoachConversationSummary[]>("/coach/conversations"),
  getCoachConversation: (id: string) => fetchFromApi<CoachConversationDetail>(`/coach/conversations/${id}`),
  deleteCoachConversation: (id: string) =>
    fetchFromApi<{ deleted: boolean; conversation_id: string }>(`/coach/conversations/${id}`, {
      method: "DELETE",
    }),
  getCoachPrompts: () => fetchFromApi<{ prompts: string[] }>("/coach/prompts"),

  // Transactions Management
  getTransactions: (page = 1, pageSize = 25, search?: string, categoryId?: string, reviewStatus?: string) => {
    let url = `/transactions?page=${page}&page_size=${pageSize}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (categoryId) url += `&category_id=${categoryId}`;
    if (reviewStatus) url += `&review_status=${reviewStatus}`;
    return fetchFromApi<PaginatedTransactions>(url);
  },
  updateTransaction: (
    id: string,
    data: {
      category_id?: string;
      review_status?: string;
      notes?: string;
      create_future_rule?: boolean;
    }
  ) =>
    fetchFromApi<TransactionItem>(`/transactions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  getTransactionExplanation: (id: string) =>
    fetchFromApi<Record<string, unknown>>(`/transactions/${id}/explanation`),
  createTransactionRule: (
    txId: string,
    data: { category_id?: string; scope_type: string }
  ) =>
    fetchFromApi<Record<string, unknown>>(`/transactions/${txId}/create-rule`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Categories
  getCategories: () => fetchFromApi<{ categories: CategoryItem[] }>("/categories"),

  // Recurring Commitments
  getRecurringCommitments: (status?: string) => {
    const url = status ? `/recurring?status=${status}` : "/recurring";
    return fetchFromApi<RecurringCommitmentItem[]>(url);
  },
  detectSubscriptions: () =>
    fetchFromApi<RecurringCommitmentItem[]>("/recurring/detect", {
      method: "POST",
    }),
  reviewRecurringCommitment: (id: string, action: "confirm" | "reject" | "review_required") =>
    fetchFromApi<RecurringCommitmentItem>(`/recurring/${id}/review`, {
      method: "POST",
      body: JSON.stringify({ action }),
    }),

  // Statement Ingestion
  uploadStatement: (formData: FormData) =>
    fetchFromApi<{ id: string; status: string; total_rows: number }>("/imports", {
      method: "POST",
      body: formData,
    }),
  getImportPreview: (importId: string) =>
    fetchFromApi<ImportPreviewData>(`/imports/${importId}/preview`),
  confirmImport: (importId: string, acceptedRowIds?: string[]) =>
    fetchFromApi<{
      status: string;
      total_rows: number;
      accepted_rows: number;
      committed_transactions_count: number;
      message?: string;
    }>(`/imports/${importId}/confirm`, {
      method: "POST",
      body: JSON.stringify(acceptedRowIds ? { accepted_row_ids: acceptedRowIds } : {}),
    }),
};
