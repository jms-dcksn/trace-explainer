"""Trace-to-narrative translator.

Takes the normalized intermediate trace produced by the capture layer
(Exercise 2) and asks an LLM to convert it into a structured Narrative.

Deliberately decoupled from the agent: the narrator only knows about the
trace JSON contract, not about middleware, LangChain state, or how the
trace was captured. That contract is what makes Exercise 4 (messages-list
input) and Exercise 6 (LangSmith input) drop-in swaps.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class Narrative(BaseModel):
    """Structured narrative of an agent run, intended for an SME approver."""

    goal: str = Field(
        description="What the agent was asked to do, in one sentence."
    )
    steps_taken: list[str] = Field(
        description=(
            "Ordered list of actions and tool calls the agent performed. "
            "Each item is one concrete step, phrased for a non-technical reader."
        )
    )
    decisions_made: list[str] = Field(
        description=(
            "Key reasoning choices: why a tool was chosen, why the agent "
            "pivoted, why it stopped. Only genuine decisions -- do not "
            "restate steps."
        )
    )
    summary: str = Field(
        description="Plain-English conclusion and the agent's final output."
    )


NARRATOR_SYSTEM_PROMPT = """\
You translate the trace of an AI agent run into a structured narrative for a
non-technical reviewer who must approve or reject the agent's output.

You will be given:
- The user's original task.
- A normalized trace as a JSON array of events. Event types:
  * agent_thought  -- reasoning the agent emitted before acting
  * tool_call      -- a tool the agent invoked, with its input
  * tool_result    -- what the tool returned
  * final_answer   -- the agent's final response to the user

Rules:
- `goal` restates the user's task in one sentence. Do not embellish.
- `steps_taken` is chronological. One item per meaningful action. Combine a
  tool_call with its tool_result into a single step ("Looked up X and found Y").
  Skip pure restatement; keep the level of detail an SME would want.
- `decisions_made` captures genuine reasoning forks: why this tool, why stop
  now, why prioritize one finding over another. If the trace contains no real
  decisions, return an empty list -- do not invent them.
- `summary` is the agent's conclusion in plain English. Quote or paraphrase
  the final_answer; do not add information that is not in the trace.
- Never speculate beyond what the trace shows.
"""


NARRATOR_MESSAGES_SYSTEM_PROMPT = """\
You translate the raw message history of an AI agent run into a structured
narrative for a non-technical reviewer who must approve or reject the
agent's output.

You will be given:
- The user's original task.
- The full chronological message history as a JSON array. Roles:
  * system   -- the agent's system prompt (context, not an action)
  * user     -- the user's request
  * ai       -- the agent's responses; may include `tool_calls` (the agent
                decided to invoke a tool) and free-form `content` (reasoning)
  * tool     -- the result returned by a tool the agent called

Rules:
- `goal` restates the user's task in one sentence. Do not embellish.
- `steps_taken` is chronological. One item per meaningful action. Combine
  an ai tool_call with its tool result into a single step ("Looked up X
  and found Y"). Skip the system prompt and pure restatement.
- `decisions_made` captures genuine reasoning forks: why this tool, why
  stop now, why prioritize one finding over another. Use the ai content
  blocks as your source of reasoning. If the messages contain no real
  decisions, return an empty list -- do not invent them.
- `summary` is the agent's conclusion in plain English. Quote or paraphrase
  the final ai message; do not add information that is not in the history.
- Never speculate beyond what the messages show.
"""


@dataclass
class NarrationResult:
    """A narrative plus metadata about the LLM call that produced it."""

    narrative: Narrative
    input_tokens: int
    output_tokens: int
    latency_s: float


def _invoke_with_meta(
    model: str, system_prompt: str, user_msg: str
) -> NarrationResult:
    llm = ChatOpenAI(model=model).with_structured_output(
        Narrative, include_raw=True
    )
    t0 = time.perf_counter()
    out = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
    )
    latency = time.perf_counter() - t0

    parsed: Narrative = out["parsed"]
    raw = out.get("raw")
    usage = getattr(raw, "usage_metadata", None) or {}
    return NarrationResult(
        narrative=parsed,
        input_tokens=int(usage.get("input_tokens", 0) or 0),
        output_tokens=int(usage.get("output_tokens", 0) or 0),
        latency_s=latency,
    )


def narrate(
    task: str,
    trace: list[dict[str, Any]],
    model: str = "gpt-5.4-mini",
) -> Narrative:
    """Generate a structured narrative from a captured trace."""
    return narrate_from_trace(task, trace, model=model).narrative


def narrate_from_trace(
    task: str,
    trace: list[dict[str, Any]],
    model: str = "gpt-5.4-mini",
) -> NarrationResult:
    """Narrate from the normalized intermediate trace (Exercise 2 contract)."""
    user_msg = (
        f"USER TASK:\n{task}\n\n"
        f"TRACE:\n{json.dumps(trace, indent=2, default=str)}"
    )
    return _invoke_with_meta(model, NARRATOR_SYSTEM_PROMPT, user_msg)


def _serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Convert a LangChain messages list into a JSON-friendly form for the narrator."""
    out: list[dict[str, Any]] = []
    for m in messages:
        if isinstance(m, SystemMessage):
            out.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            entry: dict[str, Any] = {"role": "ai", "content": m.content}
            tool_calls = list(getattr(m, "tool_calls", None) or [])
            if tool_calls:
                entry["tool_calls"] = [
                    {"name": tc.get("name"), "args": tc.get("args", {})}
                    for tc in tool_calls
                ]
            out.append(entry)
        elif isinstance(m, ToolMessage):
            out.append(
                {
                    "role": "tool",
                    "name": getattr(m, "name", None),
                    "content": m.content,
                }
            )
        else:
            out.append({"role": "other", "content": str(m)})
    return out


def narrate_from_messages(
    task: str,
    messages: list[Any],
    model: str = "gpt-5.4-mini",
) -> NarrationResult:
    """Narrate from the agent's raw LangChain messages list."""
    serialized = _serialize_messages(messages)
    user_msg = (
        f"USER TASK:\n{task}\n\n"
        f"MESSAGES:\n{json.dumps(serialized, indent=2, default=str)}"
    )
    return _invoke_with_meta(model, NARRATOR_MESSAGES_SYSTEM_PROMPT, user_msg)
