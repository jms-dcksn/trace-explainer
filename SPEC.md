# Exercise 5: Approval UI -- Spec

Streamlit app that runs the account-research agent live, streams its trace, renders the narrator's writeup, and collects approval feedback. The point is to make the capture-middleware -> narrator pipeline visually intuitive and educational, not to polish a product.

## Stack

- Streamlit (single `app.py`)
- Reuses `main.py` (agent + `CaptureMiddleware`) and `narrator.py` (`narrate_from_trace`, `narrate_from_messages`) -- no rewrites
- Real LangGraph streaming via `agent.stream(..., stream_mode="updates")` so tool-call cards appear as the agent runs, not after

## Layout

```
+----------------------+-----------------------------------------------+
| Sidebar              | Main                                          |
| - Project pitch      | [Preset task chips: Acme | Globex | Initech ] |
| - Pipeline diagram   | [Free-text chat input ........................]|
| - Glossary           |                                               |
| - Live session stats | --- Turn 1 ---------------------------------- |
|   - tool calls: N    | [thought] -> [tool card] -> [tool result]     |
|   - tokens: in/out   | [thought] -> [tool card] -> [tool result]     |
|   - latency: Xs      |                                               |
|                      | +---- Final answer ----+ +-- Narrative ----+  |
|                      | | agent's reply        | | goal             |  |
|                      | |                      | | steps_taken      |  |
|                      | |                      | | decisions_made   |  |
|                      | |                      | | summary          |  |
|                      | +----------------------+ +------------------+  |
|                      | [trace] [messages] toggle for narrative source |
|                      | [thumbs up] [thumbs down]  [notes...]         |
|                      |                                               |
|                      | --- Turn 2 (active) -------------------------- |
|                      | ... streaming ...                             |
+----------------------+-----------------------------------------------+
```

## Sidebar

Static content, no inputs. Three blocks:

1. **What this is** -- one paragraph. "Agents aren't black boxes -- they're bad at explaining themselves. This shows a capture middleware that records every meaningful event, and a narrator LLM that turns it into a structured writeup a human can actually approve."
2. **How it works** -- labeled steps (text, no image): Agent run -> Capture middleware -> Intermediate JSON -> Narrator LLM -> Structured narrative. Keep it 5 lines.
3. **Glossary** -- short definitions: capture middleware, intermediate trace, narrator, structured output.
4. **Live session stats** -- counters that update as the agent runs:
   - Tool calls: N
   - Input/output tokens (agent + narrator combined)
   - Last-turn latency
   - Total turns

## Main panel

### Input row

- Free-text `st.chat_input`
- Above it: 3-5 preset chips (buttons) that drop a task into the input. Use the Ex4 tasks:
  - "Build me an account brief on Acme Corp"
  - "What is the renewal date for Initech?"
  - "Compare Acme Corp and Globex on renewal risk"
  - "Build me an account brief on Wayne Enterprises" (not in CRM -- forces web_search)

### Turn rendering

Each turn = one user message + the agent run that followed. Per-turn block contains, in order:

1. User message (chat bubble)
2. Streaming progress region:
   - For each `tool_call`/`tool_result` pair, a **tool-call card** (see below)
   - Cards appear incrementally as `agent.stream()` yields updates
3. Final-answer + narrative side-by-side (two `st.columns`)
4. Feedback row (thumbs up/down + optional notes)

When turn 2 starts, turn 1 stays fully expanded in scroll history. Each turn has its own trace + narrative; the trace state does NOT accumulate across turns. The agent's messages list DOES persist so multi-turn conversation works.

### Tool-call card

A bordered container (`st.container(border=True)`) per tool invocation:

- **Header**: tool name (e.g. `lookup_account`) with a small icon/badge
- **Preceding thought** (italic, dim): the `agent_thought` event that came just before this call, if any -- shows reasoning -> action
- **Input args**: pretty-printed JSON in a `st.code` block
- **Output**: collapsible `st.expander("result")` -- raw output string, truncated to ~500 chars with "show full" if longer
- **Raw captured event** (collapsed by default): `st.expander("raw captured event")` showing the JSON for the `tool_call` + `tool_result` events. Reinforces the pipeline-transparency thesis -- the pretty card is just a render of this JSON. SME-friendly by default, engineer-friendly on click.

