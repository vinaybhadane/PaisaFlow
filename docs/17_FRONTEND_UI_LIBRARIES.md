# 17 — Frontend UI Libraries: Unlumen UI + SmoothUI

## Purpose
This document specifies how to integrate Unlumen UI and SmoothUI into the PaisaFlow frontend. Both libraries provide React components and are compatible with the existing Next.js + React + TypeScript direction. They are not Vue component libraries. Do not convert the frontend to Vue just to use them.

Official references:
- Unlumen UI: https://ui.unlumen.com/
- Unlumen installation: https://unlumen-ui-docs.vercel.app/docs/installation
- SmoothUI: https://smoothui.dev/
- SmoothUI installation: https://smoothui.dev/docs/guides/installation
- SmoothUI getting started: https://smoothui.dev/docs/guides/getting-started

## 1. Compatibility and prerequisites

Use the following baseline for a new or upgraded frontend:
- Node.js 20+ (use the currently supported LTS release).
- React 19 or later.
- Next.js App Router with TypeScript.
- Tailwind CSS 4 or later.
- shadcn/ui initialized in the frontend project.
- Motion package version 12.23.0 or later where required by installed Unlumen components.
- A package manager: npm, pnpm, yarn or bun.

Before changing versions in an existing project, inspect its `package.json`, lockfile, Next.js version, React version and Tailwind setup. Do not force-upgrade a working project without checking compatibility.

## 2. Why both libraries are used

### Unlumen UI
Use for polished, focused interactions and reusable animated elements. In PaisaFlow, use it for:
- Contextual tooltips explaining synthetic data, inferred recurring payments and confidence.
- Small interaction details around data cards and review actions.
- Carefully selected motion components that make the product feel refined.

Unlumen UI components are installed as source files through the shadcn CLI. They become part of the repository and can be customized. The registry contains free and Pro components. Free components do not require a license. Pro components require a valid Unlumen license and registry authentication. Do not attempt to bypass Pro licensing.

### SmoothUI
Use for high-quality animated controls and prominent interactive moments. In PaisaFlow, use it for:
- Primary and secondary CTA button interactions.
- Smooth transitions and feedback.
- Selected animated controls or showcase elements.
- Carefully chosen motion elements in the landing page and onboarding.

SmoothUI components are also added to the project as source files using its CLI or the shadcn registry. The installed source should be reviewed and customized to match PaisaFlow's design system.

## 3. Recommended frontend setup

Run commands from the frontend directory, not the repository root.

### Step 1 — Create or inspect the Next.js project

If the frontend does not exist yet:

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app
cd frontend
```

If Antigravity has already created the frontend, do not recreate it. Open the existing frontend directory and inspect its configuration.

### Step 2 — Install the base dependencies

npm:

```bash
npm install motion lucide-react clsx tailwind-merge
```

pnpm:

```bash
pnpm add motion lucide-react clsx tailwind-merge
```

yarn:

```bash
yarn add motion lucide-react clsx tailwind-merge
```

bun:

```bash
bun add motion lucide-react clsx tailwind-merge
```

Use the dependency versions resolved by the package manager and commit the lockfile. `motion` is used by components that import `motion/react`. `lucide-react` supplies icons used by the application. `clsx` and `tailwind-merge` are useful for the shared class-name helper.

### Step 3 — Initialize shadcn/ui

Only run initialization if `components.json` does not already exist. Do not overwrite an existing shadcn configuration without reviewing it.

npm:

```bash
npx shadcn@latest init
```

pnpm:

```bash
pnpm dlx shadcn@latest init
```

yarn:

```bash
yarn dlx shadcn@latest init
```

bun:

```bash
bunx --bun shadcn@latest init
```

Choose the existing Tailwind setup, CSS file and import alias when prompted. Confirm the generated `components.json` points to the project's actual component and utility directories. The common alias is `@/`.

### Step 4 — Install SmoothUI components

Recommended SmoothUI CLI method:

```bash
npx smoothui-cli@latest add smooth-button
```

Equivalent package-manager commands:

```bash
pnpm dlx smoothui-cli@latest add smooth-button
yarn dlx smoothui-cli@latest add smooth-button
bunx --bun smoothui-cli@latest add smooth-button
```

Alternatively use the shadcn registry:

```bash
npx shadcn@latest add @smoothui/smooth-button
```

Equivalent commands:

```bash
pnpm dlx shadcn@latest add @smoothui/smooth-button
yarn dlx shadcn@latest add @smoothui/smooth-button
bunx --bun shadcn@latest add @smoothui/smooth-button
```

To browse available SmoothUI components:

```bash
npx smoothui-cli@latest list
```

To open the interactive component picker:

```bash
npx smoothui-cli@latest add
```

SmoothUI's standard registry installation does not require an extra registry entry in `components.json`. Its CLI or shadcn command copies the selected component source and resolves component dependencies.

### Step 5 — Install Unlumen UI components

Unlumen UI uses the shadcn registry. Install a free component such as `floating-tooltip`:

npm:

```bash
npx shadcn@latest add @unlumen-ui/floating-tooltip
```

pnpm:

```bash
pnpm dlx shadcn@latest add @unlumen-ui/floating-tooltip
```

yarn:

```bash
yarn dlx shadcn@latest add @unlumen-ui/floating-tooltip
```

bun:

```bash
bunx --bun shadcn@latest add @unlumen-ui/floating-tooltip
```

The component source is copied into the project. The documented import for this component is:

```tsx
import { FloatingTooltip } from "@/components/unlumen-ui/floating-tooltip";
```

Use the component according to its installed source and API. Example usage:

```tsx
<FloatingTooltip.Provider>
  <FloatingTooltip.Trigger content="Illustrative synthetic demo data">
    <span>Demo data</span>
  </FloatingTooltip.Trigger>
