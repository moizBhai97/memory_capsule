"""
Hybrid search engine — combines semantic (vector) + keyword (FTS5) search.
User queries in plain English. We handle the rest.

Future: wrap this as an MCP tool so Claude/ChatGPT can query user's memory directly.
"""

import logging
from dataclasses import dataclass
from typing import Optional

from capsule.models import Capsule
from capsule.store.sqlite import SQLiteStore
from capsule.store.vector import VectorStore
from capsule.search.nlp_date import parse_date_range
from providers import get_embed

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    capsule: Capsule
    score: float          # 0.0 to 1.0
    match_type: str       # "semantic", "keyword", "hybrid"
    snippet: str          # relevant excerpt for display


class SearchEngine:
    def __init__(self, sqlite: SQLiteStore, vector: VectorStore):
        self.sqlite = sqlite
        self.vector = vector

    async def search(
        self,
        query: str,
        limit: int = 10,
        source_app: Optional[str] = None,
        source_type: Optional[str] = None,
        from_date: Optional[str] = None,   # ISO date string (overrides NLP)
        to_date: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Main search entry point.
        Parses natural language dates, runs hybrid search, returns ranked results.
        """
        if not query.strip():
            return []

        # Parse date expressions from query
        nlp_from, nlp_to, cleaned_query = parse_date_range(query)
        effective_from = from_date or nlp_from
        effective_to = to_date or nlp_to

        if nlp_from:
            logger.info(f"Date range detected: {effective_from} → {effective_to}")

        if not cleaned_query.strip():
            # Query was purely a date expression — return recent capsules in range
            capsules = self.sqlite.list(
                limit=limit,
                from_date=effective_from,
                to_date=effective_to,
                source_app=source_app,
                source_type=source_type,
            )
            return [SearchResult(c, 1.0, "date_filter", _snippet(c)) for c in capsules]

        # Run semantic and keyword search in parallel
        semantic_results = await self._semantic_search(
            cleaned_query, limit * 2, effective_from, effective_to, source_app
        )
        keyword_results = self._keyword_search(
            cleaned_query, limit * 2, effective_from, effective_to, source_app
        )

        # Merge and re-rank
        merged = _reciprocal_rank_fusion(semantic_results, keyword_results)

        # Apply type filter post-merge
        if source_type:
            merged = [r for r in merged if r.capsule.source_type.value == source_type]

        return merged[:limit]

    async def _semantic_search(
        self, query: str, limit: int,
        from_date=None, to_date=None, source_app=None
    ) -> list[SearchResult]:
        embed = get_embed()
        query_embedding = await embed.embed(query)

        # Build ChromaDB where filter
        where = {}
        if source_app:
            where["source_app"] = {"$eq": source_app}
        if from_date:
            where["timestamp"] = {"$gte": from_date}

        vector_results = self.vector.search(
            query_embedding=query_embedding,
            limit=limit,
            where=where if where else None,
        )

        results = []
        for vr in vector_results:
            capsule = self.sqlite.get(vr["id"])
            if capsule and _in_date_range(capsule, from_date, to_date):
                results.append(SearchResult(
                    capsule=capsule,
                    score=vr["score"],
                    match_type="semantic",
                    snippet=_snippet(capsule),
                ))

        return results

    def _keyword_search(
        self, query: str, limit: int,
        from_date=None, to_date=None, source_app=None
    ) -> list[SearchResult]:
        rows = self.sqlite.keyword_search(
            query=query,
            limit=limit,
            from_date=from_date,
            to_date=to_date,
            source_app=source_app,
        )
        return [
            SearchResult(capsule=c, score=abs(rank), match_type="keyword", snippet=_snippet(c))
            for c, rank in rows
        ]


def _reciprocal_rank_fusion(
    semantic: list[SearchResult],
    keyword: list[SearchResult],
    k: int = 60,
) -> list[SearchResult]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.
    Gives good results without needing to tune weights.
    """
    scores: dict[str, float] = {}
    capsules: dict[str, Capsule] = {}
    snippets: dict[str, str] = {}

    for rank, result in enumerate(semantic):
        cid = result.capsule.id
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
        capsules[cid] = result.capsule
        snippets[cid] = result.snippet

    for rank, result in enumerate(keyword):
        cid = result.capsule.id
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
        capsules[cid] = result.capsule
        snippets[cid] = result.snippet

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    return [
        SearchResult(
            capsule=capsules[cid],
            score=round(scores[cid], 4),
            match_type="hybrid",
            snippet=snippets[cid],
        )
        for cid in sorted_ids
    ]


def _in_date_range(capsule: Capsule, from_date: str, to_date: str) -> bool:
    if not from_date and not to_date:
        return True
    ts = capsule.timestamp.isoformat()
    if from_date and ts < from_date:
        return False
    if to_date and ts > to_date:
        return False
    return True


def _snippet(capsule: Capsule, max_len: int = 200) -> str:
    """Best short excerpt to show in search results."""
    if capsule.summary:
        return capsule.summary[:max_len]
    if capsule.raw_content:
        return capsule.raw_content[:max_len] + ("..." if len(capsule.raw_content) > max_len else "")
    return ""
