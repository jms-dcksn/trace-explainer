import json
import operator
import re
import sys
import time
from dataclasses import replace as dataclass_replace
from pathlib import Path
from typing import Annotated, Any, Callable, NotRequired, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,  # noqa: F401  (re-exported for downstream use)
    ModelResponse,  # noqa: F401
)
from langchain.messages import AIMessage, ToolMessage
from langchain.chat_models import init_chat_model
from langchain_openai import ChatOpenAI
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime
from langgraph.types import Command
from tavily import TavilyClient
from pydantic import BaseModel

from narrator import narrate, narrate_from_messages, narrate_from_trace


# ---------------------------------------------------------------------------
# Custom agent state: keep the captured trace co-located with messages.
# ---------------------------------------------------------------------------


TraceEvent = dict[str, Any]


class TraceState(AgentState):
    """Agent state with a normalized capture trace appended via reducer."""

    trace: NotRequired[Annotated[list[TraceEvent], operator.add]]

class AgentOutput(BaseModel):
    response: str
    agent_summary: str

# ---------------------------------------------------------------------------
# Capture middleware
# ---------------------------------------------------------------------------


_TYPE_LABELS = {
    "agent_thought": "[THOUGHT]",
    "tool_call": "[TOOL CALL]",
    "tool_result": "[TOOL RESULT]",
    "final_answer": "[FINAL ANSWER]",
}


