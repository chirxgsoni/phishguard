# PhishGuard — Frontend Build Prompt (for Claude)

## ART Breakdown
- **Act as:** Senior frontend/product designer specializing in dark, high-contrast security and dev-tool dashboards.
- **Request:** Build the complete PhishGuard React site — a single app containing public landing + auth, an authenticated Dashboard, a Scan/Submit surface, a Connections page, and a Reports view — matching the black + neon-green terminal aesthetic described below.
- **Terms:** Use the exact color tokens, component list, and states specified. Code against the API contract given — do not invent different endpoint shapes. Deploy target is Vercel.

---

## 1. Project Identity

**Name:** PhishGuard — Explainable & Autonomous Phishing Threat Detection Platform
**What the user does here:** Sign in → land on a Dashboard showing recent scans and risk trends → paste a suspicious email/URL or upload a screenshot/QR on a Scan page → watch a live, layer-by-layer analysis → see a scored result broken into "Evidence Cards" that explain exactly why something is risky → optionally connect Gmail so PhishGuard can scan their inbox automatically → view/download auto-generated incident reports for high-risk hits.

This is one website with multiple pages/routes, not two separate sites — the "dashboard" and the "submit a link" surface live in the same app, sharing nav, auth, and design system.

---

## 2. Visual Identity — Color Theme (taken from the reference screenshot, "VIRTUAL OFFICE" dashboard)

Match this palette exactly, not a generic dark theme:

- **Background (base):** near-black, `#0A0A0A` to `#0D0D0D` — not pure `#000`, slightly warm/neutral black.
- **Surface / card background:** a slightly lifted dark charcoal, `#131313`–`#161616`, with a **thin, low-contrast border** (`rgba(255,255,255,0.08)`) rather than shadows — cards read as "outlined panels," not floating boxes.
- **Primary accent (the signature color):** an electric lime/chartreuse green, approx `#C8FF33`–`#D4FF3D`. Use this SPARINGLY and deliberately: primary CTA buttons ("New Scan," "+ New Project"–style), active tab/segment indicators, key numeric highlights (risk score ring, "completed" counters), and small status dots. It should feel like a terminal/CLI accent, not a background wash.
- **Secondary status colors:** keep the standard severity semantics on top of the dark theme — LOW = a muted green (can reuse the lime accent at lower opacity), MEDIUM = amber/yellow (`#F5C244`-ish), HIGH = red (`#E5484D`-ish). These must stay visually distinct from the lime brand accent so "brand green" and "safe/low-risk green" don't get confused — consider using a cooler, more saturated green for LOW-risk states and reserve the lime specifically for UI chrome/branding.
- **Text:** primary text off-white (`#F2F2F2`), secondary/muted text gray (`#8A8A8A`–`#9A9A9A`).
- **Typography:** a monospace or geometric-mono accent font for labels, badges, counters, and metadata (mirrors the "IDLE," "FREE," model-name pill style in the reference) paired with a clean grotesk/sans for body copy and headings. Small-caps or uppercase tracking on section labels and pill badges.
- **Chrome details:** rounded pill badges with subtle borders (status: `IDLE`/`SCANNING`/`HIGH RISK` etc.), soft `border-radius` on cards (8–12px), generous padding, plenty of negative space — the reference image is dense with information but never feels cramped because of consistent spacing and a strict grid.
- **Iconography:** simple, thin-stroke line icons (Lucide-react fits this well) — shield for security, alert-triangle for risk, link for URL, mail for email, QR icon for quishing.

---

## 3. Tech Stack (fixed)

- **Framework:** React (Vite), deployed to Vercel.
- **Styling:** Tailwind CSS with the color tokens above defined as CSS variables/theme extension (`--bg`, `--surface`, `--accent`, `--risk-low`, `--risk-medium`, `--risk-high`, `--text-primary`, `--text-muted`).
- **Auth & data:** Supabase JS client (`@supabase/supabase-js`) for auth (email/password + Google OAuth sign-in) and for reading real-time scan status via Supabase Realtime or the backend WebSocket (see API contract below).
- **Charts:** Recharts, for the risk-score gauge/ring and a trend line of scans-over-time.
- **Animation:** Framer Motion for Evidence Cards sliding/fading in as a scan completes, and for the live-progress indicator.
- **Icons:** lucide-react.
- **Routing:** React Router.

---

## 4. Pages / Routes

