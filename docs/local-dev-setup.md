# Local Development Setup

## Prerequisites

- Windows 11 / macOS / Linux
- **Conda** (Anaconda or Miniconda)
- **Node.js** ≥ 22 + npm
- **Git**
- **Docker Desktop** (optional, for docker-compose)
- **Expo Go** app on your phone (for mobile testing)
- **GitHub CLI** (`gh`) authenticated

---

## 1. Python environment — `KARNAF`

```bash
conda create -n KARNAF python=3.11 -y
conda activate KARNAF
pip install -r api/requirements.txt
```

Note: The first install pulls PyTorch + SpeechBrain + faster-whisper.
On Windows with Python 3.11 this should succeed; Python 3.14 won't build pydantic-core wheels.

---

## 2. Environment variables

```bash
cp .env.example .env
```

Populate the secrets (Supabase keys, Anthropic API key, etc.). See
`docs/SETUP-SNAPSHOT.md` for the dev-project values.

---

## 3. Supabase migrations

```bash
cd api
python cli.py migrate apply
```

This applies all files in `api/migrations/sql/` via the Supabase Management API.
Requires `SUPABASE_ACCESS_TOKEN` + `SUPABASE_PROJECT_REF` in env.

---

## 4. Redis

```bash
docker run -d --name maramara-redis -p 6379:6379 redis:7-alpine
```

Or install Redis natively. The URL `redis://localhost:6379/0` is the default.

---

## 5. Run the backend

### Option A — Two terminals

```bash
# Terminal 1: API
cd api
flask --app app run --debug --port 5000

# Terminal 2: Worker
cd api
python worker_main.py
```

### Option B — Docker Compose (recommended)

```bash
docker compose -f infra/docker/docker-compose.yml up --build
```

This boots Redis + API + Worker with hot-reload volumes.

---

## 6. Mobile

```bash
cd mobile
npm install
cp .env.example .env
npm start
```

Scan the QR code with Expo Go, or press `i`/`a` for iOS/Android simulator.

For web preview:
```bash
npm run web
```

---

## 7. Verify

```bash
curl http://localhost:5000/health
# {"status":"healthy","service":"maramara-api"}

cd api && python cli.py doctor
# Table of env-var checks
```

Open <http://localhost:5000> in your browser — you should see the MARAMARA landing page.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` on boot | `pip install -r api/requirements.txt` (in KARNAF env) |
| `pydantic-core` build fails | Make sure conda env uses Python 3.11, not 3.14 |
| Whisper model download hangs | Set `HF_HUB_ENABLE_HF_TRANSFER=1` or use `whisper_model=base` |
| `No module named silero_vad` | Normal on first run — it downloads via torch.hub |
| `connection refused: redis` | Check Docker container is running: `docker ps` |
| Supabase 401 errors | Verify `SUPABASE_SERVICE_ROLE_KEY` matches the project |

---

## Editor setup

VS Code + Cursor recommended. Install:
- Python extension
- Pylance
- Ruff (format on save)
- ES7+ React/Redux snippets (for mobile)

Enable workspace setting:
```json
{
  "python.defaultInterpreterPath": "~/anaconda3/envs/KARNAF/bin/python",
  "editor.formatOnSave": true,
  "[python]": { "editor.defaultFormatter": "charliermarsh.ruff" }
}
```
