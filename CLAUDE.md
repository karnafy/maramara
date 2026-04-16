# CLAUDE.md — MARAMARA

This file is the project-level guide for AI assistants (Claude Code, Cursor, etc.)
working in this repository. Keep it current when the architecture changes.

---

## Project

**MARAMARA — Therapeutic Speech Intelligence Platform**

Not just voice tracking. A clinical-grade behavioral intelligence system that turns
everyday speech into measurable emotional, cognitive, and therapeutic insights.

**Three users:**
- **User** — wants self-awareness + emotional-language tracking.
- **Therapist / Coach** — views linked patients, tracks progress, adds notes, exports reports.
- **Admin** — system governance, moderation, risk-flag triage.

**Core promise:**
> "I don't just record what you said. I show you how you speak to the world,
> what activates you, and what actually calms you down."

Languages: **Hebrew + English** (RTL/LTR aware).

---

## Architecture

```
┌─────────────────┐   ┌────────────────────────────────────┐
│ Expo Mobile     │   │ Flask API (api/)                   │
│ (RN + TS)       │──▶│ ├── routes/     (8 blueprints)     │
│ 5 tabs          │   │ ├── services/   (VAD, speaker,     │
│ VAD on-device   │   │ │               whisper, analysis) │
└─────────────────┘   │ ├── services/crew/ (CrewAI 10 agt) │
                      │ ├── workers/    (RQ jobs)          │
┌─────────────────┐   │ └── templates/  (HTML+CSS therap.) │
│ Therapist Web   │──▶│                                    │
│ (server-rendered│   │ + Gunicorn in prod, Waitress dev   │
│ HTML + Jinja2)  │   └────────────────────────────────────┘
└─────────────────┘                 │
                                    ▼
                          ┌──────────────────────┐
                          │ Supabase (Postgres)  │
                          │ + Auth + pgvector    │
                          │ + Row Level Security │
                          └──────────────────────┘
                                    │
                          ┌──────────────────────┐
                          │ Redis (RQ queue)     │
                          └──────────────────────┘
```

### Monorepo (single git repo, no workspaces)

```
maramara/
├── api/                    # Flask backend + Jinja2 HTML therapist dashboard
│   ├── app.py              # Flask factory
│   ├── config.py           # pydantic-settings
│   ├── cli.py              # maramara management CLI
│   ├── worker_main.py      # RQ worker entry point
│   ├── routes/             # 8 blueprints: auth, voice, audio, dashboard,
│   │                       #   insights, therapist, reports, admin
│   ├── services/           # vad, speaker, transcription, analysis,
│   │                       #   queue, pdf_report, crew/
│   ├── services/crew/      # CrewAI: 10 therapeutic agents + insight_crew
│   ├── workers/            # RQ jobs: process_segment, aggregate_daily,
│   │                       #   weekly_insights
│   ├── db/supabase_client.py
│   ├── templates/          # Jinja2 (landing, auth, user, therapist, admin)
│   ├── static/css/         # tokens.css + base.css + components.css
│   ├── migrations/sql/     # 001-006 Supabase migrations
│   └── Dockerfile          # + Dockerfile.worker
├── mobile/                 # Expo RN app (5 tabs + auth + onboarding)
├── tools/                  # Cloned reference repos (gitignored)
├── infra/
│   ├── docker/             # docker-compose.yml (local dev)
│   └── railway/            # railway.dev/prod/worker.json
├── docs/                   # SETUP-SNAPSHOT.md + architecture docs
├── .env.example
├── .gitignore
└── CLAUDE.md               # this file
```

---

## Tech Stack (final)

| Layer | Choice |
|-------|--------|
| Backend | **Flask 3** + Python 3.11 (conda env: **KARNAF**) |
| Validation | **Pydantic v2** + pydantic-settings |
| Auth | **Supabase Auth** (JWT) via PyJWT |
| Queue | **RQ** + Redis |
| Database | **Supabase Postgres 17** + **pgvector** + **RLS** |
| LLM (per-segment) | **Anthropic Claude Sonnet 4.6** |
| LLM (weekly crew) | **CrewAI** orchestrating 10 agents (Claude) |
| VAD | **Silero VAD** |
| Speaker Verify | **SpeechBrain ECAPA-TDNN** (192-dim embeddings) |
| Transcription | **faster-whisper large-v3** |
| Therapist UI | **Flask + Jinja2 HTML + CSS** (server-rendered, no JS framework) |
| Mobile | **React Native + Expo SDK 54** + TypeScript + Zustand + Victory Native + TanStack Query + i18next |
| Container | **Docker** (api + worker images) |
| Deploy | **Railway** (dev + prod environments) |
| Design language | **Liquid Glass** (frosted glass + ambient gradients) |

---

## Design System

**"Liquid Glass" + Stitch "The Empathetic Observer"**

- Frosted glass panels (`.glass-panel`, `backdrop-filter: blur(20px)`)
- Ambient gradient orbs in background (purple → teal → pink)
- Tonal layering, **NO 1px borders** for sectioning
- Tri-font: **Plus Jakarta Sans** (body), **Manrope** (display), **Inter** (labels)
- Brand: Midnight teal (`#104356`) + liquid purple (`#6b5ce7`) + teal accent (`#6dd5ed`)
- Pill-shaped buttons, large radii, soft shadows
- Breathing animations for recording indicators

