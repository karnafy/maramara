# MARAMARA V2 — Full Installation Prompt (copy-paste ready)

> Paste this entire document into Claude Code / Cursor / any AI agent
> to reproduce the full MARAMARA V2 setup in a new environment.

---

## Goal

Build a single-git-repo monorepo: **MARAMARA — Therapeutic Speech
Intelligence Platform** with a mobile app + therapist dashboard +
Flask API + ML pipeline (transcription, NLP analysis, CrewAI
weekly insights) and Liquid Glass UI.

---

## Stack (final)

- **Backend:** Flask 3 + Python 3.11 (conda env: `KARNAF`)
- **Validation:** Pydantic v2 + PyJWT
- **Queue:** RQ + Redis
- **Database:** Supabase Postgres 17 + pgvector + Row Level Security
- **Transcription:** OpenAI Whisper API (cloud, no local torch)
- **Per-segment Analysis:** Claude Sonnet 4.6 via `anthropic` SDK
- **Weekly Insights:** CrewAI (10 therapeutic agents)
- **VAD:** RMS + zero-crossing (lightweight, no torch)
- **Speaker Verification:** deterministic stub for MVP (real ECAPA-TDNN later)
- **Mobile:** React Native + Expo SDK 54 + TypeScript + Zustand +
  TanStack Query + i18next (HE/EN)
- **Therapist Web:** Flask + Jinja2 + HTML/CSS (server-rendered)
- **Design Language:** Liquid Glass UI (frosted glass + ambient
  gradient orbs) + Stitch "The Empathetic Observer" tokens
- **Fonts:** Plus Jakarta Sans + Manrope + Inter
- **Brand Palette:** `#104356` teal / `#6b5ce7` purple /
  `#6dd5ed` teal accent
- **Container:** Docker (api + worker images)
- **Deploy:** Railway (dev + prod environments)
- **Repo:** single git repo (no workspaces, no monorepo tooling)
- **Languages:** Hebrew + English (RTL/LTR aware)

---

## Required Credentials

| Service | Token Format | Where to get |
|---------|--------------|--------------|
| Supabase | `sbp_...` (Access Token) | supabase.com/dashboard/account/tokens |
| Railway | UUID (Team Token) | railway.com/account/tokens |
| GitHub | `github_pat_...` (Fine-grained PAT) | github.com/settings/personal-access-tokens |
| OpenAI | `sk-proj-...` | platform.openai.com/api-keys |
| Anthropic | `sk-ant-api03-...` | console.anthropic.com/settings/keys |

GitHub PAT settings required: **All repositories** + **Contents: Read and write**.

Requires: Anthropic credits ≥ $5 + Railway **Hobby plan** ($5/month).

---

## Project Structure

```
maramara/
├── api/                     # Flask backend + Jinja2 therapist UI
│   ├── app.py               # Flask factory
│   ├── config.py            # pydantic-settings
│   ├── cli.py               # management CLI
│   ├── worker_main.py       # RQ entry point
│   ├── routes/              # 8 blueprints (auth, voice, audio,
│   │                        #  dashboard, insights, therapist,
│   │                        #  reports, admin)
│   ├── services/            # vad, speaker, transcription,
│   │                        #  analysis, queue, pdf_report
│   ├── services/crew/       # CrewAI: 10 agents + insight_crew
│   ├── workers/             # process_segment, aggregate_daily,
│   │                        #  weekly_insights
│   ├── db/supabase_client.py
│   ├── utils/               # auth, logger, errors
│   ├── templates/           # Jinja2: landing, auth, user,
│   │                        #  therapist, admin
│   ├── static/css/          # tokens + base + components (Liquid Glass)
│   ├── migrations/sql/      # 001..006 (extensions, profiles,
│   │                        #  voice, audio pipeline, metrics, RLS)
│   ├── Dockerfile
│   └── Dockerfile.worker
├── mobile/                  # Expo mobile app
│   ├── app/                 # 5 tabs + auth + onboarding
│   ├── services/            # api.ts, supabase.ts
│   ├── hooks/useAuth.tsx
│   ├── locales/             # he.json + en.json
│   └── utils/theme.ts
├── infra/
│   ├── docker/docker-compose.yml
│   └── railway/             # railway.dev/prod/worker.json
├── docs/                    # CLAUDE.md, architecture,
│                            #  setup snapshot, visual references
├── tools/                   # cloned reference repos (gitignored)
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

---

## Database Schema (13 tables, pgvector, RLS enforced)

`profiles`, `therapist_patient_links`, `voice_profiles`,
`recording_preferences`, `audio_segments`, `transcripts`,
`segment_analysis`, `detected_terms`, `daily_metrics`,
`weekly_metrics`, `therapist_notes`, `risk_flags`,
`therapist_access_log`.

**RLS rules:**
- `user` role → only own rows
- `therapist` role → linked patients only (via `is_my_patient(uid)`)
- `admin` role → everything

Helper functions: `is_admin()`, `is_therapist()`,
`is_my_patient(uuid)`.

---

## Audio Pipeline

```
Mobile (VAD + 10s chunk)
      ↓ HTTPS
POST /api/audio/chunk
      ↓
Server-side VAD (RMS + zero-crossing)
      ↓
Speaker verify (stub for MVP → real ECAPA-TDNN later)
      ↓
INSERT audio_segments row
      ↓
Enqueue RQ job (Redis)
      ↓
Worker: Whisper API transcribe
      ↓
Worker: Claude analyze (10 NLP layers)
      ↓
INSERT transcripts + segment_analysis + detected_terms
      ↓
Enqueue aggregate_daily
      ↓