### `/` — Public landing
- Hero: product name, one-line pitch ("Detect. Explain. Protect."), primary CTA "Get Started" → auth.
- Short "how it works" 3-step strip (paste/upload → layered analysis → evidence + action) using the icon style above.
- No sensitive data here; this is the only fully public page.

### `/auth` — Sign in / Sign up
- Supabase-backed email/password + "Continue with Google" button.
- Minimal, centered card on the black background, lime-accented primary button.

### `/dashboard` — Authenticated home
- Top stat row: total scans, high-risk count this week, average risk score, connected accounts count — styled like the reference's roster cards (label, big number, muted subtext).
- Recent scans list/table: source icon (email/url/qr), truncated content preview, risk badge (color-coded pill), timestamp, "View" link.
- A small risk-trend line chart (Recharts) for the last 30 days.
- Primary CTA button (lime, top-right) → "+ New Scan," matching the reference's "+ New Project" button placement and style.

### `/scan/new` — Submit content
- Tabs or segmented control: Paste Email · Paste URL · Upload Screenshot · Upload QR.
- Large paste/drop area with the outlined-panel card style.
- On submit: transition into a **live progress view** — four steps (Normalize → Deterministic Rules → Behavioral Analysis → Risk & Explanation) that light up sequentially as the backend WebSocket sends progress events (see contract below). Use the lime accent for the active step, gray for pending, and the severity color for the final step once resolved.

### `/scan/:id` — Result / Evidence Cards
- Header: big risk-score ring (0–100) using the severity color, "HIGH RISK / 87/100" style straight from the reference image's output panel.
- "Why it's suspicious?" — a stacked list of Evidence Cards, each with an icon, short label, and the exact matched text/span highlighted inline (pull `raw_match`, `span_start/end` from the API).
- "Recommended Action" panel — plain-language guidance (Do not click / Verify via official channel / Report).
- If severity is HIGH: a "Generated Reports" section exposing the CERT-style incident report text, DNS sinkhole rule, and Suricata rule in copyable code blocks, plus a "Download" / "Copy" action per artifact.

### `/connections` — App connections
- Cards per provider (Gmail live; Slack/Teams/Browser Extension shown as "Coming soon," disabled state) — connect/disconnect buttons, status pill (`Connected` / `Not connected`), last-synced timestamp.
- Clicking "Connect Gmail" kicks off the OAuth redirect flow the backend exposes.

### `/settings/agent` — Agent training profiles
- List of "agent profiles" (named system prompts) with an editor (textarea) to view/edit the instructions given to the Layer-4 explanation agent, a "set as default" toggle, and a save button. This is the UI for the "train the AI agent for phishing context" requirement — it's editing structured prompt profiles, not fine-tuning a model.

---

## 5. Component States to Design Explicitly

- Empty states: no scans yet, no connections yet (friendly, on-brand illustration/icon + CTA).
- Loading/scanning state (the 4-step live progress view above).
- Error state (scan failed / connection auth failed) — keep the red severity color for this, distinct from HIGH-risk red if possible via icon differentiation.
- Severity badge component: reusable `<RiskBadge score={n} severity="HIGH|MEDIUM|LOW" />` used across Dashboard, Result, and history table.

---

## 6. API Contract to Build Against (backend is being built separately — match this exactly, do not invent different shapes)

```
POST   /api/scans                 body: {source_type, content | file} -> {scan_id}
GET    /api/scans/{scan_id}       -> {scan_id, risk_score, severity, evidence: [...], recommended_action}
GET    /api/scans                 -> paginated {items: [...], total}
WS     /ws/scan/{scan_id}         -> {scan_id, layer, status, ...} progress events
GET    /api/reports/{scan_id}     -> {cert_report, dns_sinkhole, suricata_rule}
POST   /api/connections           -> begins OAuth, returns redirect_url
GET    /api/connections           -> [{id, provider, status, last_synced_at}]
DELETE /api/connections/{id}
GET    /api/agent-profiles        -> [{id, name, system_prompt, is_default}]
POST   /api/agent-profiles
```

Auth: attach the Supabase session JWT as a Bearer token on every request to the backend API.

---

## 7. Deliverables — build in this order

1. Design tokens (Tailwind config extension) + base layout shell (nav, auth-gated routing)
2. Landing + Auth pages
3. Dashboard page with mock data first
4. Scan submission + live progress view (mock the WebSocket events initially)
5. Result/Evidence Card page
6. Connections page
7. Agent profiles settings page
8. Wire everything to the real Supabase client + backend API base URL from an env var

For each step, give full file contents (components + Tailwind config), and call out any shadcn/ui components used so I know what to install.
