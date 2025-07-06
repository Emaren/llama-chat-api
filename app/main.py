# app/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.llama3_router import router as llama3_router
from httpx import ReadTimeout
import httpx
import logging

app = FastAPI(
    title="Llama Chat API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ✅ CORS config for frontend + API domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3006",
        "http://127.0.0.1:3006",
        "http://172.20.10.3:3006",
        "https://llama-chat.aoe2hdbets.com",
        "https://chat-api.aoe2hdbets.com",
        "https://aoe2hdbets.com"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Mount Llama3 chat endpoint under /llama3 (for direct NGINX routing)
app.include_router(llama3_router, prefix="/llama3")

# ✅ Also mount legacy-compatible API endpoint at /api/chat
app.include_router(llama3_router, prefix="/api/chat")

# ✅ Mock conversation memory for system boot
mock_data = {
    "LlamaAgent38BQ4KM": [],
    "Redlinekey": [
        {"from": "Redlinekey", "text": "Brakes done. Hubs torqued."},
        {"from": "me", "text": "Copy that. Syncing task."},
    ],
    "LlamaAgent42": [
        {"from": "LlamaAgent42", "text": "Agent heartbeat ✅"},
        {"from": "me", "text": "Status acknowledged."},
    ],
    "WoloDaemon": [
        {"from": "WoloDaemon", "text": "Block height synced: 93144"},
        {"from": "me", "text": "Hashrate trending stable?"},
    ]
}

from app.agent_models import model_routes

@app.get("/api/agents/health")
def agents_health():
    return {"status": "healthy"}

@app.get("/")
def root():
    return {"status": "🧠 Llama Chat API running"}

@app.get("/api/chat/agents")
def get_agents():
    return list(mock_data.keys())

@app.get("/api/chat/messages/{agent}")
def get_messages(agent: str):
    return mock_data.get(agent, [])

@app.post("/api/chat/send")
async def send_message(req: Request):
    data = await req.json()
    user_input = data.get("text")
    agent = data.get("to", "LlamaAgent42")

    logging.info(f"🚨 USER: {user_input}")

    model = model_routes.get(agent, "llama3")

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": user_input}],
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post("http://localhost:11434/api/chat", json=payload)
            res.raise_for_status()
            output = res.json()
            reply = output["message"]["content"]
            logging.info(f"📦 RESPONSE: {reply}")
            return {"from": agent, "text": reply}

    except ReadTimeout:
        logging.warning("⏰ TIMEOUT talking to Ollama backend")
        return JSONResponse(status_code=504, content={"error": "LLaMA3 backend timed out"})

    except Exception as e:
        logging.error(f"🔥 ERROR: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal error talking to LLaMA3 backend"})
