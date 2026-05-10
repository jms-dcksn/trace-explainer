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
from typing import Any

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


def narrate(
    task: str,
    trace: list[dict[str, Any]],
    model: str = "gpt-4.1",
) -> Narrative:
    """Generate a structured narrative from a captured trace."""
    llm = ChatOpenAI(model=model).with_structured_output(Narrative)
    user_msg = (
        f"USER TASK:\n{task}\n\n"
        f"TRACE:\n{json.dumps(trace, indent=2, default=str)}"
    )
    return llm.invoke(
        [
            {"role": "system", "content": NARRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ]
    )
