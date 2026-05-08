import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from graph import compiled_graph  # noqa: E402

BUGGY = Path("diffs/buggy.diff").read_text()
CLEAN = Path("diffs/clean.diff").read_text()

SEP = "\n" + "=" * 60 + "\n"


def run(label: str, diff: str) -> None:
    print(SEP + f"RUN — {label}" + SEP)

    initial_state = {
        "diff": diff,
        "bugs": [],
        "style_violations": [],
        "suggestions": [],
        "summary": "",
        "score": 0,
        "retry_count": 0,
    }

    final_state: dict = {}

    # stream_mode="updates" → one dict per node showing only what changed
    for step in compiled_graph.stream(initial_state, stream_mode="updates"):
        node_name, updates = next(iter(step.items()))
        keys = list(updates.keys())
        print(f"  ✓ {node_name} wrote: {keys}")
        final_state.update(updates)

    print(f"\n  score={final_state.get('score')}  "
          f"retry_count={final_state.get('retry_count')}")
    print("\n  FINAL REVIEW")
    print(json.dumps(
        {
            "bugs": final_state.get("bugs", []),
            "style_violations": final_state.get("style_violations", []),
            "suggestions": final_state.get("suggestions", []),
            "summary": final_state.get("summary", ""),
            "score": final_state.get("score"),
        },
        indent=2,
    ))


run("buggy diff", BUGGY)
run("clean diff", CLEAN)
