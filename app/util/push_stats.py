import os, logging, httpx

DASHBOARD = os.getenv("LLAMA_DASH_URL", "http://127.0.0.1:8005")
log       = logging.getLogger(__name__)

async def push_usage(stats: dict) -> None:
    """
    Fire-and-forget stat push; never block the main request path.
    """
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            await c.post(f"{DASHBOARD}/api/chat/stats/update", json=stats)
    except Exception as exc:
        log.warning("⚠️  usage push failed: %s", exc)
