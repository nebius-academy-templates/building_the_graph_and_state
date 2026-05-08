import operator
from typing import Annotated, TypedDict


class ReviewState(TypedDict):
    # ── input ────────────────────────────────────────────────────────────────
    diff: str

    # ── output fields ────────────────────────────────────────────────────────
    bugs: Annotated[list[dict], operator.add]
    style_violations: Annotated[list[dict], operator.add]
    suggestions: Annotated[list[dict], operator.add]

    summary: str
    score: int

    # ── loop control ─────────────────────────────────────────────────────────
    retry_count: int
