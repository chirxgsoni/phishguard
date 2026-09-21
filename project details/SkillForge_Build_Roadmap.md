# SkillForge — Structural Build Roadmap & Agent Prompt

A practical, real-data-first build order for turning the PDF concept into a working website — no seeded/fake data, no scripted AI responses, real Postgres database from day one.

---

## 0. Build Order Philosophy — what to build first

Most people building this kind of app make the mistake of building the frontend first with fake JSON, then "connecting it to a real backend later." That always turns into a rebuild. Since you specifically want **real data, no preloading**, build in this order instead:

1. **Database schema first** — the tables are the contract for everything else.
2. **Backend + real auth** — a live signup/login flow, hitting the real database, before any UI polish.
3. **Thinnest possible frontend shell** — just enough UI to prove signup → login → dashboard works against the real backend.
4. **One vertical feature at a time**, fully real end-to-end (DB write → API → UI), starting with the Code Lab, before touching the next feature.
5. **AI mentor last of the "core loop"** — it should call a real LLM API live, never a canned string.
6. Security hardening and deployment happen continuously, not just in "week 11."

This order means at every single step you have a real, clickable, real-data website — never a mocked shell.

---

## 1. Tech stack (production-real, minimal placeholders)

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js + React + Tailwind | Fast to build, good with an AI coding agent |
| Code editor | Monaco Editor | Same engine as VS Code, drop-in browser component |
| Backend | FastAPI (Python) | Clean, and Python makes the code-runner/judge and AI integration simpler than Node |
| Database | PostgreSQL, hosted on **Supabase** or **Neon** (free tier, real hosted DB immediately — no local-only mock DB) | You get a real database with a real connection string on day one |
| ORM | SQLAlchemy + Alembic (migrations) | Keeps schema changes real and versioned, not hand-edited |
| Auth | Supabase Auth or Clerk | Real signup/login/session tokens, not a hardcoded "test user" |
| Code execution | Judge0 (self-hosted or their API) or a Docker sandbox you write yourself | Actually runs and grades code — not a hardcoded "pass" |
| AI mentor | Real API call to an LLM (Gemini/OpenAI/Claude — your key) | Every hint/explanation is generated live from the student's actual code, never a template |
| Deployment | Vercel (frontend) + Railway/Render (backend + DB) | Fast real deployment, matches the PDF's "Week 12 demo" goal |

---

## 2. Phase-by-phase decomposition

### Phase 1 — Foundation (real DB + real auth, no UI polish yet)
- Create the Postgres database (Supabase/Neon) — this is your **first real artifact**, not a placeholder.
- Write the schema (see §3 below) and run your first migration.
- Backend skeleton: one `/health` endpoint that queries the real DB and returns a row count.
- Real signup/login endpoints — test by actually creating your own account with your real email.
- Frontend shell: login page, signup page, empty dashboard — wired to the real backend, not local state.

**Done when:** you can sign up with a real email, log out, log back in, and see a dashboard that queries the real `users` table.

### Phase 2 — Core learning loop: Code Lab
- Admin can create a real challenge (you type one in yourself — e.g. "reverse a string" — no seed script of 50 fake challenges).
- Monaco editor page pulls that challenge from the real `challenges` table.
- Submission endpoint sends code to the real code-execution sandbox (Judge0/Docker), gets a real pass/fail against `test_cases`, and writes a real row to `submissions`.

**Done when:** you submit actual broken code and it actually fails; you fix it and it actually passes.

### Phase 3 — AI Mentor (live, not scripted)
- Real API call to an LLM, sending the student's actual current code + the actual failing test output.
- Store every mentor interaction as a row in an `evidence_events`-style table.
- Guardrail from the PDF: the AI explains, it never overrides the test result as the source of truth.

**Done when:** two different broken submissions get two genuinely different hints, generated live.

