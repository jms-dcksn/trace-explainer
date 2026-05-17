# Trace Explainer

A small Streamlit app that runs an account-research agent live, captures its trajectory through middleware, and uses a second LLM to turn that trajectory into a structured writeup a non-engineer can actually review.

## The thesis

Agents are bad at explaining themselves, and SMEs can't approve what they can't read.

A correct-looking final answer can come from a wrong process: hallucinated lookups, skipped checks, the agent guessing instead of searching. Judging on output alone is a thin signal. The **trajectory** is where the agent is actually right or wrong -- did it consult the CRM before pricing, did it cross-check the renewal date, did it pivot sensibly when the account wasn't found. Those are the questions an SME can answer, if they can see them.

Raw traces and JSON are the right substrate (complete, ordered, typed) but no one in compliance, finance, or sales ops is going to read `tool_call` events. The intermediate JSON is the *contract*, not the *interface*.

So the pipeline is:

```
Agent run -> Capture middleware -> Intermediate JSON -> Narrator LLM -> Structured narrative
```

The capture middleware is a LangChain 1.0 `AgentMiddleware` that emits typed events (`agent_thought`, `tool_call`, `tool_result`, `final_answer`) into agent state. The narrator is a separate LLM call with structured output (`goal`, `steps_taken`, `decisions_made`, `summary`). The Streamlit UI puts the agent's own final answer next to the narrator's writeup so you can see the quality gap in one glance.

## What I learned building it

- **Trajectory feedback is a vector; output thumbs are one bit.** A "this step was wrong" comment from an SME is far better eval/training signal than a thumbs-down on the final answer.
- **Structured-trace vs. raw-messages narratives are visibly different.** The app has a toggle between `narrate_from_trace` and `narrate_from_messages` so you can see it on the same turn. Structured traces are less token-intensive on longer agent runs.

## Run it locally

Requires Python 3.13+ and [`uv`](https://docs.astral.sh/uv/).

```bash
git clone <repo> && cd trace-explainer
uv sync

export OPENAI_API_KEY=sk-...
export TAVILY_API_KEY=tvly-...

uv run streamlit run app.py
```

The app opens at `http://localhost:8501`. Try a preset chip ("Build me an account brief on Acme Corp") or type your own. Watch tool-call cards stream in as the agent runs, then compare the agent's own final answer to the narrator's structured writeup on the right. Toggle the narrative source between `Trace` and `Messages` to see the substrate difference.

There's also a CLI entrypoint if you want the trajectory without the UI:

```bash
uv run python main.py "Build me an account brief on Acme Corp"
```

## Files

- `main.py` -- agent, tools, `CaptureMiddleware`, CLI runner
- `narrator.py` -- `narrate_from_trace` and `narrate_from_messages`
- `app.py` -- Streamlit UI
- `SPEC.md` -- design doc for the UI
- `REFLECTIONS.md` -- running notes on what the project is actually for
