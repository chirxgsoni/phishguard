# PhishGuard — Backend Build Prompt (for Gemini / Antigravity)

## ART Breakdown
- **Act as:** Senior backend & security engineer, expert in FastAPI, Python, LLM agent orchestration, and Supabase.
- **Request:** Build the complete PhishGuard backend — a layered, explainable phishing-detection engine with a real-time, trainable LLM triage agent — exposed as a REST + WebSocket API for a separate React frontend (built independently by another AI).
- **Terms:** Follow the exact architecture, schemas, and constraints below. Do not invent UI. Do not skip the deterministic layers in favor of "just ask the LLM." Output working code, file by file, with explanations.

---

## 1. Project Identity

**Name:** PhishGuard — Explainable & Autonomous Phishing Threat Detection Platform
**Pitch:** Users paste a suspicious email, URL, or upload a screenshot/QR code. PhishGuard runs it through deterministic security rules first, then a trainable LLM agent synthesizes a plain-English explanation and a risk score, and — above a threshold — auto-generates incident reports and network-containment artifacts. It is a public, multi-tenant SaaS-style app with account connections (Gmail, later Slack/Teams), not a single-user script.

**Core design principle (do not violate this):** Judges/users must never see "we sent your text to an LLM and it said unsafe." The LLM is the *last* layer — it explains and orchestrates, it does not decide alone. Every risk score must be traceable to concrete, rule-based evidence.

---

## 2. Tech Stack (fixed — do not substitute without flagging it to me)

- **Language/Framework:** Python 3.11+, FastAPI (async)
- **Auth & DB:** Supabase (Postgres + Supabase Auth + Row Level Security). Backend uses the Supabase Python client (`supabase-py`) with the service role key server-side only; never expose it to the frontend.
- **Real-time:** FastAPI WebSocket endpoint (or Supabase Realtime channels) so the frontend can show live "Layer 1 → Layer 2 → Layer 3 → Layer 4" progress as a scan runs, instead of a single blocking response.
- **LLM orchestration:** LangChain or LiteLLM (either is fine) so the model provider is swappable. The LLM only ever receives strictly-validated JSON evidence, never raw untrusted text directly — sanitize/summarize first.
- **Detection libraries:** `tldextract`, `python-Levenshtein` (typosquatting), `pyzbar` + `opencv-python` (QR/quishing), `beautifulsoup4` (HTML parsing), `httpx` (async URL unshortening/fetching), `idna` (Punycode/IDN homograph detection).
- **Background jobs:** Celery + Redis, or FastAPI `BackgroundTasks` for the hackathon-scale version — note the tradeoff to me.
- **Deployment target:** ⚠️ Do NOT assume Vercel for this service. FastAPI + Python background tasks + WebSockets do not fit Vercel's serverless Python runtime well (execution time limits, no persistent WebSocket support). Recommend **Render, Railway, or Fly.io** for the API, and explain this tradeoff back to the user if asked. The React frontend deploys to Vercel separately and calls this API over HTTPS/WSS.
- **Secrets:** All API keys (LLM provider, Google OAuth, threat-intel feeds) via environment variables, never hardcoded.

---

## 3. The Detection Pipeline (must be implemented as five distinct, inspectable layers)

Implement each layer as its own module/function so results can be logged and shown individually in the UI. Do NOT collapse these into one LLM call.

### Layer 0 — Normalization & Ingestion
- Accept: raw email text, raw pasted URL, uploaded screenshot (OCR), uploaded QR image.
- Unshorten URLs (follow redirects with `httpx`, cap redirect depth to prevent SSRF/redirect-loop abuse).
- Decode QR payloads via `pyzbar`/`opencv-python`.
- Strip HTML, extract visible text vs. hidden/obfuscated text.
- Extract and isolate the TLD/domain; convert IDN/homograph characters to Punycode (`idna` module) and flag if punycode differs visually from the displayed domain.

### Layer 1 — Deterministic Engine (pure Python/regex, no ML)
- Levenshtein distance against a small seed list of major brand domains (bank names, common services) to catch typosquatting (`paypa1.com`, `micros0ft.com`).
- High-risk TLD list (`.xyz`, `.top`, `.info`, `.biz`, etc.) — flag, don't auto-block.
- Subdomain-spoofing detection: brand name appears before the *real* registrable domain (e.g. `wellsfargo.com.update.xyz` → real domain is `update.xyz`).
- Open-redirect / suspicious query-string detection (`?redirect=`, `?next=`).
- Output: a list of discrete "Evidence" objects, each with `type`, `severity`, `human_label`, `raw_match`.

### Layer 2 — NLP & Behavioral Extraction
- Lightweight zero-shot classification or regex/keyword rules to detect social-engineering intent: urgency, fear, authority impersonation, greed/reward bait.
- Extract and return the *exact token spans* (start/end offsets in the original text) so the frontend can highlight them — this is required for the "Evidence Card" UI.

### Layer 3 — Risk Aggregator & Scorer
- Deterministic weighted-sum scorer over all Layer 1 + Layer 2 evidence → composite score 0–100.
- Severity bands: LOW 0–39, MEDIUM 40–69, HIGH 70–100.
- This function must be pure/deterministic and unit-testable — no LLM involvement here. This is your answer to "how do you avoid being an LLM wrapper."

