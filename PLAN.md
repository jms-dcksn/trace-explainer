# Trace Explainer

An automated narrative writer for AI agent traces. Structured narratives (goal, steps taken, decisions made, summary) give a business SME enough context to meaningfully approve or reject an agent's output.

---

## Exercise Sequence

### Exercise 1: Build a Real Agent  [DONE]

**Goal**: Replace the stub in `main.py` with a proper multi-step LangChain agent.

**Status**: Complete. `main.py` now runs an account research agent with two tools:
- `web_search` (Tavily) for public/external info
- `lookup_account` against an in-memory `ACCOUNTS_DB` of mock CRM records (Acme Corp, Globex, Initech)

Default task: "Build me an account brief on Acme Corp" -- forces both tools to fire and produces a multi-step trace suitable for Exercise 2.

ReAct learning objectives skipped intentionally (already familiar).

---

### Exercise 2: Build the Capture Middleware  [DONE]

**Goal**: Capture every meaningful event from the agent run into a normalized intermediate format -- the contract between the capture layer and the explainer.

**Status**: Complete. `CaptureMiddleware` in `main.py` implements `after_model` (emits `agent_thought` + `tool_call` events, or `final_answer` when no tool calls) and `wrap_tool_call` (emits `tool_result` and packages the `ToolMessage` plus trace event into a single `Command` update). Trace lives on a `TraceState(AgentState)` subclass under a `trace` key with an `operator.add` reducer. `test_capture.py` runs the full path against a `FakeMessagesListChatModel` -- no OpenAI/Tavily creds needed -- and exercises the empty-content tool-call branch, the thought+tool-call branch, and the final-answer branch.

**Approach used**: LangChain's agent middleware (`langchain.agents.middleware`), not the legacy `BaseCallbackHandler`. Middleware is the supported path for `create_agent` going forward, gives typed inputs (`AgentState`, `ModelRequest`, `ModelResponse`) instead of a nested run tree, and lets the capture buffer live on agent state rather than handler instance attributes.

**What was built**:
- Three hooks: `after_model` (capture agent thoughts and tool-call decisions from the latest `AIMessage`), `wrap_tool_call` (capture tool input/output around `handler(request)`), and detect the final answer when `after_model` produces an `AIMessage` with no tool calls.
- Events stored on a custom `AgentState` subclass via `Command(update=...)` from `wrap_tool_call`, so the trace co-locates with the messages list (useful for Exercise 4).
- Normalized intermediate format:

```json
[
  {"step": 1, "type": "agent_thought", "content": "..."},
  {"step": 2, "type": "tool_call", "tool": "...", "input": "..."},
  {"step": 3, "type": "tool_result", "tool": "...", "output": "..."},
  {"step": 4, "type": "final_answer", "content": "..."}
]
```

This JSON is the stable contract. The explainer prompt in Exercise 3 is written against this format, not against raw middleware payloads -- which means swapping in a different capture source later (e.g., LangSmith, OTEL) only requires producing the same JSON.

**Learning objective**: Understand what middleware hooks expose at each lifecycle point, what carries real signal vs. noise, and what has to be inferred (e.g., distinguishing "thought" from "tool decision" in a single `AIMessage`).

**Questions to answer after**:
- Which fields did you have to infer vs. read directly from the middleware inputs?
- What's missing that you'd want a narrator to know?

**Follow-up to explore (deferred)**: When the model emits an `AIMessage` with tool calls and *no* text content, the `after_model` hook has no real "thought" to capture -- we currently fall back to a synthetic placeholder (`"(no commentary) decided to call: <tool>"`). An intermediate LLM call that summarizes the prior messages into the implied reasoning would produce a richer `agent_thought` event, but it adds latency, cost, and a second model dependency to every tool-call step. Worth A/B-testing in Exercise 4 (does it improve narrative quality enough to justify the spend?), not worth doing by default.

---

### Exercise 3: Write the Narrative  [DONE]

**Implemented as a standalone module (`narrator.py`), not middleware.** Rationale: the intermediate JSON contract from Exercise 2 is the whole point -- the narrator must be independent of capture source so Exercises 4 (messages-list input), 6 (LangSmith), and 7 (OTEL) can reuse it. `narrate(task, trace) -> Narrative` is wired into `main.py` after `agent.invoke(...)`.

**Goal**: Feed the aggregated trace to a second LLM call to produce a structured narrative.

