import os
from pydantic import SecretStr
from langchain_openai import AzureChatOpenAI
from ..utils.configs import LLM_MODEL, API_VERSION, AZURE_ENDPOINT

_llm = None


def get_llm() -> AzureChatOpenAI:
    global _llm
    if _llm is None:
        _llm = AzureChatOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            azure_deployment=LLM_MODEL,
            api_version=API_VERSION,
            api_key=SecretStr(k) if (k := os.getenv("API_KEY")) else None,
            temperature=0,
        )
    return _llm


# Backward-compatible module-level access
class _LazyLLM:
    def __getattr__(self, name):
        return getattr(get_llm(), name)

llm = _LazyLLM()


def chat(message: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage
    response = get_llm().invoke([
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content=message),
    ])
    return str(response.content)


if __name__ == "__main__":
    response = chat("Apple relies on TSMC for chip manufacturing.")
    print(f"This is the response: {response}")