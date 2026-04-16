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
- **Status:** Pending valid Account Token from user
- **Earlier token** `528c5cf1-61c9-4e75-979d-723687db0a0d` failed `whoami` (invalid/expired)
- **Next step:** Get new token from https://railway.com/account/tokens
- **Planned projects:** `maramara-dev` + `maramara-prod`

### GitHub
- **Planned repo:** single repo `karnafy/maramara`
- **Auth:** pending `gh auth login` in new session

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