**What to build**:
- Define a `Narrative` schema with four sections:
  - `goal`: what the agent was asked to do
  - `steps_taken`: ordered list of actions and tool calls
  - `decisions_made`: key reasoning choices the agent made (why it picked one tool over another, why it stopped, etc.)
  - `summary`: plain-English conclusion and final output
- Write a system prompt that instructs the narrator LLM to produce this from the raw trace
- Use structured output (Pydantic model + `.with_structured_output()`) so the result is machine-readable, not just text

**Learning objective**: Prompt engineering for trace-to-narrative translation. Understanding what structure makes a narrative useful vs. just verbose.

**Questions to answer after**:
- Does the narrative accurately represent what the agent actually did?
- Are the "decisions made" genuinely decision-like, or just restating steps?

---

### Exercise 4: The Comparison Experiment  [IN PROGRESS]

**Goal**: Produce the same narrative from the agent's message history and compare it to the middleware-captured trace.

**What to build**:
- After the agent run, extract the full messages list from the agent's state
- Feed to the same narrator LLM with the same `Narrative` schema and a similar prompt
- Run both approaches against 3-5 different tasks
- For each run, record: narrative quality (manual review), token count, latency, accuracy vs. what actually happened

**Learning objective**: Empirical answer to the structured-trace-vs-context-window question. The hypothesis is that the middleware-captured trace is more precise (structured, ordered, decision-typed) but the raw messages list is richer in reasoning (full chain-of-thought). Test whether that holds.

**Write up your findings** -- this is the publishable artifact. The through-line: *"Agents aren't black boxes -- they're just bad at explaining themselves. That's a solvable problem."*

---

### Exercise 5: The Approval UI

**Goal**: A simple interface that shows agent output + narrative + a human approval step.

**What to build**:
- Use Streamlit (fast, no deployment overhead for a learning project)
- Layout:
  - Top: task that was given to the agent
  - Left panel: agent's final output
  - Right panel: structured narrative (collapsible sections for goal / steps / decisions / summary)
  - Bottom: Approve / Reject buttons with optional comment field
- Wire the backend: run the agent, generate the narrative, render both

**Learning objective**: Understand how the narrative changes the human's ability to make an informed decision. Would you approve this output differently with vs. without the narrative? This is the core value proposition.

**Note**: Keep the UI minimal. The point is to validate the concept, not polish a product.

---

### Exercise 6 (Deferred): LangSmith as a Second Input Path

**Goal**: Add LangSmith API support as an alternative trace source, producing the same intermediate JSON from Exercise 2.

**What to build**:
- Pull a stored trace from LangSmith via the API
- Write a mapper that transforms LangSmith's trace format into the normalized intermediate format
- Run the same narrator prompt against it and verify the output is indistinguishable from the middleware-sourced narrative

**Learning objective**: The intermediate format contract from Exercise 2 pays off here. If the contract held, this is mostly a mapping exercise, not a redesign.

**Why deferred**: Requires a LangSmith account and introduces an external dependency. Do this after the core loop is working.

---

### Exercise 7 (Curiosity): OTEL Exploration

**Goal**: Understand what it would take to make the narrative writer framework-agnostic via OpenTelemetry.

**What to explore**:
- Does LangChain's middleware / runtime emit OTEL spans? Run with a local OTEL collector (Jaeger or similar) and inspect the span tree
- Map the OTEL span structure to the `Narrative` schema -- what fields exist, what's missing?
- Sketch (don't build) what a framework-agnostic narrator would look like: receives an OTEL trace, produces a narrative

**Learning objective**: Whether OTEL's trace model has enough semantic richness for narrative generation, or whether it's too low-level (spans without intent). This informs whether "agnostic" is viable or requires agent frameworks to emit richer metadata.

**Don't rabbit-hole here** -- timebox to one session.

---

## Open Decisions

| Decision | Recommendation |
|----------|---------------|
| Agent task domain | Company/market research -- forces multi-step tool use, produces interesting narratives |
| Narrator LLM | Same model as agent (OpenAI) for simplicity in exercises 3-4; swap to Claude for comparison if curious |
| UI framework | Streamlit for exercises 1-5; revisit Next.js if this becomes a portfolio piece |
| Structured output | Pydantic + `.with_structured_output()` from Exercise 3 onward |

## Questions This Project Answers

1. Does the callback trace produce a better narrative than passing the messages list to the narrator?
2. What structure makes a narrative useful to a non-technical SME?
3. How much does a structured narrative change the quality of a human approval decision?
4. Is OTEL rich enough to drive narrative generation without framework-specific instrumentation?
