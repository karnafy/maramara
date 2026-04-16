# MARAMARA — System Architecture

## High-level diagram

```
┌──────────────┐      ┌────────────────────┐      ┌──────────────────┐
│ Mobile App   │      │ Flask API          │      │ Supabase         │
│ (Expo / RN)  │◀────▶│ (monolith)         │◀────▶│ Postgres 17      │
│              │ HTTP │ Gunicorn + Jinja2  │  SQL │ + pgvector + RLS │
└──────┬───────┘      │                    │      │ + Auth           │
       │              │ ┌─Routes (8 bp)────┤      └──────────────────┘
       │              │ ├─Services (VAD/  │
       │              │ │  speaker/STT/   │
       │              │ │  analysis/      │
       │              │ │  CrewAI/PDF)    │
       │              │ └─Templates (HTML)│
       │              └────────┬───────────┘
       │                       │ enqueue
       │              ┌────────▼───────────┐
       │              │ Redis + RQ         │
       │              └────────┬───────────┘
       │                       │
       │              ┌────────▼───────────┐
       │              │ RQ Worker          │
       │              │ (transcription,    │
       │              │  analysis,         │
       │              │  CrewAI weekly)    │
       │              └────────────────────┘
       │
       ▼
 Device-local:
 VAD (Silero via ONNX)
 Audio chunk buffer
```

---

## Component responsibilities

### Mobile (Expo)
- Records audio chunks (10s, 16 kHz mono) during user-configured hours.
- Runs lightweight client-side VAD to avoid uploading silence.
- Uploads to `POST /api/audio/chunk` with JWT auth.
- Never persists raw audio after successful upload.
- Displays dashboard (home, timeline, insights, listen, settings).

### Flask API
Eight blueprints under `api/routes/`:

| Blueprint | Prefix | Purpose |
|-----------|--------|---------|
| `auth` | `/auth` | Signup/login/logout (HTML + JSON) |
| `voice` | `/voice` | Enrollment (3 chunks → embedding) |
| `audio` | `/api/audio` | Chunk upload + status |
| `dashboard` | `/dashboard` | User HTML + JSON |
| `insights` | `/api/insights` | Aggregations + weekly insights |
| `therapist` | `/therapist` | Therapist HTML + patient overview + notes |
| `reports` | `/reports` | PDF export |
| `admin` | `/admin` | User management + risk flags |

### RQ Worker
Listens on queue `maramara-segments`. Three job types:

1. `process_segment(segment_id, user_id, audio_b64)` — transcription + analysis + enqueue daily aggregation.
2. `aggregate_daily(user_id, date)` — rolls up `segment_analysis` into `daily_metrics`.
3. `weekly_insights(user_id, week_start)` — runs CrewAI (10 agents).

### CrewAI System (`services/crew/`)
- `agents.py` — 10 agent factories (trigger, regulation, self-talk, distortions, escalation loops, phrase mining, progress, therapist summary, user reflection, risk).
- `tasks.py` — task definitions with JSON output contract.
- `insight_crew.py` — orchestrator that pulls weekly data, runs the crew, and persists results.

---

## Data flow: a single 10-second chunk

1. Mobile runs VAD locally; if voice detected, uploads chunk.
2. Flask `/api/audio/chunk` receives multipart request.
3. Server-side VAD (Silero) re-verifies speech.
4. Speaker embedding extracted (SpeechBrain ECAPA).
5. Cosine similarity vs enrolled voice; threshold 0.75.
6. Row inserted in `audio_segments` (with `matched_to_user`, `speaker_match_score`).
7. If matched: job enqueued on Redis.
8. Worker transcribes (faster-whisper large-v3, auto-detect HE/EN).
9. Worker runs Claude Sonnet 4.6 analysis (10 layers → JSON).
10. `transcripts`, `segment_analysis`, `detected_terms` populated.
11. Worker enqueues `aggregate_daily`; `daily_metrics` row upserted.

## Data flow: weekly insights

1. Scheduler (APScheduler or cron) triggers `weekly_insights` every Sunday 00:05.
2. Worker pulls last-7-days `segment_analysis` + transcripts + baseline.
3. CrewAI builds context JSON, spins up 10 agents sequentially.
4. Each agent returns a JSON fragment; orchestrator merges.
5. Results stored in `weekly_metrics.crewai_insights` + `therapist_summary`.
6. Risk agent output → `risk_flags` if severity ≥ medium.

---

## Security boundaries

| Layer | Enforcement |
|-------|-------------|
| Transport | HTTPS (Railway terminates TLS) |
| Auth | Supabase JWT verified per request via `require_auth` |
| Authorization | Role check via `require_role('user'|'therapist'|'admin')` |
| Database | **Row Level Security** on all user-owned tables |
| Therapist access | RLS function `is_my_patient(uid)` + audit log row |
| Secrets | Railway env vars; never committed |
| Audio | Not stored (default); transcripts encrypted at rest by Supabase |

---

## Deployment environments

| Env | Supabase project | Railway service | Branch |
|-----|------------------|-----------------|--------|
| Development | `maramara-dev` | `maramara-dev` | `main` |
| Production | `maramara-prod` (requires Supabase Pro plan) | `maramara-prod` | `release` |

Mobile builds via EAS:
```bash
cd mobile
eas build --profile development --platform all
eas build --profile production --platform all
```

---

## Observability

- `structlog` → Railway logs (JSON-capable).
- `/health` endpoint for Railway healthchecks.
- `python cli.py doctor` for env + dependency sanity checks.
- `queue stats` for Redis / RQ inspection.
- Supabase dashboard for SQL metrics + RLS policy audit.

Future: OpenTelemetry + Sentry for error tracking, Grafana dashboards for KPIs.
