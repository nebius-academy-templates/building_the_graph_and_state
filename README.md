In this task, you'll extend the level 4 code review agent. You'll modify all three core primitives you've learned: state, a node, and a conditional edge:

1. Extend the shared **state** with a new `security_issues` field so findings accumulate the same way `bugs`, `style_violations`, and `suggestions` already do.
2. Add a new **security auditor node** that scans the PR diff for vulnerabilities and writes into that field before the summary is produced.
3. Wire a new **conditional edge** that blocks the review pipeline when security issues are found, preventing the summarizer from running at all.

## 👩‍💻Workflow at a glance
1. Confirm the project is working
2. Add the state field
3. Implement the security auditor node
4. Add the security gate condition
5. Rewire the graph
6. Run and verify both branches
7. Submit your task


## 1. Confirm the project is working

⚠️ This task uses an LLM provider.

The default setup uses OpenAI. If you have an OpenAI API key, add it to `**level_4/.env**`:

`OPENAI_API_KEY=sk-...your-key-here...`

If you do not have an OpenAI API key, you can still complete the task by switching the project to another LangChain chat model provider.

Recommended **no-cost** options:

- **Groq** — hosted API with a free plan and OpenAI-compatible endpoint. Good option if you want the smallest code change.
- **Google Gemini** — hosted API with a free developer tier. Good option if you already use Google AI Studio.
- **Ollama** — local model runner. You need to install the runner, as well as any models you want to use, and need to have enough local machine resources to run them.

To switch providers, update the model setup in `nodes.py` and add the matching dependency to `requirements.txt`.


### Repository check

Make sure the repository **`building_graph_and_state`** appears in your GitHub.

From the project root, activate your virtual environment and run:

```
python main.py
```

You should see two runs stream through — one for `buggy.diff` and one for `clean.diff` — each printing a node sequence ending with `summarizer wrote: ['summary', 'score', 'retry_count']`.

If any errors appear, fix them before continuing.

### Repository layout

```
building_the_graph_and_state/
├── diffs/
│   ├── buggy.diff          ← auth code with security issues
│   └── clean.diff          ← email helper, no security issues
├── graph.py                ← TODO: add security_gate + rewire (Tasks 4 & 5)
├── nodes.py                ← TODO: add security_auditor_node (Task 3)
├── state.py                ← TODO: add security_issues field (Task 2)
├── main.py                 ← TODO: update initial_state (Task 2)
└── requirements.txt
```

## 2. Add the state field

Open `state.py` and add one new field to `ReviewState` in the `# ── output fields ──` section alongside `bugs`, `style_violations`, and `suggestions`:

```python
security_issues: Annotated[list[dict], operator.add]
```

This follows the same pattern as the other specialist fields — each run of the node appends its findings without overwriting previous ones.

Then open `main.py` and add the field to `initial_state`:

```python
"security_issues": [],
```

Also add `"security_issues"` to the `json.dumps` call at the bottom of `run()` so the field appears in the printed output.

## 3. Implement the security auditor node

Open `nodes.py` and add a new prompt constant and a new node function.

### The prompt

Add a `_SECURITY_PROMPT` constant. It should:

- Give the LLM a single role: "security auditor reviewing a PR diff"
- Restrict it to only report security vulnerabilities:
    - Hardcoded secrets or credentials
    - Injection vectors (SQL, command, path traversal)
    - Broken cryptographic algorithms (MD5, SHA-1 for passwords)
    - Authentication or authorization bypasses
    - Unsafe deserialization
- Instruct it **not** to report bugs, style issues, or general improvements
- Request a JSON array with the same item shape as the other specialists: `{"file": str, "line": int|null, "description": str}`
- Return `[]` if no issues are found
- Return only valid JSON — no prose or markdown fences

### The node function

Add `security_auditor_node(state: ReviewState) -> dict`:

- Call `_call(_SECURITY_PROMPT, state["diff"])`
- Parse the result with `_parse_json_list`
- Return `{"security_issues": <parsed list>}`

Use `style_reviewer_node` as your reference — the structure is identical.

