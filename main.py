from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from tavily import TavilyClient


class MyCustomHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        print(f"LLM started with prompt: {prompts[0]}")

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        print("LLM finished generating!")


# Mock internal CRM/account database
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


tavily_client = TavilyClient()


def web_search(query: str) -> str:
    """Search the public web for recent news, financials, or general information about a company."""
    return tavily_client.search(query)


def lookup_account(company_name: str) -> str:
    """Look up internal CRM data for an account by company name. Returns ARR, owner, products, renewal date, and notes."""
    needle = company_name.strip().lower()
    for acct in ACCOUNTS_DB:
        if acct["name"].lower() == needle or needle in acct["name"].lower():
            return str(acct)
    return f"No internal account found for '{company_name}'. Known accounts: {[a['name'] for a in ACCOUNTS_DB]}"


handler = MyCustomHandler()
model = ChatOpenAI(name="gpt-4.1", callbacks=[handler])
agent = create_agent(
    model=model,
    tools=[web_search, lookup_account],
    system_prompt=(
        "You are an account research assistant for a sales team. "
        "Given a company name, combine internal CRM data (via lookup_account) "
        "with recent public information (via web_search) to produce a concise "
        "account brief covering: relationship status, recent external developments, "
        "and 2-3 talking points or risks to flag for the account owner."
    ),
)


def main():
    result = agent.invoke(
        {"messages": [{"role": "user", "content": "Build me an account brief on Acme Corp."}]}
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
