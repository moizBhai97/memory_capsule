"""
Search endpoint — natural language queries over all capsules.
"""

from typing import Optional
from fastapi import APIRouter, Depends
from api.middleware.auth import verify_api_key
from api.main import get_search

router = APIRouter(dependencies=[Depends(verify_api_key)])


@router.get("")
async def search(
    q: str,
    limit: int = 10,
    source_app: Optional[str] = None,
    source_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
):
    """
    Natural language search over all captured memories.

    Examples:
    - /api/search?q=quote from Ahmed
    - /api/search?q=invoice last month&source_app=email
    - /api/search?q=meeting notes&from_date=2024-03-01
    - /api/search?q=project price 2 weeks ago
    """
    engine = get_search()
    results = await engine.search(
        query=q,
        limit=limit,
        source_app=source_app,
        source_type=source_type,
        from_date=from_date,
        to_date=to_date,
    )

    return {
        "query": q,
        "count": len(results),
        "results": [
            {
                "capsule": r.capsule.to_dict(),
                "score": r.score,
                "match_type": r.match_type,
                "snippet": r.snippet,
            }
            for r in results
        ],
    }
