from fastapi import APIRouter, Request
import httpx

router = APIRouter()

@router.post("/chat/llama3")
async def chat_with_llama3(req: Request):
    data = await req.json()
    user_input = data.get("text")

    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": user_input}],
        "stream": False
    }

    timeout = httpx.Timeout(60.0)  # ⏱️ increase timeout to 60 seconds

    async with httpx.AsyncClient(timeout=timeout) as client:
        res = await client.post("http://localhost:11434/api/chat", json=payload)
        output = res.json()
        return { "response": output["message"]["content"] }
