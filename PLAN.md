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

### Exercise 2: Build the Callback Handler

**Goal**: Capture every meaningful event from the agent run into a normalized intermediate format -- the contract between the capture layer and the explainer.

**What to build**:
- Extend `BaseCallbackHandler`. Only four event types carry real signal: `on_agent_action`, `on_tool_start`, `on_tool_end`, `on_agent_finish`. Implement those; ignore the rest.
- LangChain's callback data arrives as a nested run tree. Flatten it into a chronological list of events.
- Normalize to this intermediate format:

```json
[
  {"step": 1, "type": "agent_thought", "content": "..."},
  {"step": 2, "type": "tool_call", "tool": "...", "input": "..."},
  {"step": 3, "type": "tool_result", "tool": "...", "output": "..."},
  {"step": 4, "type": "final_answer", "content": "..."}
]
```

This JSON is the stable contract. The explainer prompt in Exercise 3 is written against this format, not against raw callback data -- which means swapping in a different capture source later (e.g., LangSmith) only requires producing the same JSON.

**Learning objective**: Understand what the callback system exposes, what's noise, and how to flatten a nested run tree into something usable. Also: what information is explicitly in the trace vs. what has to be inferred.

**Questions to answer after**:
- Which fields did you have to infer vs. read directly from the callback data?
- What's missing that you'd want a narrator to know?

---

### Exercise 3: Write the Narrative (Callback Approach)

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

### Exercise 4: The Comparison Experiment

**Goal**: Produce the same narrative from the agent's message history and compare it to the callback approach.

**What to build**:
- After the agent run, extract the full messages list from the agent's state
- Feed to the same narrator LLM with the same `Narrative` schema and a similar prompt
- Run both approaches against 3-5 different tasks
- For each run, record: narrative quality (manual review), token count, latency, accuracy vs. what actually happened

**Learning objective**: Empirical answer to the callback-vs-context-window question. The hypothesis is that the callback trace is more precise (structured, timestamped) but the messages list is richer in reasoning (full chain-of-thought). Test whether that holds.

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
- Run the same narrator prompt against it and verify the output is indistinguishable from the callback-sourced narrative

**Learning objective**: The intermediate format contract from Exercise 2 pays off here. If the contract held, this is mostly a mapping exercise, not a redesign.

**Why deferred**: Requires a LangSmith account and introduces an external dependency. Do this after the core loop is working.

---

### Exercise 7 (Curiosity): OTEL Exploration

**Goal**: Understand what it would take to make the narrative writer framework-agnostic via OpenTelemetry.

**What to explore**:
- Does LangChain's callback handler emit OTEL spans? Run with a local OTEL collector (Jaeger or similar) and inspect the span tree
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
