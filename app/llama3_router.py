"""
llama3_router.py — FastAPI ↔ LLM bridge (Ollama or OpenAI)
"""

from __future__ import annotations
import json, os
from typing import AsyncGenerator, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.agent_models import model_routes
from app.memory       import load_memory, save_memory, trim_history
from app.loadouts     import LOADOUTS
from app.personas     import PERSONAS

from agents.chat_engine      import handle_chat
from agents.agent4_1m_core   import Agent4_1M

OLLAMA_URL        = os.getenv("OLLAMA_URL", "http://localhost:11434/api/chat")
EXCLUDE_MEMORY    = {"LlamaBear", "Agent4o"}
router            = APIRouter()


def list_agents() -> List[str]:
    return sorted(model_routes.keys())


@router.get("/agents")
async def agents():
    return list_agents()


@router.get("/messages/{agent}")
async def history(agent: str):
    raw = load_memory(agent)[-20:]
    shaped: List[Dict[str, str]] = []
    for m in raw:
        role = m.get("role")
        text = (m.get("content") or "").strip()
        if not text: continue
        shaped.append({
            "from": "me" if role == "user" else agent,
            "text": text,
        })
    return shaped


@router.get("/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=2) as c:
            ok = (await c.get(OLLAMA_URL.replace("/chat", "/tags"))).status_code == 200
    except httpx.RequestError:
        ok = False
    return {"ollama_up": ok}


def resolve_loadout(agent: str):
    loadout = LOADOUTS.get(agent)
    if loadout:
        return (
            loadout["persona"],
            model_routes.get(loadout["model"], loadout["model"]),
            loadout.get("tools", []),
        )
    return agent, model_routes.get(agent, agent), []


async def _ollama_stream(payload: Dict) -> AsyncGenerator[str, None]:
    headers = {"Accept": "text/event-stream"}
    try:
        async with httpx.AsyncClient(timeout=None) as cli, \
                   cli.stream("POST", OLLAMA_URL, json=payload, headers=headers) as resp:

            if resp.status_code == 404:
                raise RuntimeError("Ollama daemon not reachable")

            resp.raise_for_status()

            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"): continue
                try:
                    obj   = json.loads(line[5:].lstrip())
                    chunk = obj.get("message", {}).get("content") or ""
                    if chunk:
                        yield chunk
                    if obj.get("done"):
                        break
                except json.JSONDecodeError:
                    continue
    except (httpx.HTTPError, RuntimeError) as exc:
        raise HTTPException(502, str(exc)) from exc


async def _openai_stream(payload: Dict) -> AsyncGenerator[str, None]:
    import openai
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment.")

        client = openai.AsyncOpenAI(api_key=api_key)

        if "prompt" in payload:
            response = await client.responses.create(
                prompt=payload["prompt"],
                input=payload["input"],
            )
            yield response.output_text
            return

        response = await client.chat.completions.create(
            model=payload["model"],
            messages=payload["messages"],
            stream=True,
        )

        async for part in response:
            if part.choices:
                chunk = part.choices[0].delta.content or ""
                if isinstance(chunk, bytes):
                    chunk = chunk.decode("utf-8")
                yield chunk

    except Exception as e:
        print("🧠 [OPENAI STREAM ERROR]:", repr(e))
        raise HTTPException(status_code=500, detail=f"OpenAI Error: {str(e)}")


@router.post("/send")
async def chat(req: Request):
    body = await req.json()
    want_stream = bool(body.get("stream"))
    agent = (body.get("to") or "").strip()

    if not agent or agent not in model_routes:
        raise HTTPException(400, detail=f"Invalid or missing agent: {agent}")

    persona_tag, model_tag, tools = resolve_loadout(agent)

    if model_tag.lower() == "llama3":
        model_tag = "llama3:8b-instruct-q4_K_M"

    is_openai = model_tag.startswith("openai:")
    backend = _openai_stream if is_openai else _ollama_stream
    payload = {"stream": True}

    # Load prompt agent
    try:
        from importlib import import_module
        try:
            agent_module = import_module(f"agents.{agent.lower().replace('.', '_')}_core")
        except ModuleNotFoundError:
            agent_module = import_module(f"agents.{agent.lower().replace('.', '_')}")
        agent_class = getattr(agent_module, agent.replace(".", "_"))
        use_prompt = hasattr(agent_class, "prompt_id")
        prompt_class = agent_class if use_prompt else None
    except Exception as e:
        print("❌ Prompt agent import failed:", repr(e))
        use_prompt = False
        prompt_class = None

    if use_prompt:
        user_text = body.get("text") or body.get("message") or ""
        if not user_text.strip():
            raise HTTPException(400, detail="Missing message content.")
        payload["prompt"] = {
            "id": prompt_class.prompt_id,
            "version": prompt_class.prompt_version or "1"
        }
        payload["input"] = user_text

        # 🧠 Save user input for prompt agents
        if agent not in EXCLUDE_MEMORY:
            history = load_memory(agent)
            trim_history(history)
            history.append({ "role": "user", "content": user_text })
            save_memory(agent, history)

    else:
        if "messages" in body:
            history = body["messages"]
        else:
            user_text = body.get("text") or body.get("message") or ""
            if not user_text.strip():
                raise HTTPException(400, detail="Missing message content.")
            history = handle_chat(persona_tag, user_text)

            # 🧠 Save user input for regular chat agents
            if agent not in EXCLUDE_MEMORY:
                mem = load_memory(agent)
                trim_history(mem)
                mem.append({ "role": "user", "content": user_text })
                save_memory(agent, mem)

        if is_openai and not any(m["role"] == "system" for m in history):
            history.insert(0, {"role": "system", "content": persona_tag})

        payload["model"] = model_tag.split("openai:")[-1]
        payload["messages"] = history

    print("🛰️ [PAYLOAD SENT TO BACKEND]", json.dumps(payload, indent=2))

    if want_stream:
        async def sse():
            collected: List[str] = []
            try:
                async for chunk in backend(payload):
                    if chunk.strip():
                        collected.append(chunk)
                        text = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
                        yield f"data: {json.dumps({'data': text, 'done': False})}\n\n".encode()
            except HTTPException as exc:
                yield f"data: {json.dumps({'error': exc.detail, 'done': True})}\n\n".encode()
                return

            yield b'data: {"done": true}\n\n'

            if collected and agent not in EXCLUDE_MEMORY:
                history = load_memory(agent)
                trim_history(history)
                history.append({ "role": "assistant", "content": "".join(collected) })
                save_memory(agent, history)

        return StreamingResponse(
            sse(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    # fallback: full non-streaming answer
    try:
        answer_parts: List[str] = []
        async for ch in backend(payload):
            if ch.strip():
                answer_parts.append(ch)
        answer = "".join(answer_parts)
    except HTTPException as exc:
        return JSONResponse(exc.status_code, {"from": agent, "error": exc.detail})

    if agent not in EXCLUDE_MEMORY:
        history = load_memory(agent)
        trim_history(history)
        history.append({ "role": "assistant", "content": answer })
        save_memory(agent, history)

    return {"from": agent, "text": answer}
