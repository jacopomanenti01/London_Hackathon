import os
from langchain_openai import AzureChatOpenAI
from ..utils.configs import LLM_MODEL, API_VERSION, AZURE_ENDPOINT
API_KEY = os.getenv('API_KEY')


llm = AzureChatOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    azure_deployment=LLM_MODEL,
    api_version=API_VERSION,
    api_key=API_KEY,
    temperature=0,
)

def chat(message: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage
    response = llm.invoke([
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content=message),
    ])
    return response.content


if __name__ == "__main__":
    response = chat("Apple relies on TSMC for chip manufacturing.")
    print(f"This is the response: {response}")