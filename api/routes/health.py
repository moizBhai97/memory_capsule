from fastapi import APIRouter
from providers import get_llm, get_embed

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/health/providers")
async def health_providers():
    """Check which AI providers are reachable."""
    llm_ok = await get_llm().health_check()
    embed_ok = await get_embed().health_check()
    return {
        "llm": {"status": "ok" if llm_ok else "unreachable"},
        "embed": {"status": "ok" if embed_ok else "unreachable"},
    }
