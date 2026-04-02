"""
Shared API state — initialized once during lifespan, read by route handlers.
Keeping this separate from api.main breaks the circular import that would
otherwise require routes to be imported after app creation.
"""

from capsule.pipeline import Pipeline
from capsule.search.engine import SearchEngine
from capsule.store.sqlite import SQLiteStore

_state: dict = {}


def init(sqlite: SQLiteStore, pipeline: Pipeline, search: SearchEngine) -> None:
    _state["sqlite"] = sqlite
    _state["pipeline"] = pipeline
    _state["search"] = search


def get_pipeline() -> Pipeline:
    return _state["pipeline"]


def get_search() -> SearchEngine:
    return _state["search"]


def get_sqlite() -> SQLiteStore:
    return _state["sqlite"]
