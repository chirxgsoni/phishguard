# PhishGuard — Backend Engine

> **Explainable & Autonomous Phishing Threat Detection Platform**  
> Layered deterministic security engine + real-time trainable LLM triage agent.

---

## 1. Core Architecture & Philosophy

PhishGuard is **not** an LLM wrapper. A core principle of the engine is that **the LLM is the last layer** — it synthesizes plain-English explanations and orchestrates response actions; it **never** determines risk scores alone. Every risk score is completely traceable to concrete, rule-based forensic evidence.

```
Incoming Request (Email / URL / QR / Screenshot)
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 0 — Normalization & Ingestion                         │
│ • Async URL unshortening with SSRF & loop limits (httpx)    │
│ • QR code payload extraction (pyzbar / OpenCV)              │
│ • Obfuscated HTML detection (display:none, zero-width font) │
│ • Punycode / IDN homograph translation (idna, tldextract)   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 1 — Deterministic Security Engine (Pure Python/Regex) │
│ • Levenshtein distance brand typosquatting (paypa1.com)     │
│ • High-risk TLD reputation (.xyz, .top, .icu, etc.)         │
│ • Subdomain brand spoofing (wellsfargo.com.update.xyz)      │
│ • Open-redirect & suspicious parameter detection (?next=)   │
│ • Bare IP address hostnames                                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2 — NLP & Behavioral Extraction                       │
│ • Social engineering intent: Urgency, Fear, Authority, Greed│
│ • Exact character token spans (start/end) for UI highlighting│
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3 — Risk Aggregator & Scorer                          │
│ • Deterministic weighted-sum scorer (0–100)                 │
│ • Severity bands: LOW (0–39), MEDIUM (40–69), HIGH (70–100) │
│ • Recommended defensive actions                             │
└───────────────────────┬─────────────────────────────────────┘
                        │ (Strictly-validated JSON Evidence Bundle)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 4 — Generative Explainability & SOAR (Trainable Agent)│
│ • Configurable system prompts via versioned Agent Profiles  │
│ • Plain-English incident explanation with anti-hallucination│
│ • Score ≥ 70: CERT-In/APWG report, DNS sinkhole, Suricata   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Tech Stack

- **Framework:** Python 3.11+, FastAPI (async)
- **Database & Auth:** Supabase (Postgres + Supabase Auth + Row Level Security)
- **Token Cryptography:** `cryptography.fernet` (AES-128-CBC + HMAC-SHA256)
- **Real-Time Streaming:** FastAPI WebSockets (`/ws/scan/{scan_id}`)
- **Detection Libraries:** `tldextract`, `rapidfuzz`, `idna`, `beautifulsoup4`, `httpx`, `pyzbar`, `opencv-python`, `Pillow`
- **LLM Provider:** Google Gemini (`google-generativeai` / `google-genai`), swappable with LiteLLM / OpenAI, and built-in deterministic fallback generator.

---

## 3. Database Setup (Supabase)

1. Open your [Supabase Dashboard](https://supabase.com/dashboard) and navigate to the **SQL Editor**.
2. Run the SQL script located in [`sql/schema.sql`](file:///d:/codes/sql/schema.sql).
3. This creates:
   - `connections`: Encrypted OAuth tokens for external platforms.
   - `agent_profiles`: Trainable, versioned LLM agent system prompts.
   - `scans`: Master records for each scan request.
   - `evidence`: Discrete evidence cards with character spans.
   - `reports`: CERT reports, DNS sinkholes, and Suricata rules.
   - Row Level Security (RLS) policies enforcing multi-tenant isolation.

---

## 4. Local Setup & Running

### 1. Install Dependencies
```bash
python -m pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Generate a Fernet encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
Paste this into `TOKEN_ENCRYPTION_KEY` in `.env`, and add your `SUPABASE_URL`, `SUPABASE_KEY` (service role), and `GEMINI_API_KEY`.

### 3. Run the Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API docs are available at: `http://localhost:8000/docs`.

### 4. Run Test Suite
```bash
python -m pytest tests/ -v
```

