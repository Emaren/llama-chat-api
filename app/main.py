"""
Application bootstrap
Only the /api/chat router is exposed (no legacy aliases).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.llama3_router import router as chat_router

app = FastAPI(
    title="Llama-Chat API",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ─────────────────────────── CORS ────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3006",
        "http://127.0.0.1:3006",
        "https://llama-chat.aoe2hdbets.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ──────────────────────────────────────────────────────────────

# attach router once (no legacy prefixes)
app.include_router(chat_router, prefix="/api/chat")


@app.get("/")                       # sanity ping
def root():
    return {"status": "🧠 Llama-Chat API running"}

