# Design

## Source of truth
- Status: Active
- Last refreshed: 2026-08-04
- Primary product surfaces: Today, assistant chat, calendar, tasks and projects, finance, knowledge, communication, and the Action Center.
- Product architecture source: `PRODUCT_ARCHITECTURE.md`.
- Evidence reviewed: `PRODUCT_ARCHITECTURE.md`, `docs/design/FRONTEND_SYSTEM.md`, `docs/design/DOCUMENT_LINKS.md`, `docs/design/DOCUMENT_PROPOSALS.md`, `frontend/src/components/AppShell.tsx`, `frontend/src/components/ui.tsx`, `frontend/src/components/DocumentLinkPanel.tsx`, `frontend/src/components/DocumentProposalPanel.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/components/TodayOverviewWidget.tsx`, `frontend/src/api/state.ts`, `frontend/src/pages/ChatPage.tsx`, and all routes under `frontend/src/pages/`.

## Brand
- Personality: Calm, capable, focused, private, and quietly intelligent.
- Trust signals: Clear system status, explicit confirmation for consequential actions, readable loading/error states, and local-first language.
- Avoid: Neon gradients, dense dashboards, decorative chrome, excessive borders, and visual competition between primary and secondary actions.

## Product goals
- Goals: Make the assistant and personal operations workspace feel effortless; surface the next useful action; make every section feel like one product.
- Non-goals: Changing backend contracts, API behavior, permissions, or data semantics.
- Success signals: Users can reach chat or a core workspace in one glance; all pages share the same shell, spacing, typography, controls, and state treatment.

## Personas and jobs
- Primary personas: A single user managing personal work, communication, money, deadlines, and assistant memory.
- User jobs: Ask the assistant, understand the current state, review important items, and take controlled actions.
- Key contexts of use: Desktop-first work sessions with occasional mobile use; calm focus is preferred over high-alert monitoring.

## Information architecture
- Primary navigation: Home/Today and Chat are always visible; compact workspace sections follow: Calendar, Tasks & Projects, Finance, Knowledge, and Communication.
- Core routes/screens: `/dashboard` (Today projection), `/chat`, `/calendar`, `/commitments`, `/finance` (including subscription context), `/memory`, `/documents`, `/mail`, and `/notifications` (Action Center projection).
- Secondary/compatibility routes: `/deadlines`, `/subscriptions`, `/state`, `/approvals`, `/errors`, `/system`, and `/sandbox` remain available without defining new product domains.
- Content hierarchy: Page title and context, the unified Today projection, high-signal actions and schedule, then supporting domain detail.

## Design principles
- One quiet surface: Use a soft neutral canvas, a single raised surface, and restrained contrast instead of many competing panels.
- Conversation first: Chat and the next recommended action should remain visually obvious from any screen.
- Signal over decoration: Color communicates state or action; it is not used as ornament.
- Tradeoffs: Prefer a compact, highly consistent UI over bespoke page layouts. Preserve compatibility routes and functionality while placing new capabilities inside their owning domain.

## Visual language
- Color: Neutral graphite canvas and surfaces; warm white text; muted gray secondary text; green as the primary action/accent; amber and red only for attention states.
- Typography: System sans stack, normal tracking, clear hierarchy, no all-caps labels except compact metadata.
- Spacing/layout rhythm: 4px base rhythm, 16–24px page gutters, 960–1120px reading widths, generous chat whitespace.
- Shape/radius/elevation: 10–16px radii, 1px low-contrast borders, soft shadows only for overlays and the composer.
- Motion: Short opacity/transform transitions; no pulsing or bouncing except for meaningful loading indicators; respect reduced motion.
- Imagery/iconography: Lucide line icons at 16–20px; no decorative illustrations required for the core product.

## Components
- Existing components to reuse: `AppShell`, `Button`, `Card`, `PageHeader`, `LoadingState`, `EmptyState`, `ErrorState`, and `Dialog`.
- New/changed components: Refresh the shell, shared UI primitives, global tokens, dashboard cards, chat surface, `TodayOverviewWidget`, Action Center lifecycle controls, inline `DocumentLinkPanel`, and collapsed `DocumentProposalPanel` inside Document Vault cards.
- Variants and states: neutral/primary/success/danger buttons; active/hover/focus navigation; loading, empty, error, disabled, and confirmation states.
- Token/component ownership: Global color, spacing, focus, and surface tokens live in `frontend/src/index.css`; shared component behavior lives in `frontend/src/components/ui.tsx`.

## Accessibility
- Target standard: WCAG 2.1 AA intent for contrast, keyboard access, and readable target sizes.
- Keyboard/focus behavior: Every interactive control has a visible focus ring; icon-only controls have labels; dialogs expose modal semantics.
- Contrast/readability: Do not rely on color alone; secondary text remains readable on the neutral canvas.
- Screen-reader semantics: Preserve headings, landmarks, labels, and button semantics in existing routes.
- Reduced motion and sensory considerations: Disable nonessential transitions under `prefers-reduced-motion`.

## Responsive behavior
- Supported breakpoints/devices: Desktop and touch-friendly mobile layouts from 320px upward.
- Layout adaptations: Collapsible desktop sidebar becomes four primary bottom actions (Chat, Tasks, Notifications, Upload) plus an expandable «Ещё» menu; cards stack; chat composer remains reachable.
- Touch/hover differences: 44px minimum mobile targets; hover styling is additive and never required for comprehension.

## Interaction states
- Loading: Use compact skeleton-like or spinner states with a short human label.
- Empty: Explain what is absent and what the user can do next.
- Error: Inline, recoverable, and paired with retry where possible.
- Success: Subtle green confirmation or updated content; avoid intrusive toasts unless already supported.
- Disabled: Preserve layout, lower contrast, and communicate why through nearby copy when needed.
- Offline/slow network, if applicable: Keep local state usable and show recoverable request errors. Today uses the existing state snapshot and exposes one retry control; Action Center mutations show inline recovery without losing the feed.
- Document links: Keep the relation panel inline, show the current target label with its owning-domain icon, and make unlinking local to the relation. Do not introduce a separate link-management page.
- Document proposals: Keep extraction collapsed and user-triggered; show the matched evidence before offering task/event choices, then route confirmation through Action Center instead of duplicating approval controls in the document card.

## Content voice
- Tone: Clear, concise, human, and calm.
- Terminology: Prefer familiar Russian labels; use sentence case rather than title case or uppercase system jargon.
- Microcopy rules: Describe what is happening and the next action; avoid technical implementation details in user-facing copy.

## Implementation constraints
- Framework/styling system: React 19, TypeScript, React Router, Tailwind CSS v4, Lucide icons.
- Design-token constraints: Extend existing shared components and CSS tokens; do not add a new dependency or parallel design system.
- Performance constraints: Keep routes lazy-loaded and avoid introducing large visual assets. Today reuses one cached state snapshot instead of adding separate dashboard fetches.
- Compatibility constraints: Existing API routes, page behavior, and mobile navigation must remain intact.
- Test/screenshot expectations: `npm run build` and `npm run lint`; smoke-check the shell, dashboard, chat, and one data-heavy page in a browser when the backend is available.

## Open questions
- [ ] Confirm whether a light theme or theme switcher is desired; current implementation assumes a neutral dark theme aligned with the existing app and ChatGPT dark mode.
- [x] Product name is Mira; use it consistently across user-facing surfaces and documentation.
