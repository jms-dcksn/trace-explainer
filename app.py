"""Exercise 5: Approval UI.

Streamlit front-end for the trace-explainer pipeline. Runs the account-research
agent live, streams capture-middleware events into tool-call cards, then renders
the narrator's structured writeup beside the agent's final answer.

See SPEC.md for the full spec; this file is the implementation.
"""
from __future__ import annotations

import json
import time
from typing import Any

import streamlit as st
from langchain.messages import AIMessage
from langchain_openai import ChatOpenAI

from main import build_agent
from narrator import narrate_from_messages, narrate_from_trace


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRESET_TASKS = [
    "Build me an account brief on Acme Corp.",
    "What is the renewal date for Initech?",
    "Compare Acme Corp and Globex on renewal risk.",
    "Build me an account brief on Wayne Enterprises.",
]

AGENT_MODEL_NAME = "gpt-5.5"


# ---------------------------------------------------------------------------
# Session bootstrap
# ---------------------------------------------------------------------------


def _init_state() -> None:
    ss = st.session_state
    ss.setdefault("turns", [])
    ss.setdefault("messages_history", [])
    ss.setdefault("pending_task", None)
    ss.setdefault("agent", None)


@st.cache_resource(show_spinner=False)
def get_agent():
    """Build the agent once per session. Cached at the resource level."""
    model = ChatOpenAI(
        model=AGENT_MODEL_NAME,
        reasoning_effort="medium",
        use_responses_api=True,
    )
    return build_agent(model)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def render_sidebar() -> None:
    with st.sidebar:
        st.title("Trace Explainer")
        st.markdown(
            "Agents aren't black boxes -- they're bad at explaining themselves. "
            "This app shows a **capture middleware** that records every meaningful "
            "event of an agent run, and a **narrator LLM** that turns that record "
            "into a structured writeup an SME can actually approve."
        )

        st.subheader("How it works")
        st.markdown(
            "1. **Agent** runs and calls tools.\n"
            "2. **Capture middleware** records each thought, tool call, and result "
            "as a normalized JSON event.\n"
            "3. **Intermediate trace** is a stable JSON contract -- the only thing "
            "the narrator sees.\n"
            "4. **Narrator LLM** translates the trace into a structured Narrative "
            "(goal / steps / decisions / summary).\n"
            "5. **Human** reads the narrative and approves or rejects."
        )

        st.subheader("Glossary")
        st.markdown(
            "- **Capture middleware** -- LangChain agent hook that observes the "
            "run and writes events to state.\n"
            "- **Intermediate trace** -- the normalized JSON list of events. The "
            "contract between capture and narrator.\n"
            "- **Narrator** -- a second LLM call that converts the trace into a "
            "structured Narrative.\n"
            "- **Structured output** -- Pydantic schema enforced via "
            "`.with_structured_output()`, so the narrative is machine-readable."
        )

        st.subheader("Session stats")
        turns = st.session_state.turns
        total_tool_calls = sum(t["stats"]["tool_calls"] for t in turns)
        total_in = sum(t["stats"]["input_tokens"] for t in turns)
        total_out = sum(t["stats"]["output_tokens"] for t in turns)
        last_latency = turns[-1]["stats"]["latency_s"] if turns else 0.0
        c1, c2 = st.columns(2)
        c1.metric("Turns", len(turns))
        c2.metric("Tool calls", total_tool_calls)
        c1.metric("Narrator tokens (in)", total_in)
        c2.metric("Narrator tokens (out)", total_out)
        st.metric("Last turn latency (s)", f"{last_latency:.2f}")


# ---------------------------------------------------------------------------
# Event rendering helpers
# ---------------------------------------------------------------------------


def _parse_agent_output(text: str) -> dict[str, str]:
    """Parse the agent's JSON-shaped final answer into {response, agent_summary}.

    The agent is wired with response_format=AgentOutput, so the final AIMessage
    content is a JSON string with keys `response` and `agent_summary`. Fall
    back gracefully if parsing fails.
    """
    if not text:
        return {"response": "", "agent_summary": ""}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return {
                "response": str(data.get("response", "")).strip(),
                "agent_summary": str(data.get("agent_summary", "")).strip(),
            }
    except (json.JSONDecodeError, TypeError):
        pass
    return {"response": text.strip(), "agent_summary": ""}


