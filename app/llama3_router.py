"""
llama3_router.py — FastAPI ↔ LLM bridge (Ollama / OpenAI)
──────────────────────────────────────────────────────────
Works with openai-py ≥ 1.9 (no prompt= arg)
• master prompt injected as first system msg
• persona injection & JSON memory
• SSE streaming intact (via Prompt-Mgmt)
• dashboard token callback
"""
from __future__ import annotations

import asyncio
import json
import os
from importlib import import_module
from typing import AsyncGenerator, Dict, List, Optional

import httpx
import tiktoken
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent_models import model_routes
from app.loadouts     import LOADOUTS
from app.memory       import load_memory, save_memory, trim_history
from agents.chat_engine import handle_chat

# ─────────────────── config / constants ────────────────────
OLLAMA_URL     = os.getenv("OLLAMA_URL",    "http://localhost:11434/api/chat")
DASH_API_URL   = os.getenv("DASH_API_URL",  "http://localhost:8005")
EXCLUDE_MEMORY = {"LlamaBear", "Agent4o"}

router = APIRouter()

# ────────────────────── helpers ─────────────────────────────
def _count_tokens(txt: str, model: str) -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(txt or ""))


def _sanitize_agent_reply(txt: str) -> str:
    return (txt or "").replace("—", ",").replace("–", ",").strip()


def _looks_like_prompt_metadata_question(txt: str) -> bool:
    lower = (txt or "").lower()
    needles = (
        "what prompt",
        "which prompt",
        "prompt version",
        "prompt v",
        "prompt number",
        "what model",
        "which model",
        "model are you",
        "what version",
    )
    return any(needle in lower for needle in needles)


def _format_agent_metadata_reply(
    agent: str,
    model: str,
    prompt_id: Optional[str],
    prompt_version: Optional[str],
) -> str:
    parts = [agent]
    if prompt_version:
        parts.append(f"prompt v{prompt_version}")
    elif prompt_id:
        parts.append("prompt version unknown")
    parts.append(f"model {model}")
    if prompt_id:
        parts.append(f"prompt_id {prompt_id}")
    return ", ".join(parts) + "."


def _build_openai_prompt_request(messages: List[Dict]) -> Dict:
    req: Dict = {"input": ""}
    instructions: List[str] = []
    transcript: List[str] = []
    prompt_tag_seen = False

    for msg in messages:
        role = (msg.get("role") or "").strip()
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        if not prompt_tag_seen and role == "system":
            prompt_tag_seen = True
            if content.startswith("<prompt:") and content.endswith(">"):
                parts = content.strip("<>").split(":")
                if len(parts) == 3 and parts[1] and parts[2]:
                    req["prompt"] = {"id": parts[1], "version": parts[2]}
                    continue
            instructions.append(content)
            continue

        if role == "system":
            instructions.append(content)
        elif role == "assistant":
            transcript.append(f"Assistant: {content}")
        else:
            transcript.append(f"User: {content}")

    if instructions:
        req["instructions"] = "\n\n".join(instructions)
    if transcript:
        req["input"] = "\n".join(transcript)
    return req

async def _push_usage(p: int, c: int, model: str, usd: float):
    try:
        async with httpx.AsyncClient(timeout=3) as c_:
            await c_.post(
                f"{DASH_API_URL}/api/chat/stats/update",
                json={
                    "prompt_tokens": p,
                    "completion_tokens": c,
                    "model_name":     model,
                    "cost_usd":       round(usd, 6),
                },
            )
    except Exception as e:
        print("⚠️  push_usage failed:", e)


# ─────────── back-end stream adapters ────────────
async def _openai_stream(payload: dict) -> AsyncGenerator[str, None]:
    import openai
    from openai import OpenAIError

    client = openai.AsyncOpenAI()
    try:
        openai_req = _build_openai_prompt_request(payload["messages"])
        if "prompt" not in openai_req:
            openai_req["model"] = payload["model"]
        openai_req["stream"] = True
        stream = await client.responses.create(**openai_req)

        async for ev in stream:
            # Each Prompt-Mgmt stream event now has `.text`
            text = getattr(ev, "text", None)
            if text is not None:
                yield text
            await asyncio.sleep(0)

    except OpenAIError as e:
        # map to 502 so the UI sees an error and closes
        raise HTTPException(502, f"OpenAI error: {e}") from e

    except Exception as e:
        # catch anything else and terminate cleanly
        print("⚠️ unexpected error in _openai_stream:", e)
        raise HTTPException(500, "internal stream error") from e


async def _ollama_stream(payload: dict) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient(timeout=None) as c:
        async with c.stream("POST", OLLAMA_URL, json=payload) as r:
            async for raw in r.aiter_lines():
                if not raw.strip():
                    continue
                try:
                    yield json.loads(raw)["message"]["content"]
                except Exception:
                    print("⚠️  bad Ollama chunk:", raw[:100])


# ─────────── loadouts / personas ───────────
def _resolve(agent: str):
    if agent in LOADOUTS:
        ld = LOADOUTS[agent]
        return ld["persona"], model_routes.get(ld["model"], ld["model"])
    return agent, model_routes.get(agent, agent)