(weekly) CrewAI 10-agent crew → weekly_metrics + risk flags
```

---

## Design System Rules (Liquid Glass)

- **NO 1px borders** — use tonal layering + glass surfaces
- `backdrop-filter: blur(20px)` on all panels
- Pill-shape buttons with gradient fills (purple → teal)
- Breathing animation on recording indicator
- Pastel glow orbs in page background (purple/teal/pink)
- Tri-font editorial scale: **Manrope** (display), **Plus Jakarta
  Sans** (body), **Inter** (labels)
- Respect `prefers-reduced-motion`
- RTL/LTR aware

CSS token file: `api/static/css/tokens.css`
Components: `api/static/css/components.css`

---

## Install Commands (Windows + Git Bash)

```bash
# 1. Supabase CLI (binary - npm doesn't support it globally)
curl -sL https://github.com/supabase/cli/releases/latest/download/supabase_windows_amd64.tar.gz \
  -o /tmp/supabase.tar.gz && \
  tar -xzf /tmp/supabase.tar.gz -C /tmp && \
  mv /tmp/supabase.exe ~/bin/supabase.exe

# 2. Railway CLI
npm install -g @railway/cli
# Note on Windows Git Bash: call /c/Users/User/AppData/Roaming/npm/node_modules/@railway/cli/bin/railway.exe directly

# 3. GitHub CLI (pre-installed on most Windows with Git for Windows)
gh auth login  # OR set GH_TOKEN env var with a PAT

# 4. Python env
conda create -n KARNAF python=3.11 -y
conda activate KARNAF
pip install -r api/requirements.txt

# 5. Redis (local dev)
docker run -d --name maramara-redis -p 6379:6379 redis:7-alpine
```

---

## Reference Repos to Clone Under `tools/` (inspiration only)

```bash
cd tools
git clone --depth 1 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git
git clone --depth 1 https://github.com/obra/superpowers.git
git clone --depth 1 https://github.com/googleworkspace/cli.git google-workspace-cli
git clone --depth 1 https://github.com/affaan-m/everything-claude-code.git
```

These are **reference** repos (not imported into the app).
Folder is git-ignored.

---

## Railway Setup (via GraphQL API — Team Tokens can't use `railway whoami`)

```python
# Create projects, env vars, Redis, public domain, deploy — all via
# POST https://backboard.railway.com/graphql/v2
# with Authorization: Bearer <team-token>
# and User-Agent: curl/8.0 (Cloudflare blocks default Python UA)
```

Key mutations:
- `projectCreate` — new project
- `serviceCreate` — service from GitHub repo
- `serviceInstanceUpdate` — set rootDirectory + dockerfilePath
- `variableCollectionUpsert` — bulk set env vars (needed because
  Railway rate-limits `variableUpsert` to 10 calls / minute)
- `serviceDomainCreate` — public domain
- `serviceInstanceDeployV2` — trigger deploy
- `buildLogs` + `deploymentLogs` — debug failures

---

## Acceptance Criteria

1. `GET /health` returns `{"status":"healthy"}`.
2. Supabase has 13 tables + pgvector extension enabled.
3. Railway has `api` + `worker` + `redis` services running.
4. Docker build completes in **<2 min** (no torch in image).
5. Mobile runs `npm start` with Expo Go QR.
6. Signup → enroll → record flow works end-to-end.
7. RLS blocks cross-tenant reads (therapist can't see non-linked
   patients).

---

## Important Notes

- Raw audio **NEVER persists** (`RETAIN_RAW_AUDIO=false`).
- OpenAI Whisper API used for transcription (no local torch).
- CrewAI runs for **weekly** insights only (per-chunk analysis uses
  Claude directly — cheaper/faster).
- Therapist access audit-logged to `therapist_access_log`.
- Target compliance: **GDPR-style** (EU/Israel), not HIPAA.
- Railway rate limits: use `variableCollectionUpsert` for bulk var
  updates.
- Shared vars in Railway **do NOT auto-inherit** to services —
  explicitly copy via `variableCollectionUpsert` with `serviceId`.

---

## Common Pitfalls to Avoid

- ❌ Do NOT include `webrtcvad`, `torch`, `speechbrain`,
  `faster-whisper` in the Railway image (build fails / too large).
- ❌ Do NOT use fine-grained GitHub PAT without **All repositories** +
  **Contents: Read/Write**.
- ❌ Do NOT call `railway whoami` with Team Tokens — it always fails.
  Use the GraphQL API with `Authorization: Bearer` instead.
- ❌ Do NOT forget `rootDirectory: "api"` +
  `dockerfilePath: "Dockerfile.worker"` on the worker service.
- ❌ Do NOT call Cloudflare-protected Railway GraphQL without
  `User-Agent: curl/8.0` (else `error code: 1010`).
- ❌ Do NOT trigger `serviceInstanceDeployV2` without first copying
  project-level vars into the service scope — worker will crash
  with pydantic ValidationError for missing Supabase/Anthropic
  fields.
- ❌ Do NOT rely on Railway auto-deploy from `git push` without the
  Railway GitHub App installed — it caches the initial clone and
  won't refetch. Workarounds: make repo public, install App, or
  delete+recreate the service.

---

## Quick Reproduction Sequence

```bash
# 1. Create GitHub repo (empty, private or public)
gh repo create <owner>/maramara --private

# 2. Scaffold locally (follow the Structure section above), commit,
#    push to main.

# 3. Create Supabase project, apply migrations 001..006 via
#    Supabase Management API (POST /v1/projects/<ref>/database/query).

# 4. Create Railway projects (dev + prod). Add Redis as service
#    (image: redis:7-alpine). Set all env vars via
#    variableCollectionUpsert. Create api + worker services from
#    GitHub repo.

# 5. Trigger deploys. Wait for /health to return 200.
```

---

**End of prompt.** Save this file as `docs/INSTALL-PROMPT.md` in the
project root and it will be committed with the repo for future
reference.
