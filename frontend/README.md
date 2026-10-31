# PaisaFlow Frontend — UI Library Setup

This frontend uses Next.js + React + TypeScript. The UI layer combines:
- Unlumen UI for polished contextual interactions and tooltips.
- SmoothUI for animated buttons and selected high-impact interactions.
- shadcn/ui for accessible base primitives.
- Tailwind CSS for the PaisaFlow visual system.

## Important
Unlumen UI and SmoothUI are React libraries. Do not use them in a Vue.js application. Keep the project's Next.js + React frontend.

## Install

Run from this directory:

```bash
npm install motion lucide-react clsx tailwind-merge
npx shadcn@latest init
npx smoothui-cli@latest add smooth-button
npx shadcn@latest add @unlumen-ui/floating-tooltip
```

If `components.json` already exists, do not run shadcn initialization again without reviewing it.

For pnpm:

```bash
pnpm add motion lucide-react clsx tailwind-merge
pnpm dlx shadcn@latest init
pnpm dlx smoothui-cli@latest add smooth-button
pnpm dlx shadcn@latest add @unlumen-ui/floating-tooltip
```

For yarn:

```bash
yarn add motion lucide-react clsx tailwind-merge
yarn dlx shadcn@latest init
yarn dlx smoothui-cli@latest add smooth-button
yarn dlx shadcn@latest add @unlumen-ui/floating-tooltip
```

For bun:

```bash
bun add motion lucide-react clsx tailwind-merge
bunx --bun shadcn@latest init
bunx --bun smoothui-cli@latest add smooth-button
bunx --bun shadcn@latest add @unlumen-ui/floating-tooltip
```

SmoothUI can alternatively be installed with:

```bash
npx shadcn@latest add @smoothui/smooth-button
```

See `../docs/17_FRONTEND_UI_LIBRARIES.md` for prerequisites, compatibility, component selection, Pro licensing, Next.js boundaries, design rules and verification.

## Start

```bash
npm run dev
```

Open `http://localhost:3000`.

## Expected generated component imports

The sample landing page expects the SmoothUI registry installation to provide:

```tsx
import SmoothButton from "@/components/smooth-button";
import { FloatingTooltip } from "@/components/unlumen-ui/floating-tooltip";
```

Registry output paths can differ depending on the CLI version and `components.json` aliases. Inspect the generated files and update the imports if needed. Do not create a fake placeholder component to hide an unsuccessful install.

## Important product rules

- Use synthetic demo data only.
- Keep financial arithmetic in backend services.
- Do not add animations that obscure money values or warnings.
- Label illustrative dashboard values as synthetic.
- Respect keyboard access and reduced-motion preferences.
