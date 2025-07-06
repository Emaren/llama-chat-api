# app/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from app.llama3_router import router as llama3_router
from app.agent_models import model_routes
from httpx import ReadTimeout
import httpx, logging, asyncio, json

app = FastAPI(
    title="Llama Chat API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─────────────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3006",
        "http://127.0.0.1:3006",
        "http://172.20.10.3:3006",
        "https://llama-chat.aoe2hdbets.com",
        "https://chat-api.aoe2hdbets.com",
        "https://aoe2hdbets.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ─────────────────────────────────────────────────────────────────────────────

app.include_router(llama3_router, prefix="/llama3")     # direct path
app.include_router(llama3_router, prefix="/api/chat")   # legacy path

# ---------------------------------------------------------------------------#
#  Mock boot-memory (trimmed for brevity)                                    #
# ---------------------------------------------------------------------------#
mock_data = {
    "LlamaAgent42": [
        {"from": "LlamaAgent42", "text": "Agent heartbeat ✅"},
        {"from": "me", "text": "Status acknowledged."},
    ]
}

# ─────────────────────── Auxiliary endpoints ────────────────────────────────
@app.get("/api/agents/health")
def agents_health():  return {"status": "healthy"}

@app.get("/")                          # sanity ping
def root():            return {"status": "🧠 Llama Chat API running"}

@app.get("/api/chat/agents")
def get_agents():       return list(mock_data.keys())

@app.get("/api/chat/messages/{agent}")
def get_messages(agent: str):
    return mock_data.get(agent, [])

# ─────────────────────────── Main send endpoint ─────────────────────────────
@app.post("/api/chat/send")
async def send_message(req: Request):
    data       = await req.json()
    user_input = data.get("text")
    agent      = data.get("to", "LlamaAgent42")
    stream     = data.get("stream", False)

    logging.info(f"🚨 USER: {user_input}")

    payload = {
        "model": model_routes.get(agent, "llama3"),
        "messages": [{"role": "user", "content": user_input}],
        "stream": stream,
    }

    # -------- Streaming branch (SSE) ----------------------------------------
    if stream:

        async def stream_generator():
            try:
                async with httpx.AsyncClient(timeout=None) as client:
                    async with client.stream(
                        "POST", "http://localhost:11434/api/chat", json=payload
                    ) as res:
                        async for line in res.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            content = line.removeprefix("data:").strip()
                            if content:
                                # VALID JSON FRAME
                                yield (
                                    f"data: "
                                    f"{json.dumps({'data': content, 'done': False})}\n\n"
                                )
                # final sentinel
                yield 'data: {"done": true}\n\n'
                await asyncio.sleep(0)
            except Exception as e:
                logging.error(f"🔥 stream error: {e}")
                yield 'data: {"done": true}\n\n'
                await asyncio.sleep(0)

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # -------- Non-stream branch --------------------------------------------
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post("http://localhost:11434/api/chat", json=payload)
            res.raise_for_status()
            reply = res.json()["message"]["content"]
            logging.info(f"📦 RESPONSE: {reply}")
            return {"from": agent, "text": reply}

    except ReadTimeout:
        return JSONResponse(504, {"error": "LLaMA3 backend timed out"})
    except Exception as e:
        logging.error(f"🔥 ERROR: {e}")
        return JSONResponse(500, {"error": "Internal server error"})

# ─── helper so POST /send/stream (no /api/) works the same ──────────────────
@app.post("/send/stream")
async def send_stream(req: Request):
    body = await req.json()
    body["stream"] = True

    class _R:       # tiny shim to reuse send_message
        async def json(self): return body

    return await send_message(_R())
