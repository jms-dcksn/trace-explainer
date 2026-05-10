"""End-to-end test of CaptureMiddleware with a stubbed model and tools.

Runs the agent against a deterministic FakeMessagesListChatModel that yields:
  1. An AIMessage with a tool call to lookup_account AND NO content (the
     tool-only emission case the user flagged).
  2. An AIMessage with content + a tool call to web_search.
  3. An AIMessage with the final account brief and no tool calls.

This exercises every branch of the capture middleware without requiring
OpenAI/Tavily credentials.
"""
from __future__ import annotations

import json
from typing import Any, Sequence

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage

from main import build_agent, lookup_account


# ---------------------------------------------------------------------------
# Stub the model
# ---------------------------------------------------------------------------


class FakeToolCallingModel(FakeMessagesListChatModel):
    """Fake chat model that satisfies create_agent's `bind_tools` contract.

    `create_agent` calls `model.bind_tools(tools, ...)` before invoking; the base
    BaseChatModel raises NotImplementedError. We just return self so the canned
    responses flow through unchanged.
    """

    def bind_tools(
        self,
        tools: Sequence[Any],
        **kwargs: Any,
    ):  # type: ignore[override]
        return self


CANNED_RESPONSES: list[BaseMessage] = [
    # Round 1: tool call only, no commentary -- the empty-content path.
    AIMessage(
        content="",
        tool_calls=[
            {
                "name": "lookup_account",
                "args": {"company_name": "Acme Corp"},
                "id": "call_lookup_1",
            }
        ],
    ),
    # Round 2: thought + tool call.
    AIMessage(
        content=(
            "Got the CRM record. Now I want recent public news about Acme Corp "
            "to round out the brief."
        ),
        tool_calls=[
            {
                "name": "web_search",
                "args": {"query": "Acme Corp recent news 2026"},
                "id": "call_search_1",
            }
        ],
    ),
    # Round 3: final answer, no tool calls.
    AIMessage(
        content=(
            "Account brief — Acme Corp\n"
            "Relationship: Strategic tier, $1.25M ARR, owned by Priya Shah; "
            "renewal 2026-09-15.\n"
            "Recent: signed expansion of finance automation footprint and "
            "announced new CFO sponsor.\n"
            "Talking points / risks:\n"
            "  - Procurement bottleneck flagged in notes — pre-warm Legal.\n"
            "  - Two open opportunities tied to Document Understanding.\n"
            "  - Last QBR was Feb 2026; schedule the next one before renewal."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Stub web_search so we don't hit Tavily
# ---------------------------------------------------------------------------


def web_search(query: str) -> str:
    """Stubbed web_search returning canned 'recent news' text."""
    return (
        "[stubbed search results for query: "
        + query
        + "]\n"
        "- Acme Corp announces expansion of finance automation program (Apr 2026).\n"
        "- New CFO Lara Chen joins Acme Corp from Globex (Mar 2026).\n"
        "- Acme Corp reports Q1 2026 revenue +12% YoY."
    )


def main() -> None:
    model = FakeToolCallingModel(responses=CANNED_RESPONSES)
    agent = build_agent(model, tools=[web_search, lookup_account])

    print("=" * 72)
    print("RUNNING AGENT (fake model, stubbed web_search)")
    print("=" * 72)

    result = agent.invoke(
        {
            "messages": [
                {"role": "user", "content": "Build me an account brief on Acme Corp."}
            ]
        }
    )

    print("\n" + "=" * 72)
    print("FINAL RESULT (last message content)")
    print("=" * 72)
    print(result["messages"][-1].content)

    print("\n" + "=" * 72)
    print("CAPTURED TRACE (normalized intermediate format)")
    print("=" * 72)
    print(json.dumps(result.get("trace", []), indent=2, default=str))


if __name__ == "__main__":
    main()
