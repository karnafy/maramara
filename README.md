# MARAMARA

**Therapeutic Speech Intelligence Platform**

> "I don't just record what you said. I show you how you speak to the world,
> what activates you, and what actually calms you down."

MARAMARA analyses daily speech on-device, verifies the speaker, transcribes, and
produces 10-layer NLP insights: triggers, regulation mechanisms, self-talk patterns,
cognitive distortions, escalation loops, phrase mining, and weekly progress tracking.

Three user types — **user**, **therapist/coach**, **admin** — share the same
backend but see different UIs.

---

## Stack

- **Backend:** Flask 3 + Python 3.11 (conda env `KARNAF`)
- **Database:** Supabase (Postgres 17 + pgvector + RLS)
- **Jobs:** RQ + Redis
- **AI:** CrewAI (10 therapeutic agents) + Claude Sonnet 4.6 + faster-whisper large-v3 + SpeechBrain ECAPA + Silero VAD
- **Therapist Web:** Flask server-rendered (Jinja2 + HTML + CSS, no JS framework)
- **Mobile:** React Native + Expo SDK 54 (TypeScript, i18next HE/EN)
- **Design:** Liquid Glass UI (frosted panels + ambient gradients) + Stitch "The Empathetic Observer"
- **Deploy:** Railway (dev + prod) + Docker

Full architecture + data model → [CLAUDE.md](./CLAUDE.md).

---

## Quick start

```bash
# Prerequisites: conda, Node 22+, Docker (optional)

# 1. Clone
git clone https://github.com/karnafy/maramara.git
cd maramara

# 2. Python environment
conda create -n KARNAF python=3.11 -y
conda activate KARNAF
pip install -r api/requirements.txt

# 3. Environment variables
cp .env.example .env
# Edit .env with your Supabase + Anthropic + Redis URLs

# 4. Apply migrations
cd api && python cli.py migrate apply && cd ..

# 5. Run Redis
docker run -d --name maramara-redis -p 6379:6379 redis:7-alpine

# 6. Run backend (two terminals)
cd api && flask --app app run --debug --port 5000
cd api && python worker_main.py

# 7. Run mobile (separate terminal)
cd mobile && npm install && npm start
```

Or with one command:

```bash
docker compose -f infra/docker/docker-compose.yml up
```

Web dashboard: <http://localhost:5000>
API docs + endpoints: see `api/routes/*.py`

---

## Project structure

```
maramara/
├── api/                 # Flask backend + Jinja2 therapist dashboard
├── mobile/              # Expo mobile app
├── infra/               # Docker + Railway configs
├── docs/                # Product spec, architecture, setup snapshot
├── tools/               # Cloned reference repos (gitignored)
└── CLAUDE.md            # AI-assistant project guide
```

---

## Management CLI

```bash
python api/cli.py user list
python api/cli.py user set-role user@example.com therapist
python api/cli.py queue stats
python api/cli.py queue run-weekly user@example.com
python api/cli.py report weekly user@example.com
python api/cli.py doctor
```

---

## Deployment

Two Railway environments:
- **`maramara-dev`** → tracks `main` branch (or `dev` if you prefer)
- **`maramara-prod`** → tracks `release` branch

Config files in `infra/railway/`:
- `railway.dev.json` — dev service
- `railway.prod.json` — prod service (2 replicas)
- `railway.worker.json` — RQ worker

---

## Privacy & ethics

- **Raw audio never persists** by default (transcripts + metadata only).
- **Explicit consent** at onboarding.
- **Row Level Security** enforced at the database level.
- **Therapist access is audit-logged** (`therapist_access_log`).
- Full data export + deletion via admin CLI.

Target compliance: **GDPR-style (Israel/EU)**. HIPAA is a future concern.

---

## License

Internal / proprietary. All rights reserved, KARNAF AI.
