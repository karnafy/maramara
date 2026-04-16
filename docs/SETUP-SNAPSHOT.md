# MARAMARA — Setup Snapshot

**Date:** 2026-04-16
**Purpose:** Full installation record for reproduction in future projects.

---

## 1. Machine Environment

| Component | Version | Path |
|-----------|---------|------|
| OS | Windows 11 Pro | — |
| Shell | Git Bash (Unix-style) | `/mingw64/bin/bash` |
| Conda | 26.1.1 | `C:\Users\User\anaconda3` |
| Node.js | 22.22.0 | `/c/Program Files/nodejs` |
| npm | 10.9.4 | — |
| Python | 3.13.9 (system) / 3.11 (conda KARNAF) | — |
| Git | mingw64 | `/mingw64/bin/git` |
| GitHub CLI | installed | `/c/Program Files/GitHub CLI/gh` |

---

## 2. Conda Environments (existing)

```bash
conda env list
```

- `base` - `C:\Users\User\anaconda3`
- `IVRIT` - Hebrew NLP work
- `SASSOMM` - prior project
- `SITESDESIGN` - prior project
- **`KARNAF`** ← MARAMARA (created in this project)

### Create KARNAF env
```bash
conda create -n KARNAF python=3.11 -y
conda activate KARNAF
pip install -r api/requirements.txt
```

---

## 3. Installed CLIs

### Supabase CLI v2.90.0
- **Install:** Binary download from GitHub releases
- **Path:** `C:\Users\User\bin\supabase.exe`
- **Auth:** `export SUPABASE_ACCESS_TOKEN=sbp_xxx`
- **Install command:**
  ```bash
  curl -sL "https://github.com/supabase/cli/releases/latest/download/supabase_windows_amd64.tar.gz" -o supabase.tar.gz
  tar -xzf supabase.tar.gz
  mv supabase.exe "/c/Users/User/bin/supabase.exe"
  ```

### Railway CLI
- **Install:** `npm install -g @railway/cli`
- **Path:** `C:\Users\User\AppData\Roaming\npm\node_modules\@railway\cli\bin\railway.exe`
- **Auth:** `RAILWAY_TOKEN=xxx` or `RAILWAY_API_TOKEN=xxx`
- **Known issue on Git Bash/Windows:** `.cmd` wrapper path-resolution breaks. Call the `.exe` directly:
  ```bash
  "/c/Users/User/AppData/Roaming/npm/node_modules/@railway/cli/bin/railway.exe" <cmd>
  ```

### GitHub CLI (pre-existing)
- **Path:** `C:\Program Files\GitHub CLI\gh.exe`
- **Auth:** `gh auth login` (interactive)

---

## 4. Cloned Repositories (under `tools/`)

| Repo | Purpose | URL |
|------|---------|-----|
| `ui-ux-pro-max-skill` | Design intelligence (50+ styles, 161 palettes, 57 fonts) | https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git |
| `superpowers` | Claude Code skill collection | https://github.com/obra/superpowers.git |
| `google-workspace-cli` | Google Workspace CLI | https://github.com/googleworkspace/cli.git |
| `everything-claude-code` | Claude Code conventions + skills | https://github.com/affaan-m/everything-claude-code.git |

### Reinstall commands
```bash
cd tools
git clone --depth 1 https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git
git clone --depth 1 https://github.com/obra/superpowers.git
git clone --depth 1 https://github.com/googleworkspace/cli.git google-workspace-cli
git clone --depth 1 https://github.com/affaan-m/everything-claude-code.git
```

---

## 5. Cloud Services

### Supabase
| Field | Value |
|-------|-------|
| Organization | `KARNAF AI` |
| Organization ID | `pjghflhcnajyektrtors` |
| Project Name | `maramara-dev` |
| Project Ref | `tfygluotkrfjougyrvbw` |
| URL | `https://tfygluotkrfjougyrvbw.supabase.co` |
| Region | Central EU (Frankfurt) |
| Plan | Free (max 2 projects per org) |
| DB Password | `buVX1T9kOYtrsOXEJ4Zw8RsK` (stored in `.supabase-db-password.txt`) |
| Dashboard | https://supabase.com/dashboard/project/tfygluotkrfjougyrvbw |
| Access Token | `sbp_...` (stored in OS env, rotate after handoff) |

**Existing Free-plan project:** `ClearBalance` (ref: `bknswnzipvdtqsfhhsss`)
→ To create `maramara-prod`, either upgrade to Pro or pause/delete one.

### Railway
| Field | Value |
|-------|-------|
| Workspace | `karnafy's Projects` |
| Token type | **Team/Workspace Token** (uses Bearer auth, cannot query `me`) |
| Token | `bc3596e0-c1f1-4872-b95a-cbbbef1073eb` (rotate after handoff) |
| Note | Railway CLI `railway whoami` fails with team tokens — use GraphQL API |

#### Projects

**maramara-dev**
- Project ID: `eea1deb6-21f7-4cf8-812a-22a358ef3fc6`
- Environment ID: `5f900729-c9fe-4766-9788-f135c2d2301a` (default `production`)
- Redis service ID: `85cd82bd-b555-49e8-95d1-451d80af07b7`
- Dashboard: https://railway.com/project/eea1deb6-21f7-4cf8-812a-22a358ef3fc6

