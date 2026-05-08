import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from state import ReviewState

# ── shared LLM instance ──────────────────────────────────────────────────────
_llm = ChatOpenAI(model="gpt-4o", temperature=0)

# ── prompts ─────────────────────
_BUG_PROMPT = """You are a bug detection specialist reviewing a PR diff.

Your ONLY job is to identify bugs: logic errors, null/undefined dereferences,
off-by-one errors, race conditions, unhandled exceptions, and similar defects
that cause incorrect runtime behavior.

Do NOT comment on style, naming conventions, or improvement suggestions.

Return a JSON array. Each item: {"file": str, "line": int|null, "description": str}
If no bugs found, return [].
Return only valid JSON — no prose, no markdown fences."""

_STYLE_PROMPT = """You are a style review specialist reviewing a PR diff.

Your ONLY job is to flag style violations: naming inconsistencies, formatting
issues, dead code, overly complex expressions, missing docstrings, and anything
that reduces readability — measured against common conventions for the language.

Do NOT report bugs or suggest architectural improvements.

Return a JSON array. Each item: {"file": str, "line": int|null, "description": str}
If no violations found, return [].
Return only valid JSON — no prose, no markdown fences."""

_IMPROVEMENT_PROMPT = """You are an improvement advisor reviewing a PR diff.

Your ONLY job is to suggest improvements to readability, maintainability, and
performance — things that are not bugs and not style violations: better
abstractions, missing edge-case handling, unnecessary complexity, performance
concerns.

Do NOT report bugs or flag style/convention issues.

Return a JSON array. Each item: {"file": str, "line": int|null, "description": str}
If no improvements needed, return [].
Return only valid JSON — no prose, no markdown fences."""

_SUMMARIZER_PROMPT = """You are a senior code reviewer writing a final summary.

You receive structured findings from three specialists and must produce:
1. A plain-English summary (2–4 sentences): what the PR does, its main risks,
   and whether it looks ready to merge.
2. A confidence score (integer 1–10) reflecting how thorough and reliable the
   review is. Use 9–10 for small, clear diffs; 7–8 for moderate complexity;
   below 7 for large or ambiguous diffs.

Return valid JSON only:
{"summary": "<text>", "score": <int>}
No prose, no markdown fences."""


# ── helpers ──────────────────────────────────────────────────────────────────
def _call(system: str, user: str) -> str:
    response = _llm.invoke(
        [SystemMessage(content=system), HumanMessage(content=user)]
    )
    return response.content


def _parse_json_list(raw: str) -> list[dict]:
    """Strip markdown fences and parse a JSON array defensively."""
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def _parse_json_object(raw: str) -> dict:
    """Strip markdown fences and parse a JSON object defensively."""
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except json.JSONDecodeError:
        return {}


# ── nodes ────────────────────────────────────────────────────────────────────
def bug_detector_node(state: ReviewState) -> dict:
    """Owns: bugs"""
    raw = _call(_BUG_PROMPT, state["diff"])
    return {"bugs": _parse_json_list(raw)}


def style_reviewer_node(state: ReviewState) -> dict:
    """Owns: style_violations"""
    raw = _call(_STYLE_PROMPT, state["diff"])
    return {"style_violations": _parse_json_list(raw)}


def improvement_advisor_node(state: ReviewState) -> dict:
    """Owns: suggestions"""
    raw = _call(_IMPROVEMENT_PROMPT, state["diff"])
    return {"suggestions": _parse_json_list(raw)}


def summarizer_node(state: ReviewState) -> dict:
    """Owns: summary, score, retry_count"""
    findings = json.dumps(
        {
            "bugs": state.get("bugs", []),
            "style_violations": state.get("style_violations", []),
            "suggestions": state.get("suggestions", []),
        },
        indent=2,
    )
    raw = _call(_SUMMARIZER_PROMPT, findings)
    parsed = _parse_json_object(raw)

    summary = parsed.get("summary", "")
    score = max(1, min(10, int(parsed.get("score", 5))))  # clamp to 1–10

    return {
        "summary": summary,
        "score": score,
        "retry_count": state.get("retry_count", 0) + 1,
    }
