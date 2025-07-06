"""
llama3_router.py — FastAPI ↔ Ollama gateway  (SSE + one-shot JSON)

Compatible with Ollama ≥ 0.9.x using the /api/chat endpoint.
"""

from __future__ import annotations

import json
import time
from typing import AsyncGenerator, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent_models import model_routes
from app.memory import load_memory, save_memory

# ─────────────────────────── settings ────────────────────────────
OLLAMA_URL            = "http://localhost:11434/api/chat"
MAX_HISTORY_CHARS     = 12_000
CLIENT_IDLE_TIMEOUT_S = 120

router = APIRouter()
# ─────────────────────────────────────────────────────────────────


# ────────────────────────── helpers ──────────────────────────────
def list_agents() -> List[str]:
    """Return the configured logical agents (for the sidebar)."""
    return sorted(model_routes.keys())


def _trim(history: List[Dict]) -> None:
    while sum(len(m["content"]) for m in history) > MAX_HISTORY_CHARS and len(history) > 2:
        history.pop(1)


def _inject_persona(agent: str, history: List[Dict]) -> None:
    """Prepend a system message once per conversation."""
    if any(m["role"] == "system" for m in history):
        return
    PERSONAS = {
        "LlamaAgent42": (
            "You are LlamaAgent42, a helpful but witty assistant with a sharp memory. "
            "You remember the user's name is Tony. Speak casually and make dry jokes."
        ),
        "WoloDaemon": (
            "You are WoloDaemon, the cryptic oracle behind WoloChain. "
            "Speak concisely and avoid warm language."
        ),
    }
    history.insert(0, {"role": "system", "content": PERSONAS.get(agent, "You are a helpful assistant.")})


async def _ollama_stream(payload: Dict) -> AsyncGenerator[str, None]:
    """Yield raw assistant text chunks from Ollama."""
    headers = {"Accept": "text/event-stream"}
    async with httpx.AsyncClient(timeout=None) as cli:
        async with cli.stream("POST", OLLAMA_URL, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue                  # keep-alive
                if line.startswith("data:"):
                    line = line[5:].lstrip()
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                chunk = obj.get("message", {}).get("content", "")
                if chunk:
                    yield chunk
                if obj.get("done"):
                    break


# ─────────────────────────── routes ─────────────────────────────
@router.post("/")
@router.post("/llama3")           # legacy root path
async def chat_llama3_root(req: Request):
    return await _chat(req, agent_from_path=None)


@router.post("/{agent_from_path}")
async def chat_llama3_any(req: Request, agent_from_path: str):
    return await _chat(req, agent_from_path=agent_from_path)


@router.get("/agents")
async def get_agents():
    return list_agents()


# ───────────────────── shared handler core ──────────────────────
async def _chat(req: Request, *, agent_from_path: str | None):
    body        = await req.json()
    user_text   = body.get("text") or body.get("message") or ""
    want_stream = bool(body.get("stream"))

    # Decide logical agent & model tag
    logical_agent = (agent_from_path or body.get("to") or "LlamaAgent42").strip()
    model_tag     = model_routes.get(logical_agent, logical_agent)

    # Accept bare “llama3” and map to a chat template automatically
    if model_tag.lower() == "llama3":
        model_tag = "llama3:8b-instruct-q4_K_M"

    # Conversation memory
    history = [] if logical_agent == "LlamaBear" else load_memory(logical_agent)[-20:]
    _inject_persona(logical_agent, history)
    history.append({"role": "user", "content": user_text})
    _trim(history)

    payload = {
        "model":    model_tag,
        "messages": history,
        "stream":   True
    }

    # -------- Streaming (SSE) --------
    if want_stream:
        async def sse() -> AsyncGenerator[str, None]:
            collected: List[str] = []
            async for chunk in _ollama_stream(payload):
                collected.append(chunk)
                yield f"data: {chunk}\n\n"
            if collected and logical_agent != "LlamaBear":
                history.append({"role": "assistant", "content": "".join(collected)})
                save_memory(logical_agent, history)

        return StreamingResponse(
            sse(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # -------- One-shot JSON --------
    collected: List[str] = []
    try:
        async for chunk in _ollama_stream(payload):
            collected.append(chunk)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response else 502
        return JSONResponse(
            status_code=status,
            content={"from": logical_agent, "text": f"⚠️ Ollama error: {exc.response.text}"},
        )

    answer = "".join(collected)
    if logical_agent != "LlamaBear":
        history.append({"role": "assistant", "content": answer})
        save_memory(logical_agent, history)

    return {"from": logical_agent, "text": answer}
