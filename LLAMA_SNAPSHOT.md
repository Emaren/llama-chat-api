# 🧩 LLAMA DEV SNAPSHOT — v2025-07-23.1

📌 **Latest**: ✅ Clean venv rebuild · ✅ `.envrc` + pyenv auto-activation  
📌 **Prior**: PM2 + venv best practices · GitHub secret cleanup  
📌 **Earlier**: Tile polling fix · Next.js metadata bug

---

## ✅ STACK STATUS (LIVE)

| Layer             | Port   | Component          | Tech/Status                  |
|------------------|--------|--------------------|------------------------------|
| 🎯 AoE2HD App     | —      | Frontend           | Next.js ✅ (Flutter live)    |
| 🎯 AoE2HD API     | 8003   | Betting backend    | FastAPI ✅                   |
| 🧠 Metrics API    | 8005   | `llama-api`        | FastAPI ✅                   |
| 🧩 Agent Chat API | 8006   | `llama-chat-api`   | FastAPI ✅ SSE patched       |
| 💬 Chat UI        | 3006   | `llama-chat-app`   | Next.js ✅ Streams OK        |
| 📊 Dashboard UI   | 3005   | `llama-dashboard`  | Next.js ✅ Metrics flow      |
| 🧠 Ollama LLM     | —      | LLaMA 3 8b Q4_K_M   | ✅ Local inference           |
| 🎭 OpenAI Agent   | —      | Agent4oMP          | ✅ Prompt-Mgmt injected      |

---

## 🧰 PM2 SNAPSHOT

| Name                | Port(s)       | Tech         |
|---------------------|---------------|--------------|
| token_tap_app       | 3007          | Next.js      |
| token_tap_api       | 8007          | FastAPI      |
| redline-legal-app   | 3004          | Next.js      |
| redline-legal-api   | 8004          | FastAPI      |
| explorer-prod       | 4173          | Vite         |
| wolo-prod           | 26656/26657   | Cosmos SDK   |

---

## 🐚 INFRA & DEV HYGIENE

- ✅ PM2 frontend: `start-llama.sh`  
- ✅ PM2 backend: `venv/bin/python -m uvicorn …`  
- ✅ venv auto-activation: `.envrc + pyenv local 3.11.9`  
- ✅ Clean Python: 3.11.9 (via `pyenv`, rebuilt `venv`)  
- ✅ Git hygiene: `.gitignore` updated to exclude `venv/`, `.env`, `.idea/`, `.pyc`  
- ✅ Mobile testing: iOS/Safari requires `*.ngrok-free.app` (not `localhost`)

---

## 🔌 CHAT SYSTEM

- Framework: React 19.1 + Next.js 15.3.4 + Tailwind ✅  
- Markdown: via `ReactMarkdown` ✅  
- Streaming: via `streamChat()` ✅  
- Key API routes: `/api/chat/send`, `/chat/messages/{agent}`, `/responses` ✅

---

## 📊 DASHBOARD SYSTEM

- Frontend: `Next.js 15.3.4` @ `:3005`  
- Backend: `FastAPI` @ `:8005`  
- Live endpoints: `/stats/tokens`, `/system-vitals`, `/agents/health`  
- Token tile auto-refresh: 🔄 in progress

---

## 🧠 OLLAMA (LOCAL LLM)

- Model: `llama3:8b-instruct-q4_K_M`  
- Streaming + Persona inject ✅  
- Memory: `./memory/{agent}.json` (12K cap)  
- `keep_alive: false` (patched to avoid stale containers)

---

## ⚠️ BUGS + FIXES

| Issue                         | Fix                                           |
|------------------------------|-----------------------------------------------|
| ❌ Stream reply not visible   | `logRef[idx] = {…}` + `flushSync()`         |
| ❌ Token tile stale           | `refetchInterval: 10000` + `invalidateQueries()` |
| ❌ Agent4oMP SSE fallback     | Inject `<prompt:…>` tag + `client.responses.create()` |

---

## 🧱 NEXT.JS & .ENV PATCHES

- ✅ `.env` secret leak fixed (via BFG, rotated, re-ignored)  
- ✅ Hydration fix: wrap with `<ClientProviders>{children}</ClientProviders>`

---

## 🧠 MEMORY SYSTEM STATUS

| Feature              | Status   | Notes                          |
|----------------------|----------|--------------------------------|
| Persistent JSON      | ✅        | Per-agent memory               |
| Prepend into GPT     | ✅        | Injected at start              |
| Tagging entries      | 🟡        | Inline scoped tags             |
| FAISS vector search  | 🟡        | Scaffolded                     |
| Scoped filters       | 🟡        | Token-fit filtering            |
| GPT summaries        | 🟡        | Auto-chunking in dev           |
| Pruning              | 🔜        | Next pass                      |
| Manual testing       | ✅        | All agents validated           |

---

## 🔬 MEMORY ROADMAP — v2025 Q3

- 🥇 `🔖 Tagging` + `🧠 Embeddings` — High  
- 🥇 `📁 Scoped filters` — High  
- 🥇 `💬 GPT summaries` — Medium  
- 🥈 `🧹 Pruning` — Medium  
- 🥉 `🧬 Mutation / Replay` — Low  
- 📂 Next: `vector_memory.py`

---

## 🐚 VENV STATUS

| Project            | Activated Via                        |
|--------------------|--------------------------------------|
| `llama-chat-api`   | ✅ `source venv/bin/activate` (3.11.9) |
| `llama-chat-app`   | ✅ `.envrc` + `direnv`               |
| `llama-dashboard`  | ✅ `.envrc` + `direnv`               |
| `llama-api`        | ✅ `.envrc` + `direnv`               |

---

## 📋 FEATURE SNAPSHOT

✅ SSE backend  
✅ Markdown rendering  
✅ Agent-based memory  
✅ Per-agent stream isolation  
⚠️ Prompt-Mgmt SSE fix pending  
🔄 Token tile refresh pending  

---

## 📱 MOBILE / NGROK ACCESS

- ❌ iOS Safari fails on `localhost`  
- ✅ Use:  
  `NEXT_PUBLIC_API_BASE=https://<your-subdomain>.ngrok-free.app`