# ───────────────────────── endpoints ────────────────────────
@router.get("/agents")
async def agents():
    return sorted(model_routes.keys())


@router.get("/messages/{agent}")
async def history(agent: str, limit: int = 50):
    raw = load_memory(agent)[-limit:]
    return [
        {"from": "me" if m["role"] == "user" else agent, "text": m["content"].strip()}
        for m in raw if m.get("content")
    ]


# ───────────────────────── main /send ───────────────────────
@router.post("/send")
async def chat(req: Request):
    body        = await req.json()
    want_stream = bool(body.get("stream"))
    agent       = (body.get("to") or "").strip()

    # 1️⃣ validate + resolve agent/model
    if agent not in model_routes:
        raise HTTPException(400, f"invalid agent {agent}")
    persona, model_alias = _resolve(agent)
    is_openai            = model_alias.startswith("openai:")
    model                = model_alias.split(":", 1)[1] if is_openai else model_alias
    backend              = _openai_stream if is_openai else _ollama_stream

    # 2️⃣ assemble messages
    if "messages" in body:
        messages  = body["messages"]
        user_text = messages[-1]["content"] if messages else ""
    else:
        user_text = (body.get("text") or body.get("message") or "").strip()
        if not user_text:
            raise HTTPException(400, "missing text")
        messages = handle_chat(persona, user_text)

    # 3️⃣ master-prompt injection
    sys_prompt_txt: Optional[str] = None
    prompt_id: Optional[str] = None
    prompt_version: Optional[str] = None
    try:
        mod_name = f"agents.{agent.lower().replace('.', '_')}_core"
        core_mod = import_module(mod_name)
        core_cls = getattr(core_mod, agent.replace(".", "_"))
        pid      = getattr(core_cls, "prompt_id", None)
        if pid:
            prompt_id      = str(pid)
            prompt_version = str(getattr(core_cls, "prompt_version", "1"))
            sys_prompt_txt = f"<prompt:{prompt_id}:{prompt_version}>"
            print(f"[debug] {agent} injecting master prompt {sys_prompt_txt}")
    except Exception:
        pass

    # 4️⃣ ensure first message is system
    if sys_prompt_txt:
        if not messages or messages[0].get("content") != sys_prompt_txt:
            messages.insert(0, {"role": "system", "content": sys_prompt_txt})
    elif is_openai and (not messages or messages[0]["role"] != "system"):
        messages.insert(0, {"role": "system", "content": persona})

    # 5️⃣ build payload
    payload: Dict = {"model": model, "messages": messages}
    if want_stream and not is_openai:
        payload["stream"] = True

    # persist user → memory
    if agent not in EXCLUDE_MEMORY and user_text:
        mem = load_memory(agent)
        trim_history(mem)
        mem.append({"role": "user", "content": user_text})
        save_memory(agent, mem)

    async def _finalise(reply: str):
        if reply and agent not in EXCLUDE_MEMORY:
            mem = load_memory(agent)
            trim_history(mem)
            mem.append({"role": "assistant", "content": reply})
            save_memory(agent, mem)
        if is_openai and reply:
            p = _count_tokens(user_text, model)
            c = _count_tokens(reply, model)
            asyncio.create_task(_push_usage(p, c, model, (p + c) / 1000 * 0.005))

    if _looks_like_prompt_metadata_question(user_text):
        reply = _sanitize_agent_reply(
            _format_agent_metadata_reply(agent, model, prompt_id, prompt_version)
        )
        await _finalise(reply)
        return {
            "from": agent,
            "text": reply,
            "metadata": {
                "agent": agent,
                "model": model,
                "prompt_id": prompt_id,
                "prompt_version": prompt_version,
            },
        }

    # ── streaming path ──────────────────────────────────────────
    if want_stream:
        async def sse():
            buf: List[str] = []
            try:
                async for ch in backend(payload):
                    if ch.strip():
                        clean_ch = ch.replace("—", ",").replace("–", ",")
                        buf.append(clean_ch)
                        yield f"data: {json.dumps({'data': clean_ch, 'done': False})}\n\n".encode()
            except HTTPException as e:
                yield f"data: {json.dumps({'error': str(e.detail), 'done': True})}\n\n".encode()
                return
            # close out
            yield b'data: {"done": true}\n\n'
            await _finalise("".join(buf))

        return StreamingResponse(
            sse(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # ── blocking path ──────────────────────────────────────────
    parts: List[str] = []
    try:
        if is_openai:
            import openai
            client = openai.AsyncOpenAI()
            openai_req = _build_openai_prompt_request(payload["messages"])
            if "prompt" not in openai_req:
                openai_req["model"] = payload["model"]
            openai_req["stream"] = False
            resp = await client.responses.create(**openai_req)
            parts.append(resp.output[0].content[0].text)
        else:
            async for ch in backend(payload):
                if ch.strip():
                    parts.append(ch)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"from": agent, "error": e.detail})

    reply = _sanitize_agent_reply("".join(parts))
    await _finalise(reply)
    return {"from": agent, "text": reply}