**maramara-prod**
- Project ID: `bf0bf164-c3c5-40e5-bd82-44eadf8aa5e3`
- Environment ID: `551cd4eb-0fa2-49cb-aa19-3115a615c1e7` (default `production`)
- Redis service ID: `89f287f1-427d-4570-b4ef-eef2bbcf73fc`
- Dashboard: https://railway.com/project/bf0bf164-c3c5-40e5-bd82-44eadf8aa5e3

#### Env vars already set (both projects)

`APP_ENV`, `FLASK_ENV`, `DEBUG`, `LOG_LEVEL`, `SUPABASE_URL`,
`SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_PROJECT_REF`,
`DATABASE_URL`, `DB_PASSWORD`, `SECRET_KEY` (unique per env),
`DEFAULT_LANGUAGE`, `SUPPORTED_LANGUAGES`, `CREWAI_MODEL`,
`RETAIN_RAW_AUDIO`, `ENABLE_CREWAI_INSIGHTS`,
`SPEAKER_SIMILARITY_THRESHOLD`, `VAD_THRESHOLD`, `WHISPER_MODEL`,
`WHISPER_DEVICE`, `AUDIO_CHUNK_DURATION_SEC`, `AUDIO_SAMPLE_RATE`.

#### Still TODO (user action required)

- [ ] Add `ANTHROPIC_API_KEY` to both projects (via Railway dashboard → project → Variables)
- [ ] Add `REDIS_URL` reference: `${{Redis.REDIS_URL}}` (once first deploy exposes it)
- [ ] Create `api` service from GitHub repo (after repo is pushed)
- [ ] Create `worker` service using `Dockerfile.worker`

### GitHub
- **Repo:** `karnafy/maramara` (private) — https://github.com/karnafy/maramara
- **Auth:** Fine-grained PAT with `All repositories` + `Contents: Read/Write`
- **Token (rotate after handoff):** `github_pat_11B26EK4Y0iZ12LUkZhcfz_...`

---

## 6. Environment Variables Used

See `.env.example` for full list. Secret values saved locally in `.env` (git-ignored):

```
SUPABASE_ACCESS_TOKEN=sbp_645e548f2c0487b0a40126477944de8494e7d790
SUPABASE_URL=https://tfygluotkrfjougyrvbw.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_PROJECT_REF=tfygluotkrfjougyrvbw
DB_PASSWORD=buVX1T9kOYtrsOXEJ4Zw8RsK
```

---

## 7. Claude Code Skills & Plugins (pre-existing on machine)

From paths in `$PATH`:
- `ui-ux-pro-max` @ `C:\Users\User\.claude\plugins\cache\ui-ux-pro-max-skill\ui-ux-pro-max\2.0.1`
- `superpowers` @ `C:\Users\User\.claude\plugins\cache\claude-plugins-official\superpowers\5.0.7`
- `frontend-design` @ `C:\Users\User\.claude\plugins\cache\claude-plugins-official\frontend-design`
- `code-review` @ `C:\Users\User\.claude\plugins\cache\claude-plugins-official\code-review`
- `ui-design` @ `C:\Users\User\.claude\plugins\cache\claude-code-workflows\ui-design\1.0.1`

---

## 8. Stack Decisions (for MARAMARA)

| Layer | Choice |
|-------|--------|
| Backend | **Flask** + Python 3.11 + Pydantic v2 + PyJWT |
| Job Queue | **RQ** + Redis |
| Database | **Supabase** PostgreSQL + pgvector + RLS |
| Auth | Supabase Auth (JWT) |
| Therapist Web | **Jinja2 HTML + CSS** (server-rendered via Flask) |
| Mobile | **React Native + Expo SDK 54** + TypeScript |
| AI Insights | **CrewAI** (weekly/daily), Claude Sonnet 4.6 for base NLP |
| VAD | Silero |
| Speaker Verification | SpeechBrain ECAPA-TDNN |
| Transcription | faster-whisper large-v3 |
| Container | Docker + Railway |
| Repo | Single git repo `maramara` (no workspaces) |
| Languages | Hebrew + English |

---

## 9. Quick Reproduction Script

```bash
# 1. Install CLIs
curl -sL "https://github.com/supabase/cli/releases/latest/download/supabase_windows_amd64.tar.gz" -o /tmp/supabase.tar.gz && tar -xzf /tmp/supabase.tar.gz -C /tmp && mv /tmp/supabase.exe "$HOME/bin/supabase.exe"
npm install -g @railway/cli

# 2. Clone repo
git clone https://github.com/karnafy/maramara.git && cd maramara

# 3. Install tool repos (reference)
mkdir -p tools && cd tools
for repo in "nextlevelbuilder/ui-ux-pro-max-skill" "obra/superpowers" "googleworkspace/cli" "affaan-m/everything-claude-code"; do
  git clone --depth 1 "https://github.com/$repo.git"
done
cd ..

# 4. Conda env
conda create -n KARNAF python=3.11 -y
conda activate KARNAF
pip install -r api/requirements.txt

# 5. Env vars
cp .env.example .env
# edit .env with your credentials

# 6. Run
flask --app api/app run --debug
```

---

## 10. Rotation / Security Checklist

When handing off / ending session:

- [ ] Revoke `sbp_645e548f2c0487b0a40126477944de8494e7d790` at https://supabase.com/dashboard/account/tokens
- [ ] Revoke old Railway token (if issued)
- [ ] Rotate DB password in Supabase dashboard
- [ ] Never commit `.env` or `.supabase-db-password.txt` (already in `.gitignore`)

---

**End of snapshot.** Re-run step 9 to reproduce from scratch on a new machine.