def _extract_final_answer(messages: list[Any]) -> str:
    """Pull final-answer text from the last AIMessage. Handles content blocks."""
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            content = m.content
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        parts.append(block)
                return "".join(parts)
    return ""


def _pair_events(trace: list[dict]) -> list[dict]:
    """Walk the trace and group thought + tool_call + tool_result into cards.

    Returns a list of "render items": either
      {"kind": "card", "thought": str|None, "call": evt, "result": evt|None}
      {"kind": "final", "evt": evt}
    Preserves order. Used for both live and post-stream rendering.
    """
    items: list[dict] = []
    pending_thought: str | None = None
    open_cards_by_id: dict[str, int] = {}  # tool_call_id -> items index

    for evt in trace:
        etype = evt["type"]
        if etype == "agent_thought":
            pending_thought = evt["content"]
        elif etype == "tool_call":
            items.append(
                {
                    "kind": "card",
                    "thought": pending_thought,
                    "call": evt,
                    "result": None,
                }
            )
            pending_thought = None  # consumed by first tool_call
            tcid = evt.get("tool_call_id")
            if tcid:
                open_cards_by_id[tcid] = len(items) - 1
        elif etype == "tool_result":
            tcid = evt.get("tool_call_id")
            idx = open_cards_by_id.pop(tcid, None) if tcid else None
            if idx is None:
                # Fallback: attach to the last card without a result
                for i in range(len(items) - 1, -1, -1):
                    if items[i]["kind"] == "card" and items[i]["result"] is None:
                        idx = i
                        break
            if idx is not None:
                items[idx]["result"] = evt
        elif etype == "final_answer":
            items.append({"kind": "final", "evt": evt})

    return items


def render_tool_card(item: dict) -> None:
    """Render one tool-call card. Spinner when result is missing."""
    call = item["call"]
    result = item["result"]
    thought = item["thought"]

    tool_name = call.get("tool", "?")
    args = call.get("input", {})

    icon = "🔍" if tool_name == "web_search" else "🗂️" if tool_name == "lookup_account" else "⚙️"
    state = "complete" if result is not None else "running"
    label = f"{icon} {tool_name}" + ("" if result else "  (running...)")

    with st.status(label, state=state, expanded=False):
        if thought:
            st.markdown(f"_{thought}_")
        st.caption("Input")
        st.code(json.dumps(args, indent=2, default=str), language="json")

        if result is not None:
            st.caption("Output")
            output = str(result.get("output", ""))
            if len(output) > 500:
                st.code(output[:500] + "  ...", language="text")
                with st.expander("show full output"):
                    st.code(output, language="text")
            else:
                st.code(output, language="text")

        with st.expander("raw captured event"):
            st.code(
                json.dumps(
                    {"tool_call": call, "tool_result": result},
                    indent=2,
                    default=str,
                ),
                language="json",
            )


def render_thought_only(text: str) -> None:
    """For a trailing agent_thought with no tool call after it (rare)."""
    st.markdown(f"💭 _{text}_")


def render_progress(trace: list[dict]) -> None:
    """Render the streaming progress area for a single turn."""
    items = _pair_events(trace)
    trailing_thought: str | None = None
    for item in items:
        if item["kind"] == "card":
            render_tool_card(item)
        elif item["kind"] == "final":
            # Final-answer event is rendered in the answer column, not here.
            continue
    # Dangling thought (no tool_call followed) — uncommon, but handle it.
    if items and items[-1]["kind"] != "card":
        pass


# ---------------------------------------------------------------------------
# Agent invocation (streaming)
# ---------------------------------------------------------------------------