Tokens live in `api/static/css/tokens.css`.
See `docs/VISUAL-REFERENCES.md` for inspiration images and Stitch project link.

---

## Data Model (Supabase)

13 tables + pgvector. See `api/migrations/sql/`.

| Table | Purpose |
|-------|---------|
| `profiles` | User identity + role (user/therapist/admin) |
| `therapist_patient_links` | Therapist ↔ patient relationships |
| `voice_profiles` | pgvector(192) voice embeddings |
| `recording_preferences` | Schedule + sensitivity |
| `audio_segments` | Every 10s chunk metadata |
| `transcripts` | Whisper output |
| `segment_analysis` | Per-segment NLP (10 layers) |
| `detected_terms` | Phrase mining |
| `daily_metrics` | Aggregated daily stats |
| `weekly_metrics` | CrewAI weekly insights |
| `therapist_notes` | Clinical notes |
| `risk_flags` | Crisis-flag queue |
| `therapist_access_log` | GDPR-style audit log |

**RLS enforced on all tables.** Policies:
- `user` sees only own data
- `therapist` sees linked patients (only if `status='active'`)
- `admin` sees all

---

## Audio Pipeline

```
Mobile (Expo)            API (Flask)                    Worker (RQ)
─────────────            ───────────                    ───────────
VAD + chunk (10s) ──────▶ POST /api/audio/chunk
                          ↓ (fast path, req thread)
                          VAD (Silero)
                          ↓
                          Speaker Verify (cosine vs enrolled, threshold 0.75)
                          ↓
                          INSERT audio_segments
                          ↓
                          enqueue ──────────────────────▶ process_segment
                                                          ↓
                                                          faster-whisper transcribe
                                                          ↓
                                                          Claude analysis (10 layers)
                                                          ↓
                                                          INSERT transcripts + segment_analysis + detected_terms
                                                          ↓
                                                          enqueue aggregate_daily
```

Weekly CrewAI job (`weekly_insights`) runs on a schedule — 10 agents produce the
clinical summary + user reflection, stored in `weekly_metrics.crewai_insights`.

---

## Environment Variables

See `.env.example` for the full list. Must-haves:

- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `DATABASE_URL` (for direct Postgres ops)
- `REDIS_URL`
- `ANTHROPIC_API_KEY` (for CrewAI + per-segment analysis)
- `SECRET_KEY` (Flask sessions)

**Dev Supabase project ref:** `tfygluotkrfjougyrvbw` (see `docs/SETUP-SNAPSHOT.md`).

---

## Running locally

```bash
# 1. Install deps
conda activate KARNAF
pip install -r api/requirements.txt

# 2. Redis
docker run -d -p 6379:6379 --name maramara-redis redis:7-alpine

# 3. Apply migrations
cd api && python cli.py migrate apply

# 4. Run API + worker (in separate terminals)
flask --app app run --debug --port 5000
python worker_main.py

# OR - single-command via docker-compose
docker compose -f infra/docker/docker-compose.yml up
```

Mobile:
```bash
cd mobile
npm install
npm start
```

---

## Management CLI

Available via `python api/cli.py <command>`:

- `user list` / `user set-role <email> <role>` / `user create-admin <email>`
- `report weekly <email>`
- `queue stats` / `queue run-weekly <email>`
- `migrate apply`
- `doctor` — runs health checks

---

## Conventions

### Python
- Black + Ruff; target py311.
- Pydantic models for all request/response shapes.
- Structured logging via `structlog` (`utils/logger.py`).
- All DB access via `db/supabase_client.py`.
- Never bypass RLS in user-context code; `get_admin_client()` only in workers + admin routes.

### TypeScript (mobile)
- Strict mode. Path alias `@/*`.
- Data fetching via TanStack Query.
- Auth state via `hooks/useAuth.tsx`.
- i18n strings only — never hardcode user-facing text.

### CSS
- Tokens in `tokens.css` — components must never hardcode colors or radii.
- Use `.glass-panel` utility for consistent glass surfaces.
- Respect `prefers-reduced-motion` (already handled in `components.css`).

### UX copy rules (clinical safety)
- Never shame or judge. Replace "toxic", "bad" with measured descriptions.
- Use reflective phrasing: "You tended to speak more harshly between 16:00–18:00."
- See section 11 of the product spec (`docs/product-spec.md`).

---

## Privacy & compliance

- Raw audio **not** retained by default (`RETAIN_RAW_AUDIO=false`).
- Explicit consent during onboarding (`terms_accepted_at`, `privacy_accepted_at`).
- Audit log for therapist access (`therapist_access_log`).
- Delete-account flow via admin CLI + soft-delete + hard-delete job.
- Target: **GDPR-style (Israel/EU)**. HIPAA not a target at MVP.

---

## When editing

- If you add a table → add an RLS policy in `006_rls_policies.sql`.
- If you add a CrewAI agent → register it in `services/crew/agents.py` and add its task.
- If you add a route → register the blueprint in `app.py` `_register_blueprints()`.
- Keep this file in sync.

---

## Related tools cloned under `tools/` (reference only; gitignored)

- `ui-ux-pro-max-skill` — design intelligence
- `superpowers` — Claude Code skill collection
- `everything-claude-code` — conventions
- `google-workspace-cli` — Google Workspace integration

Use them as **references**, not as imported code.