</FloatingTooltip.Provider>
```

Do not assume every Unlumen component is free. Check the component's own page. For a Pro component only, follow the official license activation process. Keep `UNLUMEN_LICENSE_KEY` in `.env.local` and out of source control. Configure the registry authentication exactly as described by Unlumen's current documentation. Never commit the license key.

### Step 6 — Verify generated files and aliases

After installing, inspect the actual generated files. Component names and output paths may vary by registry version or shadcn configuration. The intended organization is:

```text
frontend/
├── app/
│   ├── layout.tsx
│   ├── page.tsx
│   └── globals.css
├── components/
│   ├── ui/
│   ├── smoothui/
│   │   └── ui/
│   │       └── SmoothButton.tsx
│   └── unlumen-ui/
│       └── floating-tooltip.tsx
├── lib/
│   └── utils.ts
├── components.json
├── package.json
└── ...
```

If the CLI creates a different path, update imports to match the actual generated path. Do not create duplicate components just to force the example path.

## 4. PaisaFlow UI composition rules

Use the two libraries as complementary component sources, not as two competing design systems.

- SmoothUI: primary CTA, high-visibility interactive controls and selected animated transitions.
- Unlumen UI: contextual tooltips and small polished interaction patterns.
- shadcn/ui: standard form controls, dialogs, dropdowns, tabs and accessible primitives where a specialized animated component is not needed.
- Tailwind CSS: layout, responsive behavior, typography, spacing and visual tokens.
- Motion: use only where needed by components or custom interactions.

Do not install dozens of components. Install only components used by a real screen. Review every generated component for keyboard behavior, reduced-motion support, focus states and bundle impact.

## 5. PaisaFlow design tokens

Keep the existing PaisaFlow light-first visual direction:
- Page background: `#F7F9FC`
- Surface: `#FFFFFF`
- Main text: `#142033`
- Muted text: `#667085`
- Border: `#E5EAF0`
- Primary action: `#123F36`
- Soft accent: `#DDF4EC`
- Success: `#16845B`
- Warning: `#B7791F`
- Danger: `#C2413B`

The components must be customized to these tokens. Do not leave default demo colors if they conflict with the brand.

## 6. Where to use them in PaisaFlow

### Landing page
- SmoothUI primary CTA in hero and final CTA.
- SmoothUI hover/press motion on key interactive controls.
- Unlumen tooltip for "Synthetic demo" and explanatory feature labels.
- Keep hero headline, value proposition and primary CTA clear. Animation must not distract from the product.

### Dashboard
- Unlumen tooltip on metric definitions, confidence labels and inferred recurring commitments.
- SmoothUI for selected high-value interactions, not every card.
- Charts must remain readable and have text summaries.

### Transactions
- Use tooltip to explain categorization confidence and review status.
- Do not hide transaction details inside hover-only UI. Tooltips are supplementary.

### Recurring commitments
- Explain "Likely recurring" versus "confirmed by you".
- Explain possible price changes with evidence and dates.

### Simulator
- Use smooth input feedback if it does not interfere with keyboard or screen-reader operation.
- Keep financial calculations deterministic and display the exact assumptions.

## 7. Accessibility and performance requirements

- All actions must work with keyboard.
- Provide visible focus indicators.
- Do not use hover as the only way to expose important information.
- Respect `prefers-reduced-motion`.
- Avoid continuous animation in financial dashboards.
- Avoid layout shifts when animated components load.
- Keep touch targets comfortable on mobile.
- Test on narrow mobile screens and desktop.
- Ensure animation does not delay important financial content.
- Check that components do not introduce hydration errors in Next.js.

## 8. Next.js implementation notes

- Next.js App Router pages are Server Components by default.
- Interactive animated components may require Client Components.
- Add `"use client"` only to the component that needs browser interaction or React state.
- Do not convert the entire app to client rendering unnecessarily.
- Keep financial calculations in backend services. UI sliders may request a backend simulation but must not become the authoritative calculation engine.
- Inspect each installed component for its own client/server requirements.

## 9. Verification checklist

After installation:

1. `npm run dev` starts without errors.
2. `npm run lint` passes.
3. `npx tsc --noEmit` passes if the project exposes TypeScript checks.
4. Landing page renders without hydration warnings.
5. SmoothUI button renders and its action works.
6. Unlumen tooltip opens and is accessible.
7. Both components match PaisaFlow colors and typography.
8. Reduced-motion preference is respected.
9. Mobile layout has no horizontal overflow.
10. No Pro-only component is installed without a valid license.
11. `.env.local` and all secrets are gitignored.
12. Package lockfile is updated and committed.

## 10. Official documentation and source of truth

Registry commands and component APIs can change. Before installation, Antigravity must check the official documentation linked at the top of this file and inspect the component's current installation instructions. The installed source code in the repository is the final reference for its exact props and import path.