### Phase 4 — Debug Lab + Project Lab
- Debug Lab: real "broken mini-app" repositories you actually write and break on purpose.
- Project Lab: one full end-to-end project brief with real acceptance criteria, graded the same way as Code Lab.

### Phase 5 — Industry Simulation (the signature feature)
- Implement the ticket template from the PDF (§5) as a real data model: `simulations → simulation_tasks → evidence_events`.
- L1–L5 levels are just increasing task complexity — build L1 (single broken function) fully working before adding L2+.

### Phase 6 — Skill Graph & Scoring
- Calculate scores **from the real `evidence_events` table**, not a static number — this is the part most builders fake. It has to be a real query/aggregation.
- Treat the weights in the PDF (§7) as a first draft; expose them as a config table you can tune.

### Phase 7 — Company Dashboard
- Real candidate search against real `student_profiles` + `student_skill_scores`.
- No fake company logins — build real company signup as its own account type.

### Phase 8 — Security hardening (ongoing, then a final pass)
- Sandbox isolation (CPU/memory/time limits, no network from student code, no filesystem/secret access).
- Rate-limit submissions and AI calls.
- Deterministic tests, separated from AI feedback (per PDF guardrail).

### Phase 9 — Deploy + Demo polish
- Deploy frontend + backend + DB to real hosting.
- Rehearse the demo storyline from the PDF (§14): problem → diagnostic → debug ticket → fix → readiness profile → company view.

---

## 3. Database schema (concrete, from the PDF's data model)

```
users (id, email, password_hash, role[student|company|admin], created_at)
student_profiles (id, user_id FK, name, readiness_score, updated_at)
company_profiles (id, user_id FK, company_name)

skills (id, name, category)
student_skill_scores (id, student_id FK, skill_id FK, score, evidence_count)

challenges (id, title, description, difficulty, category, created_by)
test_cases (id, challenge_id FK, input, expected_output, is_hidden)
submissions (id, student_id FK, challenge_id FK, code, passed, runtime_ms, created_at)

projects (id, title, brief, acceptance_criteria)
project_tasks (id, project_id FK, title, description)
project_submissions (id, project_id FK, student_id FK, repo_or_code, status)

simulations (id, title, level[L1-L5], context, acceptance_criteria)
simulation_tasks (id, simulation_id FK, title, status)
evidence_events (id, student_id FK, source_type, source_id, event_type, payload_json, created_at)

assessments (id, title)
assessment_questions (id, assessment_id FK, question, type)
assessment_attempts (id, assessment_id FK, student_id FK, answers_json, score)
```

`evidence_events` is the important one — every hint used, every test run, every commit, every mentor interaction gets logged here in real time, and the skill graph in Phase 6 is just a query over this table.

---

## 4. Your literal Day 1 checklist

| Day | Do this | Done when |
|---|---|---|
| 1 | Create Supabase/Neon project, run schema migration | Real tables exist, visible in DB dashboard |
| 2 | Backend `/health` + `/signup` + `/login` (real JWT/session) | You can create a real account via curl or Postman |
| 3 | Next.js shell: login/signup pages calling the real API | You log in through the browser, not just the API |
| 4 | Create ONE real challenge by hand via an admin endpoint | The row exists in `challenges`, visible in DB |
| 5 | Monaco editor page loads that one real challenge | You see your actual challenge text in the editor |
| 6 | Wire submission → Judge0/Docker → real test result | Submitting broken code fails; fixed code passes |
| 7 | First real AI mentor hint on your own failing submission | The hint text references your actual code/error |

---

## 5. Prompt for your Antigravity / Gemini agent

Since you want an AI coding agent to actually build this, here's the prompt structured with the **ART framework** (Act as → Request → Terms), which gets more reliable, less-hallucinated output from coding agents than a plain instruction dump.

**A (Act as):** A senior full-stack engineer who specializes in building real, production-shaped MVPs — someone who refuses to fake data or stub out functionality, and always wires every feature to a real database and real API from the first commit.