def run_turn(task: str, progress_slot) -> dict:
    """Stream the agent over `task`, render cards live, return the turn record."""
    agent = get_agent()

    # Build the input messages list: prior history + this user turn.
    history = st.session_state.messages_history
    input_messages = list(history) + [{"role": "user", "content": task}]

    trace: list[dict] = []
    final_state: dict[str, Any] | None = None
    last_event_count = 0

    t0 = time.perf_counter()
    for chunk in agent.stream(
        {"messages": input_messages},
        stream_mode="values",
    ):
        final_state = chunk
        trace = chunk.get("trace", []) or []
        if len(trace) != last_event_count:
            with progress_slot.container():
                render_progress(trace)
            last_event_count = len(trace)
    agent_latency = time.perf_counter() - t0

    assert final_state is not None
    full_messages = final_state.get("messages", [])
    final_answer = _extract_final_answer(full_messages)

    # Narrate from trace (always). Messages narration is lazy on toggle.
    t1 = time.perf_counter()
    from_trace = narrate_from_trace(task, trace)
    narrator_latency = time.perf_counter() - t1

    # Update persistent message history (full state, so multi-turn memory works).
    st.session_state.messages_history = [
        _message_to_dict(m) for m in full_messages
    ]

    tool_call_count = sum(1 for e in trace if e["type"] == "tool_call")

    return {
        "task": task,
        "trace": trace,
        "messages_snapshot": full_messages,
        "final_answer": final_answer,
        "narrative_trace": from_trace,
        "narrative_messages": None,
        "narrative_view": "trace",
        "feedback": {"thumbs": None, "notes": ""},
        "stats": {
            "input_tokens": from_trace.input_tokens,
            "output_tokens": from_trace.output_tokens,
            "latency_s": agent_latency + narrator_latency,
            "tool_calls": tool_call_count,
        },
    }


def _message_to_dict(m: Any) -> dict[str, Any]:
    """Best-effort conversion for re-feeding into agent.stream on next turn.

    LangChain accepts dicts of the form {"role": ..., "content": ...} and
    will preserve tool_calls / tool_call_ids on ai/tool messages.
    """
    role_map = {
        "HumanMessage": "user",
        "AIMessage": "assistant",
        "SystemMessage": "system",
        "ToolMessage": "tool",
    }
    role = role_map.get(type(m).__name__, "user")
    entry: dict[str, Any] = {"role": role, "content": m.content}
    tcs = getattr(m, "tool_calls", None)
    if tcs:
        entry["tool_calls"] = tcs
    tcid = getattr(m, "tool_call_id", None)
    if tcid:
        entry["tool_call_id"] = tcid
    name = getattr(m, "name", None)
    if name:
        entry["name"] = name
    return entry


# ---------------------------------------------------------------------------
# Turn rendering (post-stream)
# ---------------------------------------------------------------------------


def render_narrative(narr) -> None:
    n = narr.narrative if hasattr(narr, "narrative") else narr
    with st.expander("**Goal**", expanded=True):
        st.write(n.goal)
    with st.expander("**Steps taken**", expanded=True):
        for s in n.steps_taken:
            st.markdown(f"- {s}")
    with st.expander("**Decisions made**", expanded=True):
        if n.decisions_made:
            for d in n.decisions_made:
                st.markdown(f"- {d}")
        else:
            st.caption("_(no genuine decisions captured)_")
    with st.expander("**Summary**", expanded=True):
        st.write(n.summary)


