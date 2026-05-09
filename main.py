from langchain_core.callbacks import BaseCallbackHandler
from typing import Any, Dict, List
# Usage with a Chat Model
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from tavily import TavilyClient


class MyCustomHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs: Any) -> Any:
        print(f"🚀 LLM started with prompt: {prompts[0]}")

    def on_llm_end(self, response: Any, **kwargs: Any) -> Any:
        print("✅ LLM finished generating!")

tavily_client = TavilyClient()

def web_search(query: str, max_results: int) -> str:
    """Run a web search"""
    return tavily_client.search(query)

handler = MyCustomHandler()
model = ChatOpenAI(name="gpt-4.1", callbacks=[handler])
agent = create_agent(
        model=model,
        tools=[web_search],
        system_prompt="You are a helpful assistant named Tom."
    )

def main():    
    result = agent.invoke({"messages": [{"role": "user", "content": "What's the weather in Port Aransas?"}]})
    print(result["messages"][-1].content_blocks)


if __name__ == "__main__":
    main()
