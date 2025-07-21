# app/main.py
"""
Llama-Chat (agent runtime)
──────────────────────────
Only the /api/chat endpoints needed by the UI live here.
Run (dev):
    uvicorn app.main:app --reload --port 8006
"""

from __future__ import annotations
import os, sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# make "app.*" importable when cwd ≠ repo root
BASE_DIR = os.path.dirname(__file__)
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from app.llama3_router import router as chat_router  # noqa: E402

# ── FastAPI instance ───────────────────────────────────────────────
app = FastAPI(
    title="Llama-Chat Agent API",
    version="0.3.1",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS using FRONTEND_ORIGIN ─────────────────────────────────────
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3006")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── routes ────────────────────────────────────────────────────────
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])

# ── health probe ─────────────────────────────────────────────────
@app.get("/", tags=["meta"])
async def root():
    return {"status": "🧠 llama-chat running"}

from app.llama3_router import history  # <-- already defined route handler
from fastapi.routing import APIRoute

# Mount the /messages/{agent} path globally as well
app.add_api_route(
    path="/messages/{agent}",
    endpoint=history,
    methods=["GET"],
    tags=["chat"]
)
