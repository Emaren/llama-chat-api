"""
llama3_router.py — FastAPI ↔ LLM gateway (SSE + one-shot JSON)

Supports both Ollama and OpenAI APIs via logical agent routing.
"""

from __future__ import annotations

import json
import os
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
EXCLUDE_MEMORY        = {"LlamaBear", "Agent4o"}  # 🛡️ no memory for these

router = APIRouter()
# ─────────────────────────────────────────────────────────────────


# ────────────────────────── helpers ──────────────────────────────
def list_agents() -> List[str]:
    return sorted(model_routes.keys())


def _trim(history: List[Dict]) -> None:
    while sum(len(m["content"]) for m in history) > MAX_HISTORY_CHARS and len(history) > 2:
        history.pop(1)


def _inject_persona(agent: str, history: List[Dict]) -> None:
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
        "Agent4oM": (
            "You are Agent4oM, an OpenAI-powered assistant with long-term memory. "
            "You remember everything the user says, speak clearly, and give smart answers."
        ),
    }
    history.insert(0, {"role": "system", "content": PERSONAS.get(agent, "You are a helpful assistant.")})


async def _ollama_stream(payload: Dict) -> AsyncGenerator[str, None]:
    headers = {"Accept": "text/event-stream"}
    async with httpx.AsyncClient(timeout=None) as cli:
        async with cli.stream("POST", OLLAMA_URL, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
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


async def _openai_stream(payload: Dict) -> AsyncGenerator[str, None]:
    import openai
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    client = openai.AsyncOpenAI()
    model = payload["model"]
    messages = payload["messages"]
    response = await client.chat.completions.create(model=model, messages=messages, stream=True)
    async for chunk in response:
        if chunk.choices:
            yield chunk.choices[0].delta.content or ""
# ─────────────────────────────────────────────────────────────────


# ─────────────────────────── routes ─────────────────────────────
@router.post("/")
@router.post("/llama3")
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

    logical_agent = (agent_from_path or body.get("to") or "LlamaAgent42").strip()
    model_tag     = model_routes.get(logical_agent, logical_agent)

    # Default fallback
    if model_tag.lower() == "llama3":
        model_tag = "llama3:8b-instruct-q4_K_M"

    is_openai = model_tag.startswith("openai:")
    actual_model = model_tag.split("openai:")[-1] if is_openai else model_tag

    # Only load memory if agent is not excluded
    history = [] if logical_agent in EXCLUDE_MEMORY else load_memory(logical_agent)[-20:]
    _inject_persona(logical_agent, history)
    history.append({"role": "user", "content": user_text})
    _trim(history)

    payload = {
        "model": actual_model,
        "messages": history,
        "stream": True
    }

    gen = _openai_stream(payload) if is_openai else _ollama_stream(payload)

    # ────────── Streamed mode (SSE) ──────────
    if want_stream:
        async def sse() -> AsyncGenerator[str, None]:
            collected: List[str] = []
            async for chunk in gen:
                collected.append(chunk)
                yield f"data: {chunk}\n\n"
            if collected and logical_agent not in EXCLUDE_MEMORY:
                history.append({"role": "assistant", "content": "".join(collected)})
                save_memory(logical_agent, history)

        return StreamingResponse(
            sse(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # ────────── JSON response mode ──────────
    collected: List[str] = []
    try:
        async for chunk in gen:
            collected.append(chunk)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response else 502
        return JSONResponse(
            status_code=status,
            content={"from": logical_agent, "text": f"⚠️ Ollama error: {exc.response.text}"},
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"from": logical_agent, "text": f"⚠️ OpenAI error: {str(exc)}"},
        )

    answer = "".join(collected)
    if logical_agent not in EXCLUDE_MEMORY:
        history.append({"role": "assistant", "content": answer})
        save_memory(logical_agent, history)

    return {"from": logical_agent, "text": answer}