def _extract_text(content: Any) -> str:
    """Pull text out of an AIMessage's `content`, which may be a str or content blocks."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text" and "text" in block:
                    parts.append(block["text"])
        return "".join(parts).strip()
    return ""


def _truncate(text: str, limit: int = 600) -> str:
    text = str(text)
    return text if len(text) <= limit else text[:limit] + " ... [truncated]"


def _log_event(evt: TraceEvent) -> None:
    label = _TYPE_LABELS.get(evt["type"], evt["type"].upper())
    step = evt["step"]
    if evt["type"] == "tool_call":
        args_repr = json.dumps(evt["input"], default=str, ensure_ascii=False)
        print(f"\nstep {step} {label} {evt['tool']}({args_repr})")
    elif evt["type"] == "tool_result":
        print(f"\nstep {step} {label} {evt['tool']} ->\n{_truncate(evt['output'])}")
    else:
        print(f"\nstep {step} {label}\n{_truncate(evt['content'])}")


class CaptureMiddleware(AgentMiddleware):
    """Capture agent thoughts, tool calls, tool results, and final answers.

    Two hooks do the work:
      - ``after_model``: inspects the latest ``AIMessage`` to emit ``agent_thought`` and
        ``tool_call`` events (or a ``final_answer`` when no tool calls are present).
      - ``wrap_tool_call``: wraps tool execution to emit a ``tool_result`` event with
        the actual output. Returns a ``Command`` so we can both forward the
        ``ToolMessage`` and append to the trace in one update.

    The trace lives on a custom ``AgentState`` subclass (``TraceState``) under the
    ``trace`` key, with an ``operator.add`` reducer so each update appends.
    """

    state_schema = TraceState

    def after_model(
        self, state: TraceState, runtime: Runtime
    ) -> dict[str, Any] | None:
        messages = state.get("messages") or []
        if not messages:
            return None
        msg = messages[-1]
        if not isinstance(msg, AIMessage):
            return None

        prior_trace = list(state.get("trace") or [])
        next_step = len(prior_trace) + 1
        new_events: list[TraceEvent] = []

        text = _extract_text(msg.content)
        tool_calls = list(getattr(msg, "tool_calls", None) or [])

        if tool_calls:
            # Surface a "thought" even when the model emitted only tool-call blocks.
            # Without this, the trace would jump straight from the user input to
            # the tool call with no visible reasoning -- which is exactly the
            # opaqueness the explainer is supposed to fix.
            if text:
                thought = text
            else:
                names = ", ".join(tc.get("name", "?") for tc in tool_calls)
                thought = f"(no commentary) decided to call: {names}"
            new_events.append(
                {"step": next_step, "type": "agent_thought", "content": thought}
            )
            next_step += 1

            for tc in tool_calls:
                new_events.append(
                    {
                        "step": next_step,
                        "type": "tool_call",
                        "tool": tc.get("name", "?"),
                        "input": tc.get("args", {}),
                        "tool_call_id": tc.get("id"),
                    }
                )
                next_step += 1
        else:
            new_events.append(
                {"step": next_step, "type": "final_answer", "content": text}
            )

        for evt in new_events:
            _log_event(evt)

        return {"trace": new_events}

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        result = handler(request)

        # Step number reflects the trace state observed at entry. With multiple
        # parallel tool calls in a single AIMessage the numbers can collide;
        # accepted for v1 since the example task is sequential.
        prior_state = request.state if isinstance(request.state, dict) else {}
        prior_trace = list(prior_state.get("trace") or [])
        next_step = len(prior_trace) + 1

        tool_msg: ToolMessage | None = None
        output: str
        if isinstance(result, ToolMessage):
            tool_msg = result
            output = (
                result.content
                if isinstance(result.content, str)
                else json.dumps(result.content, default=str)
            )
        elif isinstance(result, Command):
            update = result.update if isinstance(result.update, dict) else {}
            for m in update.get("messages", []) or []:
                if isinstance(m, ToolMessage):
                    tool_msg = m
                    break
            output = (
                tool_msg.content
                if tool_msg is not None
                and isinstance(tool_msg.content, str)
                else json.dumps(update, default=str)
            )
        else:
            output = str(result)

        evt: TraceEvent = {
            "step": next_step,
            "type": "tool_result",
            "tool": request.tool_call.get("name", "?"),
            "tool_call_id": request.tool_call.get("id"),
            "output": output,
        }
        _log_event(evt)

        if isinstance(result, Command):
            new_update = dict(result.update) if isinstance(result.update, dict) else {}
            new_update["trace"] = list(new_update.get("trace") or []) + [evt]
            return dataclass_replace(result, update=new_update)
        # ToolMessage path: package both the tool message and the trace event
        # into a single Command update so the trace lives alongside `messages`.
        return Command(update={"messages": [result], "trace": [evt]})


# ---------------------------------------------------------------------------
# Mock CRM data + tools
# ---------------------------------------------------------------------------


ACCOUNTS_DB = [
    {
        "name": "Acme Corp",
        "account_owner": "Priya Shah",
        "tier": "Strategic",
        "arr_usd": 1_250_000,
        "products": ["Automation Cloud", "Document Understanding"],
        "renewal_date": "2026-09-15",
        "open_opportunities": 2,
        "last_qbr": "2026-02-10",
        "notes": "Expanding finance automation. Exec sponsor: CFO. Procurement is a known bottleneck.",
    },
    {
        "name": "Globex",
        "account_owner": "Marcus Lee",
        "tier": "Enterprise",
        "arr_usd": 480_000,
        "products": ["Automation Cloud"],
        "renewal_date": "2026-07-01",
        "open_opportunities": 1,
        "last_qbr": "2025-11-22",
        "notes": "Stalled expansion after CIO change. Re-engaging via new VP of Ops.",
    },
    {
        "name": "Initech",
        "account_owner": "Priya Shah",
        "tier": "Mid-Market",
        "arr_usd": 95_000,
        "products": ["Automation Cloud"],
        "renewal_date": "2026-12-01",
        "open_opportunities": 0,
        "last_qbr": None,
        "notes": "Low engagement. Single use case in HR onboarding.",
    },
]


def web_search(query: str) -> str:
    """Search the public web for recent news, financials, or general information about a company."""
    return TavilyClient().search(query)


def lookup_account(company_name: str) -> str:
    """Look up internal CRM data for an account by company name. Returns ARR, owner, products, renewal date, and notes."""
    needle = company_name.strip().lower()
    for acct in ACCOUNTS_DB:
        if acct["name"].lower() == needle or needle in acct["name"].lower():
            return str(acct)
    return f"No internal account found for '{company_name}'. Known accounts: {[a['name'] for a in ACCOUNTS_DB]}"


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------


SYSTEM_PROMPT = (
    "You are an account research assistant for a sales team. "
    "Given a company name, combine internal CRM data (via lookup_account) "
    "with recent public information (via web_search) to produce a concise "
    "account brief covering: relationship status, recent external developments, "
    "and 2-3 talking points or risks to flag for the account owner."
    "Output the response to the user query, and a summary of how you solved the query."
)


def build_agent(
    model: str,
    tools: Sequence[Callable[..., Any]] | None = None,
    extra_middleware: Sequence[AgentMiddleware] = (),
):
    """Construct the account-research agent with the capture middleware attached."""
    return create_agent(
        model=model,
        tools=list(tools) if tools is not None else [web_search, lookup_account],
        system_prompt=SYSTEM_PROMPT,
        middleware=[CaptureMiddleware(), *extra_middleware],
        response_format=AgentOutput
    )


# ---------------------------------------------------------------------------
# Exercise 4: comparison harness
# ---------------------------------------------------------------------------


# 3-5 tasks chosen to exercise a spread of agent behaviors:
#   - simple single-tool lookup
#   - canonical multi-tool brief (matches Exercise 1's default)
#   - multi-tool brief on a different account (variance check)
#   - unknown account -- forces the agent to pivot or admit ignorance
#   - comparison across two accounts -- multiple lookups + synthesis
COMPARISON_TASKS = [
    "What is the renewal date for Initech?",
    "Build me an account brief on Acme Corp.",
    "Build me an account brief on Globex.",
    "Build me an account brief on Wayne Enterprises.",
    "Compare Acme Corp and Globex on renewal risk.",
]


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:60] or "task"


def _serialize_messages_for_json(messages: list[Any]) -> list[dict[str, Any]]:
    out = []
    for m in messages:
        entry: dict[str, Any] = {
            "type": type(m).__name__,
            "content": getattr(m, "content", None),
        }
        tcs = getattr(m, "tool_calls", None)
        if tcs:
            entry["tool_calls"] = [
                {"name": tc.get("name"), "args": tc.get("args", {})} for tc in tcs
            ]
        name = getattr(m, "name", None)
        if name:
            entry["name"] = name
        out.append(entry)
    return out


def run_comparison(
    tasks: Sequence[str] = COMPARISON_TASKS,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Run each task once, narrate from trace AND from messages, write artifacts."""
    out_dir = out_dir or Path(__file__).parent / "results" / "exercise4"
    out_dir.mkdir(parents=True, exist_ok=True)

    model = ChatOpenAI(model="gpt-5.5", reasoning_effort="medium", use_responses_api=True)
    agent = build_agent(model)

    rows: list[dict[str, Any]] = []

    for i, task in enumerate(tasks, 1):
        print(f"\n{'#' * 72}\n# [{i}/{len(tasks)}] {task}\n{'#' * 72}")

        t0 = time.perf_counter()
        result = agent.invoke({"messages": [{"role": "user", "content": task}]})
        agent_latency = time.perf_counter() - t0

        trace = result.get("trace", [])
        messages = result.get("messages", [])

        print(f"\n-- narrating from trace ({len(trace)} events) --")
        from_trace = narrate_from_trace(task, trace)
        print(f"-- narrating from messages ({len(messages)} messages) --")
        from_messages = narrate_from_messages(task, messages)

        record = {
            "task": task,
            "agent_latency_s": round(agent_latency, 2),
            "trace_event_count": len(trace),
            "message_count": len(messages),
            "final_answer": (
                messages[-1].content if messages else None
            ),
            "trace": trace,
            "messages": _serialize_messages_for_json(messages),
            "from_trace": {
                "narrative": from_trace.narrative.model_dump(),
                "input_tokens": from_trace.input_tokens,
                "output_tokens": from_trace.output_tokens,
                "latency_s": round(from_trace.latency_s, 2),
            },
            "from_messages": {
                "narrative": from_messages.narrative.model_dump(),
                "input_tokens": from_messages.input_tokens,
                "output_tokens": from_messages.output_tokens,
                "latency_s": round(from_messages.latency_s, 2),
            },
        }
        rows.append(record)

        slug = f"{i:02d}-{_slug(task)}"
        (out_dir / f"{slug}.json").write_text(json.dumps(record, indent=2, default=str))
        print(f"wrote {out_dir / f'{slug}.json'}")

    summary_path = out_dir / "summary.md"
    summary_path.write_text(_render_summary(rows))
    print(f"\nwrote {summary_path}")
    return {"rows": rows, "out_dir": str(out_dir)}


