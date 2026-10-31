# 05 — UI/UX Guidelines, Landing Page and Application Design

## 1. Design objective
Create a premium, trustworthy fintech SaaS experience: clear, calm, modern and data-rich without intimidation. The landing page and logged-in application must share one visual system. Avoid a generic admin template.

## 2. Brand
Name: PaisaFlow. Tagline: "Your Money. Your Flow. Your Future." Attributes: clarity, control, confidence, adaptability and transparency. Voice: supportive, direct, non-judgmental and honest.

## 3. Visual direction
Use a refined light-first fintech design:
- Background `#F7F9FC`
- Surface `#FFFFFF`
- Primary text `#142033`
- Muted text `#667085`
- Border `#E5EAF0`
- Primary action `#123F36`
- Soft accent `#DDF4EC`
- Success `#16845B`
- Warning `#B7791F`
- Danger `#C2413B`

Use color plus text/icon labels; never communicate status by color alone. Keep shadows restrained, borders subtle and spacing consistent.

## 4. Typography
Use Inter or Geist. Tabular numerals for money.
- Hero: 48–68px desktop, 36–44px mobile.
- Page title: 28–36px.
- Section title: 20–24px.
- Card title: 15–18px.
- Body: 14–16px.
- Labels: 12–13px.
Maintain readable line lengths and contrast.

## 5. Landing page — complete required specification

### Navigation
Logo/wordmark left. Links: How it works, Features, Money Model, Privacy. Right side: Sign in if authentication exists and primary CTA "Explore demo". Sticky or subtly fixed after scroll. Accessible mobile menu. No dead links.

### Hero
Headline direction: **"Your money has a story. PaisaFlow helps you understand what comes next."**
Supporting copy: "Bring your transactions, goals and recurring expenses into one living money model. See what changed, explore what-if scenarios and make your next money decision with clarity."
Primary CTA: Explore the demo. Secondary CTA: See how it works.
Visual: realistic synthetic dashboard preview with monthly cash flow, goal progress, recurring insight and scenario card. Label every preview number illustrative/demo. Do not use unsupported savings statistics or fake testimonials.

### Problem section
Explain that transaction lists alone do not reveal the full picture: recurring costs accumulate, categories need correction, goals are disconnected from spending and life changes alter the plan. Be empathetic, never shame users.

### Feature grid
Cards:
1. Understand every transaction.
2. Learn from your corrections.
3. Spot recurring commitments.
4. Keep a living money profile.
5. Plan goals with realistic assumptions.
6. Explore what-if scenarios.
7. Receive useful nudges.
8. Review each month.
Each card has icon, short benefit and concise explanation.

### How it works
1. Bring in synthetic statements.
2. Review and correct the transaction picture.
3. Let the money model update.
4. Plan, simulate and learn.

### What-if showcase
A working sample scenario with baseline dining spend, reduction slider/presets, monthly improvement, annualized effect and goal impact. Use deterministic sample calculation. Mark data illustrative. Do not imply it changes a user's actual profile.

### Living Money Model section
Show a timeline: baseline month → new rent value arrives → fixed-cost model updates → goal forecast recalculates → coach explains the change. Distinguish confirmed and inferred facts.

### Privacy and trust
State: hackathon prototype uses synthetic data only; no bank account is connected; no payment is initiated; calculations are deterministic; users can review and correct imported data.

### FAQ
Answer:
- Does PaisaFlow connect to my bank? No, not in this hackathon prototype.
- Is demo data real? No, all demo data is synthetic.
- How does correction learning work? Explicit corrections can create scoped future rules.
- Does AI calculate money totals? No, deterministic services do.
- Does PaisaFlow recommend investments? No.
- Can demo data be deleted? Explain reset/delete feature.

### Footer
Product summary, working in-page links, docs link if public, privacy and contact placeholders clearly marked. Do not invent a company address or email.

## 6. App information architecture
Navigation: Overview, Transactions, Recurring, Budgets, Goals, Simulator, AI Coach, Monthly Review, Settings. Desktop sidebar + topbar; mobile compact or bottom navigation.

## 7. Overview dashboard
Show selected period, income/expense/net cash flow, spending chart, budget utilization, recurring summary, goal progress, recent transactions, profile changes and evidence-backed nudges. Prioritize clarity over density. Never hardcode production totals.

## 8. Transactions
Search/filter by date, category, type and merchant. Show date, description, amount, type, category, confidence and review state. Include import action, details drawer, correction action, provenance and warnings.

## 9. Recurring
Show merchant, cadence, typical/range amount, last observed, expected next date when defensible, confidence, evidence, price-change timeline and review controls.

## 10. Goals
Goal cards with target, saved amount, progress, target date, required contribution and scenario comparison. Add/edit flow with validation.

## 11. Simulator
Scenario selector, bounded inputs, baseline, scenario, difference, goal impact, assumptions, chart, save and reset. Clearly distinguish scenario from actual data.

## 12. AI Coach
Chat with suggested questions and context chips. Display grounded facts, calculation cards, assumptions and missing-data notes. No fake typing or unperformed action claims.

## 13. Monthly Review
Month selector, data coverage, totals, categories, budget variance, recurring changes, goals, evidence-backed insights and export if implemented.

## 14. Settings
Profile/locale, currency, import history, correction rules, notifications, privacy, AI status, reset demo and delete demo data.

## 15. Reusable components
AppShell, Sidebar, Topbar, PageHeader, MetricCard, MoneyAmount, PeriodSelector, CategoryBadge, ConfidenceBadge, TransactionTable, ReviewDrawer, RecurringCard, GoalCard, ScenarioInput, ScenarioResult, InsightCard, EmptyState, ErrorState, Skeleton, ConfirmDialog and AccessibleChart.

## 16. Motion
Use subtle hover, chart, drawer and progress transitions. Respect `prefers-reduced-motion`. Avoid distracting parallax or excessive animations.

## 17. Responsive QA
Test approximately 360px, 390–430px, 768px, 1024px and 1440px. Prevent overflow. Adapt data tables intentionally.

## 18. Accessibility
Target WCAG 2.2 AA where practical: semantic headings, keyboard navigation, visible focus, labelled forms, contrast, chart text equivalents, non-color status, reduced motion and accessible dialogs.

## 19. UX acceptance
Landing page explains product quickly; CTA works; all links work; demo values labelled; app values sourced from API or explicit demo fixture; all pages have loading/empty/error states; mobile works; no dead controls; no fake bank-connect/cancellation actions.