---

## 5. API Contract Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service uptime and health status |
| `POST` | `/api/auth/session` | Validate Supabase JWT Bearer token |
| `POST` | `/api/scans` | Submit content/file for scan (`{source_type, content}`) |
| `GET` | `/api/scans/{scan_id}` | Full scan result with evidence cards and score |
| `GET` | `/api/scans` | Paginated scan history |
| `WS` | `/ws/scan/{scan_id}` | Live layer-by-layer progress stream |
| `GET` | `/api/reports/{scan_id}` | SOAR containment artifacts (CERT, DNS, Suricata) |
| `POST` | `/api/connections` | Start OAuth connection (Gmail) |
| `GET` | `/api/connections` | List connected accounts |
| `DELETE` | `/api/connections/{id}` | Revoke connected account |
| `POST` | `/api/connections/{id}/sync` | Pull inbox messages and execute threat scans |
| `GET` | `/api/agent-profiles` | List available agent training prompt profiles |
| `POST` | `/api/agent-profiles` | Create or update an agent prompt profile |

All error responses strictly adhere to the contract:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable explanation"
  }
}
```

---

## 6. Real-Time WebSocket Streaming

Clients connect to `/ws/scan/{scan_id}`. The backend broadcasts progressive state updates as each layer executes:

```json
{"scan_id": "...", "layer": 0, "status": "running", "message": "Normalizing content, unshortening URLs, and decoding payloads"}
{"scan_id": "...", "layer": 1, "status": "complete", "evidence_count": 2}
{"scan_id": "...", "layer": 2, "status": "complete", "evidence_count": 3}
{"scan_id": "...", "layer": 3, "status": "complete", "risk_score": 85, "severity": "HIGH"}
{"scan_id": "...", "layer": 4, "status": "streaming", "partial_explanation": "PhishGuard analyzed this message..."}
{"scan_id": "...", "status": "complete", "risk_score": 85, "severity": "HIGH", "recommended_action": "CRITICAL THREAT..."}
```

---

## 7. Architectural Decisions & Tradeoffs

### Background Processing: FastAPI `BackgroundTasks` vs. `Celery + Redis`
- **Hackathon & Fast MVP (Current Implementation):**  
  Uses FastAPI `BackgroundTasks` executing within the ASGI event loop.  
  *Pros:* Zero extra infrastructure dependencies; runs out-of-the-box locally and on lightweight cloud containers.  
  *Cons:* Tied to the web server lifecycle; tasks are not persistent across server restarts.
- **Enterprise Scale Transition:**  
  `app/pipeline/orchestrator.py` is decoupled so that replacing `background_tasks.add_task(...)` with `celery_app.send_task(...)` requires zero changes to the detection pipeline. Celery + Redis provides persistent queueing, worker horizontal scaling, and automatic retries.

### Deployment Target: Render / Railway / Fly.io vs. Vercel
⚠️ **Do NOT deploy this backend service to Vercel Serverless Functions.**
- **Why Vercel Serverless fails for this backend:**
  1. Vercel's serverless execution environment enforces strict maximum request timeouts (10–15 seconds on free tiers).
  2. Serverless execution environments terminate immediately after the HTTP response is dispatched, terminating background tasks prematurely.
  3. Persistent WebSockets (`/ws/scan/{scan_id}`) are unsupported on Vercel Python serverless runtimes.
- **Recommended Targets:**
  - **Render** (Web Service, Python 3.11+, Docker or Native): Supports long-running WebSockets and background tasks.
  - **Railway** or **Fly.io**: First-class persistent process and WebSocket support.
  - The React frontend should deploy separately to **Vercel** and connect over HTTPS/WSS.

---

## 8. Deploying to Render / Railway

### Deploying to Render
1. Create a **New Web Service** linked to your repository.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. In Environment Variables, populate all keys from `.env.example`.

### Deploying to Railway
1. Click **New Project** -> **Deploy from GitHub repo**.
2. Railway detects Python automatically.
3. Set the start command to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add environment variables under the **Variables** tab.