### Layer 4 — Generative Explainability & SOAR (the trainable LLM agent)
- Receives ONLY the strictly-validated JSON evidence bundle from Layers 1–3 (never raw attacker-controlled text verbatim, to avoid prompt injection from the phishing content itself).
- System prompt for this agent should be swappable/configurable per "training context" — expose a `system_prompt_version` or `agent_profile` field in the DB so the user can iterate on how the agent is instructed (this is the "train the agent for phishing context" requirement).
- Generates: (a) a plain-English explanation of why the message is risky, (b) if score ≥ 70: an incident report formatted for CERT-In/APWG/CISA-style submission, and (c) network containment artifacts: a DNS-sinkhole line (`0.0.0.0 <domain>`) and a Suricata/Snort rule skeleton.
- **Guardrail:** the agent must never fabricate evidence not present in the JSON bundle it was given. Validate its output against the evidence list before returning it to the client.

---

## 4. Real-Time Agent Behavior

- Implement a WebSocket endpoint `/ws/scan/{scan_id}` that streams layer-by-layer progress events as the pipeline runs, e.g.:
  ```json
  {"scan_id": "...", "layer": 1, "status": "complete", "evidence_count": 3}
  {"scan_id": "...", "layer": 4, "status": "streaming", "partial_explanation": "..."}
  {"scan_id": "...", "status": "complete", "risk_score": 87, "severity": "HIGH"}
  ```
- This lets the frontend show a live "scanning..." experience rather than a spinner + dead air — important for the demo.

---

## 5. Data Model (Supabase/Postgres — propose exact `CREATE TABLE` statements)

At minimum:
- `users` (managed by Supabase Auth)
- `connections` — id, user_id, provider (`gmail`, `slack`, etc.), oauth_tokens (encrypted), status, created_at
- `scans` — id, user_id, source_type (`email`|`url`|`qr`|`screenshot`), raw_input_ref, risk_score, severity, created_at
- `evidence` — id, scan_id, layer, type, severity, human_label, raw_match, span_start, span_end
- `reports` — id, scan_id, report_type (`cert`|`dns_sinkhole`|`suricata`), content, submitted (bool)
- `agent_profiles` — id, user_id (nullable = global default), name, system_prompt, created_at — this is what "training the agent" means in practice: versioned system prompts the user can edit and A/B test.

Apply Supabase Row Level Security so users only ever see their own `connections`, `scans`, `evidence`, `reports`.

---

## 6. Gmail / App Connections

- Implement Google OAuth (read-only Gmail scope, e.g. `gmail.readonly`) via a standard OAuth2 authorization-code flow. Store refresh tokens encrypted in Supabase.
- Provide an endpoint to pull recent inbox messages and run them through the same pipeline as manually pasted content — same evidence/scoring code path, just a different ingestion source. Do not duplicate pipeline logic for connected-account scanning.
- Architect the connection layer so a new provider (Slack, Teams, WhatsApp Business API) can be added by implementing one `Connector` interface (fetch messages → normalize → hand to Layer 0), not by rewriting the pipeline.

---

## 7. Required REST Endpoints (exact contract — the frontend will be built against this)

```
POST   /api/auth/session          -> validate Supabase JWT, return user profile
POST   /api/scans                 -> body: {source_type, content | file}, returns {scan_id}
GET    /api/scans/{scan_id}       -> full result incl. evidence[], risk_score, severity
GET    /api/scans                 -> paginated list of user's past scans
WS     /ws/scan/{scan_id}         -> live progress stream, see §4
GET    /api/reports/{scan_id}     -> SOAR artifacts (CERT report text, DNS rule, Suricata rule)
POST   /api/connections           -> start OAuth flow for a provider
GET    /api/connections           -> list user's connected accounts + status
DELETE /api/connections/{id}      -> revoke a connection
GET    /api/agent-profiles        -> list available agent "training" profiles
POST   /api/agent-profiles        -> create/edit a system-prompt profile
GET    /api/health                -> uptime/liveness check
```

For every endpoint, return errors as `{"error": {"code": "...", "message": "..."}}` with proper HTTP status codes.

---

## 8. Non-Goals / Guardrails (explicit — respect these)

- Do NOT let this become "paste text → single LLM call → trust the output." Every score must trace back to deterministic evidence.
- Do NOT execute or "click" any submitted URL beyond following redirects for unshortening — no rendering attacker HTML, no running attacker JS.
- Do NOT store plaintext OAuth tokens.
- Treat all pasted/ingested content (email bodies, page titles, QR payloads) as untrusted input to the LLM step — never let it override the system prompt (prompt-injection defense).
- This is a defensive security tool: it detects and reports phishing, it never generates or sends phishing content.

---

## 9. Deliverables — build in this order

1. FastAPI project skeleton + Supabase client wiring + health check
2. Layer 0–3 deterministic pipeline as pure, unit-tested Python functions
3. `/api/scans` POST + GET wired to the pipeline (LLM layer stubbed with a mock response first)
4. Layer 4 LLM integration + agent_profiles table/endpoints
5. WebSocket live-progress endpoint
6. Gmail OAuth connector
7. SOAR report generation endpoints
8. requirements.txt, `.env.example`, README with local run + deploy instructions (Render/Railway)

For each step, give me the full file contents, not diffs, and tell me exactly which env vars and Supabase tables it depends on.
