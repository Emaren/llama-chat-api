"""
llama3_router.py — FastAPI ↔ LLM gateway (SSE + one-shot JSON)

• Chooses Ollama (local) or OpenAI (cloud) per `model_routes`
• Streams every token as *valid JSON* Server-Sent Events so the browser
  never receives a broken frame.
"""

from __future__ import annotations

import json
import os
from typing import AsyncGenerator, Dict, List

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent_models import model_routes
from app.memory import load_memory, save_memory

# ───────────────────────── settings ────────────────────────────
OLLAMA_URL        = "http://localhost:11434/api/chat"
MAX_HISTORY_CHARS = 12_000
EXCLUDE_MEMORY    = {"LlamaBear", "Agent4o"}          # no long-term memory
router = APIRouter()
# ────────────────────────────────────────────────────────────────


# ───────────────────────── helpers ──────────────────────────────
def list_agents() -> List[str]:
    return sorted(model_routes.keys())


def _trim(history: List[Dict]) -> None:
    """Keep chat history below MAX_HISTORY_CHARS."""
    while sum(len(m["content"]) for m in history) > MAX_HISTORY_CHARS and len(history) > 2:
        history.pop(1)


def _inject_persona(agent: str, history: List[Dict]) -> None:
    """Insert a system persona if one isn’t already present."""
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
    history.insert(
        0,
        {"role": "system", "content": PERSONAS.get(agent, "You are a helpful assistant.")},
    )


def _nonempty(chunk: str) -> bool:
    """True if the chunk has any non-whitespace characters."""
    return bool(chunk and chunk.strip())


# ───────────── low-level streaming to Ollama ──────────────
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
                chunk = obj.get("message", {}).get("content") or ""
                if chunk:
                    yield chunk
                if obj.get("done"):
                    break


# ───────────── low-level streaming to OpenAI ──────────────
async def _openai_stream(payload: Dict) -> AsyncGenerator[str, None]:
    import openai

    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "ollama"))
    response = await client.chat.completions.create(
        model=payload["model"],
        messages=payload["messages"],
        stream=True,
    )
    async for part in response:
        if part.choices:
            yield part.choices[0].delta.content or ""


# ────────────────────────── routes ─────────────────────────────
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


# ───────────── shared handler core ──────────────
async def _chat(req: Request, *, agent_from_path: str | None):
    body        = await req.json()
    user_text   = body.get("text") or body.get("message") or ""
    want_stream = bool(body.get("stream"))

    logical_agent = (agent_from_path or body.get("to") or "LlamaAgent42").strip()
    model_tag     = model_routes.get(logical_agent, logical_agent)

    # Default fallback
    if model_tag.lower() == "llama3":
        model_tag = "llama3:8b-instruct-q4_K_M"

    is_openai    = model_tag.startswith("openai:")
    actual_model = model_tag.split("openai:")[-1] if is_openai else model_tag

    # Build conversation history
    history = [] if logical_agent in EXCLUDE_MEMORY else load_memory(logical_agent)[-20:]
    _inject_persona(logical_agent, history)
    history.append({"role": "user", "content": user_text})
    _trim(history)

    payload = {"model": actual_model, "messages": history, "stream": True}
    gen     = _openai_stream(payload) if is_openai else _ollama_stream(payload)

    # ────────── streaming (SSE) branch ──────────
    if want_stream:

        async def json_sse() -> AsyncGenerator[bytes, None]:
            collected: List[str] = []
            async for chunk in gen:
                if not _nonempty(chunk):
                    continue  # ignore pure-whitespace deltas
                collected.append(chunk)
                frame = {"data": chunk, "done": False}
                yield f"data: {json.dumps(frame, ensure_ascii=False)}\n\n".encode()

            # final sentinel
            yield b'data: {"done": true}\n\n'

            if collected and logical_agent not in EXCLUDE_MEMORY:
                history.append({"role": "assistant", "content": "".join(collected)})
                save_memory(logical_agent, history)

        return StreamingResponse(
            json_sse(),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    # ────────── one-shot JSON branch ──────────
    collected: List[str] = []
    try:
        async for chunk in gen:
            if not _nonempty(chunk):
                continue
            collected.append(chunk)
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response else 502
        return JSONResponse(
            status, {"from": logical_agent, "text": f"⚠️ backend error: {exc.response.text}"}
        )
    except Exception as exc:
        return JSONResponse(
            500, {"from": logical_agent, "text": f"⚠️ backend error: {str(exc)}"}
        )

    answer = "".join(collected)
    if logical_agent not in EXCLUDE_MEMORY:
        history.append({"role": "assistant", "content": answer})
        save_memory(logical_agent, history)

    return {"from": logical_agent, "text": answer}