**R (Request):** Build the SkillForge platform (a practical employability platform for developers) as a real, working website — starting from the database schema and working outward, one vertical feature at a time, never building a UI against mock/local data.

**T (Terms):**
- Tech stack: Next.js + Tailwind frontend, FastAPI backend, PostgreSQL (Supabase/Neon), real auth (Supabase Auth/Clerk), Monaco Editor, real code execution via Judge0 or a Docker sandbox, real LLM API calls for the AI mentor.
- **No seed scripts, no fake/mock/placeholder data, no hardcoded "example" users, challenges, or scores.** Every table gets populated only through real signup flows or real admin input I type in myself.
- Build in this exact order and stop for my confirmation after each phase before moving to the next: (1) DB schema + migrations, (2) backend health check + real auth, (3) minimal frontend shell wired to real auth, (4) Code Lab vertical slice with a real sandboxed code runner, (5) AI mentor making live LLM calls, (6) Debug Lab + Project Lab, (7) Industry Simulation data model + one working L1 ticket, (8) Skill graph computed from real `evidence_events`, (9) Company dashboard, (10) security hardening, (11) deployment.
- At the end of every phase, tell me exactly how to manually verify it's real (e.g., "check this row exists in this table," "try logging in with a real email").
- Never mark a phase complete by writing placeholder UI with static numbers — every number on screen must come from a live database query.
- Output format: working code files organized by phase, plus a short verification checklist after each phase.

**Ready-to-paste prompt block:**

```
Act as a senior full-stack engineer who specializes in building real, 
production-shaped MVPs. You never fake data or stub out functionality — 
every feature is wired to a real database and real API from the first commit.

Build "SkillForge," a practical employability platform for developers, as a 
real working website. Stack: Next.js + Tailwind (frontend), FastAPI (backend), 
PostgreSQL via Supabase/Neon (database), Supabase Auth or Clerk (real auth), 
Monaco Editor (code editor), Judge0 or a Docker sandbox (real code execution), 
and a real LLM API call (not a canned response) for the AI mentor.

Hard rules:
- No seed scripts, no mock/placeholder/dummy data, no hardcoded example users, 
  challenges, or scores. Every table is populated only via real signup flows 
  or real input I provide.
- Every number or piece of content shown in the UI must come from a live 
  database query — never a static/hardcoded value standing in for real data.
- The AI mentor must call a real LLM API with the student's actual current 
  code and actual test failure — never return a templated string.
- Automated tests are the source of truth for pass/fail; the AI mentor only 
  explains, never overrides a result.

Build order — complete one phase fully, show me how to manually verify it's 
real, and wait for my go-ahead before starting the next:
1. Database schema + migrations (users, student_profiles, company_profiles, 
   skills, student_skill_scores, challenges, test_cases, submissions, 
   projects, project_tasks, project_submissions, simulations, 
   simulation_tasks, evidence_events, assessments, assessment_questions, 
   assessment_attempts)
2. Backend health check + real signup/login/auth
3. Minimal frontend shell (login, signup, empty dashboard) wired to the real backend
4. Code Lab: one real challenge, Monaco editor, real sandboxed code execution, 
   real pass/fail written to `submissions`
5. AI mentor: live LLM call using the student's real code + real test output
6. Debug Lab + Project Lab
7. Industry Simulation data model + one working Level 1 (single broken 
   function) ticket end-to-end
8. Skill graph: scores computed live from `evidence_events`, not stored constants
9. Company dashboard: real candidate search over real student data
10. Security hardening: sandbox isolation, rate limiting, deterministic tests
11. Deployment (Vercel + Railway/Render)

For each phase, give me the code, then a short checklist of how to verify 
with my own eyes that the data involved is real and live — not placeholder.
```

---

### Adjusting this prompt
If you'd rather have the agent build everything in one shot instead of pausing after each phase, or want it to pick NestJS over FastAPI, or scaffold the frontend before the DB, let me know and I'll rewrite the A/R/T accordingly.