## 4. Add the security gate condition

Open `graph.py` and add a `security_gate` function above `build_graph`.

### Routing logic

| Condition | Return value |
| --- | --- |
| `security_issues` is non-empty | `"END"` |
| `security_issues` is empty | `"summarizer"` |

When the gate returns `"END"`, the graph stops immediately — the summarizer never runs and no score is written. This is the block branch.

## 5. Rewire the graph

In `build_graph`, make the following changes:

1. Import `security_auditor_node` at the top of `graph.py` alongside the other node imports.
2. Register the new node — add `graph.add_node("security_auditor", security_auditor_node)` alongside the other nodes.
3. Replace the direct edge from `improvement_advisor` to `summarizer` with a two-step sequence:
    - Direct edge: `improvement_advisor → security_auditor`
    - Conditional edge: `security_auditor → security_gate`
4. Wire the conditional edge from `security_auditor` using `security_gate`, mapping both outcomes:
    
    ```python
    graph.add_conditional_edges(
        "security_auditor",
        security_gate,
        {
            "END": END,
            "summarizer": "summarizer",
        },
    )
    ```
    

### Expected graph shape

```mermaid

flowchart TD
    A([START]) --> B[bug_detector]
    B --> C[style_reviewer]
    C --> D[improvement_advisor]
    D --> E[security_auditor]

    E -->|"security_gate issues found"| F([END — blocked])
    E -->|"security_gate no issues"| G[summarizer]

    G -->|"quality_router score ≥ 8"| H([END])
    G -->|"quality_router score < 8 retry_count < 2"| B

```

## 6. Run and verify both branches

Run the agent:

```
python main.py
```

### Expected result — buggy diff

`buggy.diff` contains auth code that uses MD5 for password hashing and a middleware that does not block unauthenticated requests. The security auditor should catch both.

Expected node sequence:

```
  ✓ bug_detector wrote: ['bugs']
  ✓ style_reviewer wrote: ['style_violations']
  ✓ improvement_advisor wrote: ['suggestions']
  ✓ security_auditor wrote: ['security_issues']
```

The `summarizer` node should not appear. The printed score should be `0` (never written).

### Expected result — clean diff

`clean.diff` adds a well-structured email helper with no secrets or dangerous patterns. The security auditor should return an empty list, and the pipeline should continue normally.

Expected node sequence:

```
  ✓ bug_detector wrote: ['bugs']
  ✓ style_reviewer wrote: ['style_violations']
  ✓ improvement_advisor wrote: ['suggestions']
  ✓ security_auditor wrote: ['security_issues']
  ✓ summarizer wrote: ['summary', 'score', 'retry_count']
```

The `summarizer` node should appear, and a non-zero score should be printed.


## 7. Submit your task

Before submitting, review the checklist.

### ✅ Submission checklist

- [ ]  `state.py` — `security_issues: Annotated[list[dict], operator.add]` added to `ReviewState`
- [ ]  `main.py` — `"security_issues": []` added to `initial_state`
- [ ]  `main.py` — `"security_issues"` included in the final `json.dumps` output
- [ ]  `nodes.py` — `_SECURITY_PROMPT` defined and scoped to security vulnerabilities only
- [ ]  `nodes.py` — `security_auditor_node` implemented, returns `{"security_issues": [...]}`
- [ ]  `graph.py` — `security_gate` condition implemented with two return values: `"END"` and `"summarizer"`
- [ ]  `graph.py` — `security_auditor` node registered in `build_graph`
- [ ]  `graph.py` — `improvement_advisor → security_auditor` direct edge added
- [ ]  `graph.py` — `security_auditor` conditional edge wired with `security_gate`
- [ ]  `python main.py` runs without errors
- [ ]  `buggy.diff` run: `summarizer` does **not** appear in the output
- [ ]  `clean.diff` run: `summarizer` **does** appear and prints a non-zero score
- [ ]  Changes are committed and pushed to `main`

### Submit the task

1. Commit your changes.
2. Push to GitHub.
3. Return to the lesson and click "Submit."
