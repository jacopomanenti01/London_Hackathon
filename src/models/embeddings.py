import os
from langchain_openai import AzureOpenAIEmbeddings
from ..utils.configs import EMBEDDING_MODEL, API_VERSION, AZURE_ENDPOINT
API_KEY = os.getenv('API_KEY')



embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_ENDPOINT,
    azure_deployment=EMBEDDING_MODEL,
    api_version=API_VERSION,
    api_key=API_KEY,
)


def embed(text: str) -> list[float]:
    return embeddings.embed_query(text)


if __name__ == "__main__":
    vector = embed("Apple relies on TSMC for chip manufacturing.")
    print(f"Embedding dim: {len(vector)}")