def render_turn(turn_idx: int, turn: dict) -> None:
    """Render a completed turn block (after streaming has finished)."""
    st.markdown(f"### Turn {turn_idx + 1}")
    with st.chat_message("user"):
        st.write(turn["task"])

    # Replay the tool-call cards (collapsed but present).
    with st.expander(f"Captured events ({len(turn['trace'])})", expanded=False):
        render_progress(turn["trace"])

    # Parse the agent's structured output (response + self-summary).
    parsed = _parse_agent_output(turn["final_answer"])

    # Top: the agent's actual response to the user.
    st.markdown("#### Agent's response")
    with st.container(border=True):
        st.markdown(parsed["response"] or "_(no response)_")

    # Below: comparison row -- agent's self-summary vs. narrator's writeup.
    st.markdown("#### How the run was explained")
    st.caption(
        "Left: the agent's own one-paragraph summary, produced inline as part "
        "of its structured output. Right: a separate narrator LLM that reads "
        "the captured trace and produces a structured writeup. Same run, two "
        "explanation strategies."
    )
    col_self, col_narr = st.columns(2, gap="large")

    with col_self:
        st.markdown("**Agent's self-summary**")
        st.caption("Produced by the agent itself (same call as the response).")
        with st.container(border=True):
            st.markdown(parsed["agent_summary"] or "_(none)_")
        with st.expander("raw final-answer event"):
            final_evt = next(
                (e for e in turn["trace"] if e["type"] == "final_answer"), None
            )
            st.code(json.dumps(final_evt or {}, indent=2, default=str), language="json")

    with col_narr:
        st.markdown("**Narrator's structured writeup**")
        st.caption("Produced by a separate LLM call over the captured trace.")
        view = st.segmented_control(
            "Source",
            options=["Trace", "Messages"],
            default="Trace" if turn["narrative_view"] == "trace" else "Messages",
            key=f"narr_source_{turn_idx}",
            label_visibility="collapsed",
        )
        if view == "Messages" and turn["narrative_messages"] is None:
            with st.spinner("Narrating from messages..."):
                turn["narrative_messages"] = narrate_from_messages(
                    turn["task"], turn["messages_snapshot"]
                )
        turn["narrative_view"] = "trace" if view == "Trace" else "messages"
        narr = (
            turn["narrative_trace"]
            if view == "Trace"
            else turn["narrative_messages"]
        )
        render_narrative(narr)
        st.caption(
            f"narrator: {narr.input_tokens} in / {narr.output_tokens} out tok, "
            f"{narr.latency_s:.2f}s"
        )

    # Feedback row
    st.markdown("#### Was this narrative useful?")
    fb = turn["feedback"]
    fc1, fc2, fc3 = st.columns([1, 1, 6])
    if fc1.button("👍", key=f"up_{turn_idx}", type="primary" if fb["thumbs"] == "up" else "secondary"):
        fb["thumbs"] = "up"
    if fc2.button("👎", key=f"down_{turn_idx}", type="primary" if fb["thumbs"] == "down" else "secondary"):
        fb["thumbs"] = "down"
    fb["notes"] = fc3.text_input(
        "Notes (optional)",
        value=fb["notes"],
        key=f"notes_{turn_idx}",
        label_visibility="collapsed",
        placeholder="Optional notes...",
    )
    if fb["thumbs"]:
        st.caption(f"Feedback recorded: {fb['thumbs']}")

    st.divider()


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------


def main() -> None:
    st.set_page_config(
        page_title="Trace Explainer",
        page_icon="🔎",
        layout="wide",
    )
    _init_state()
    render_sidebar()

    st.title("Account Research Agent")
    st.caption(
        "Run the agent, watch the capture middleware record its trace in real time, "
        "then read the narrator's structured writeup."
    )

    # Render completed turns first so the new run streams below them.
    for i, turn in enumerate(st.session_state.turns):
        render_turn(i, turn)

    # Preset task chips
    st.markdown("**Quick-pick tasks:**")
    chip_cols = st.columns(len(PRESET_TASKS))
    for i, (col, preset) in enumerate(zip(chip_cols, PRESET_TASKS)):
        if col.button(preset, key=f"preset_{i}", use_container_width=True):
            st.session_state.pending_task = preset
            st.rerun()

    typed = st.chat_input("Ask the agent about an account...")
    if typed:
        st.session_state.pending_task = typed

    pending = st.session_state.pending_task
    if pending:
        st.session_state.pending_task = None

        st.markdown(f"### Turn {len(st.session_state.turns) + 1} (running)")
        with st.chat_message("user"):
            st.write(pending)

        st.markdown("**Live capture:**")
        progress_slot = st.empty()

        try:
            turn = run_turn(pending, progress_slot)
        except Exception as e:
            st.error(f"Agent run failed: {e}")
            raise

        st.session_state.turns.append(turn)
        # Force a rerun so the completed turn renders through the normal path
        # (with two-column answer/narrative + feedback), and stats refresh.
        st.rerun()


if __name__ == "__main__":
    main()