Cards render as soon as the corresponding capture events land on state. While a tool is running (after `tool_call` event, before `tool_result`), show a spinner inside the card.

### Final answer + narrative columns

Two equal `st.columns`:

- **Left -- Agent's final answer**: the agent's last `AIMessage.content`, rendered as markdown
- **Right -- Narrative**: 4 collapsible sections (goal, steps_taken, decisions_made, summary). Default to all expanded.

Above the narrative column, a **source toggle**:
- `[ Trace ]  [ Messages ]` segmented control (`st.segmented_control` or radio)
- Default: Trace
- Switching to Messages triggers `narrate_from_messages(...)` on demand (cached after first generation per turn), reuses the captured messages list
- This is the Ex4 comparison surfaced in-product, not a separate analysis

### Feedback row

Below the columns, per turn:

- Two buttons: thumbs up / thumbs down
- `st.text_input` for optional notes
- On submit, append `{turn_id, thumbs, notes, narrative_source}` to `st.session_state.feedback` (in-memory only, lost on reload -- session state only by design)
- Show a small acknowledgement after submission

## Streaming implementation notes

- Use `agent.stream({"messages": [...]}, stream_mode="updates")` to get per-node update dicts
- Each update may contain new `messages` (model outputs, tool messages) and new `trace` events (from the capture middleware's `Command(update=...)`)
- Maintain a render loop that:
  1. Reads the latest `trace` events
  2. Pairs `tool_call` with corresponding `tool_result` (by step or by tool name + order)
  3. Renders/updates tool-call cards using `st.empty()` placeholders so cards mutate in place rather than re-render the whole thread
- After the stream ends, run `narrate_from_trace(task, trace)` synchronously and render the narrative column
- `narrate_from_messages(...)` is lazy: only called if the user toggles to Messages view

Streamlit's rerun model is hostile to mid-run partial updates. Use `st.write_stream` where possible; otherwise keep a single placeholder per card and overwrite it. If this gets ugly, fall back to a simulated stream: invoke to completion, then loop over `trace` events with `time.sleep(0.05)` between renders. Document the fallback in code.

## State model (Streamlit session_state)

```python
{
  "turns": [
    {
      "task": str,
      "messages_at_start": [...],          # snapshot before this turn
      "trace": [...],                      # captured events for THIS turn
      "messages_after": [...],             # full messages list after this turn
      "final_answer": str,
      "narrative_trace": Narrative,        # from narrate_from_trace
      "narrative_messages": Narrative | None,  # lazy
      "narrative_view": "trace" | "messages",
      "feedback": {"thumbs": "up"|"down"|None, "notes": str},
      "stats": {"input_tokens": int, "output_tokens": int, "latency_s": float, "tool_calls": int},
    },
  ],
  "agent_state": {...}  # the persistent LangGraph state across turns
}
```

## Out of scope (do NOT do)

- Persisting feedback (file/DB) -- session-only by design
- Auth / multi-user
- Streaming the narrator output (run it post-trace, render when done)
- Editing the agent's tools or prompts from the UI
- Mobile-optimized layout
- Deployment configuration (local `streamlit run app.py` is enough for now)

## Build sequence

1. Skeleton: sidebar + chat input + preset chips, no agent yet
2. Single-turn, non-streaming: invoke agent, render trace + answer + narrative
3. Add streaming with tool-call cards
4. Add narrative source toggle (trace vs messages)
5. Add feedback row
6. Multi-turn: persist agent state, stack turn blocks
7. Sidebar live stats

Ship after step 4 is usable end-to-end; steps 5-7 are polish.

## Resolved decisions

- **Multi-turn: keep it.** Account research has natural follow-ups ("now compare them", "what about their competitors"). The per-turn block model already isolates trace + narrative cleanly, so multi-turn adds only session_state plumbing, not conceptual complexity. The persistent agent messages list is what enables a real conversation; trace and narrative reset per turn so each block stays educationally clean.
- **Raw captured-event JSON: include it, collapsed by default, on every tool-call card.** The whole project's thesis is that the intermediate JSON is the contract -- hiding it undermines the point. Default-collapsed keeps the SME view clean; expanding it lets engineers and curious viewers see exactly what the middleware captured. Same treatment for the final-answer event (an expander under the agent's reply).