def _render_summary(rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Exercise 4: Trace vs. Messages Narration\n")
    lines.append(
        "Per-task comparison of narratives produced from the structured trace "
        "(Exercise 2 contract) vs. the agent's raw messages list.\n"
    )
    lines.append("## Token / latency table\n")
    lines.append(
        "| # | Task | Trace events | Msgs | Trace in/out tok | Msgs in/out tok | Trace lat (s) | Msgs lat (s) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['task']} | {r['trace_event_count']} | {r['message_count']} | "
            f"{r['from_trace']['input_tokens']}/{r['from_trace']['output_tokens']} | "
            f"{r['from_messages']['input_tokens']}/{r['from_messages']['output_tokens']} | "
            f"{r['from_trace']['latency_s']} | {r['from_messages']['latency_s']} |"
        )

    # Totals
    t_in = sum(r["from_trace"]["input_tokens"] for r in rows)
    t_out = sum(r["from_trace"]["output_tokens"] for r in rows)
    m_in = sum(r["from_messages"]["input_tokens"] for r in rows)
    m_out = sum(r["from_messages"]["output_tokens"] for r in rows)
    lines.append(
        f"\n**Totals** -- trace: {t_in} in / {t_out} out tokens. "
        f"messages: {m_in} in / {m_out} out tokens. "
        f"Δ input: {m_in - t_in:+d} ({((m_in - t_in) / t_in * 100) if t_in else 0:+.1f}%)."
    )

    lines.append("\n## Side-by-side narratives\n")
    for i, r in enumerate(rows, 1):
        lines.append(f"### {i}. {r['task']}\n")
        lines.append("**Final answer:**\n")
        lines.append(f"> {r['final_answer']}\n")
        for label, key in (("From trace", "from_trace"), ("From messages", "from_messages")):
            n = r[key]["narrative"]
            lines.append(f"#### {label}\n")
            lines.append(f"- **Goal:** {n['goal']}")
            lines.append("- **Steps taken:**")
            for s in n["steps_taken"]:
                lines.append(f"  - {s}")
            lines.append("- **Decisions made:**")
            if n["decisions_made"]:
                for d in n["decisions_made"]:
                    lines.append(f"  - {d}")
            else:
                lines.append("  - _(none)_")
            lines.append(f"- **Summary:** {n['summary']}\n")
        lines.append("---\n")

    lines.append("## Observations\n")
    lines.append("_(fill in after reviewing the runs: which narrative is more accurate? "
                 "Where does the messages version add reasoning the trace version misses? "
                 "Where does the trace version stay cleaner? Token / latency tradeoff worth it?)_\n")
    return "\n".join(lines)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        run_comparison()
        return

    model = ChatOpenAI(model="gpt-5.5", reasoning_effort="medium", use_responses_api=True)
    agent = build_agent(model)
    task = "Build me an account brief on Acme Corp."
    result = agent.invoke({"messages": [{"role": "user", "content": task}]})

    print("\n" + "=" * 72)
    print("FINAL RESULT")
    print("=" * 72)
    print(result["messages"][-1].content)

    print("\n" + "=" * 72)
    print("CAPTURED TRACE (normalized intermediate format)")
    print("=" * 72)
    print(json.dumps(result.get("trace", []), indent=2, default=str))

    print("\n" + "=" * 72)
    print("NARRATIVE")
    print("=" * 72)
    narrative = narrate(task=task, trace=result.get("trace", []))
    print(narrative.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
