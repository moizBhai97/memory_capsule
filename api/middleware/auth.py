"""
Optional API key auth middleware.
If MC_API_KEY is set in config, all requests must include it.
If not set, API is open (fine for local use).
"""

from fastapi import Header, HTTPException, status
from config import get_config


async def verify_api_key(x_api_key: str = Header(default="")):
    cfg = get_config()
    if not cfg.api.api_key:
        return  # No key configured = open access (local use)
    if x_api_key != cfg.api.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Set X-Api-Key header.",
        )
