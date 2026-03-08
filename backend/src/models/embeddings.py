import os
from pydantic import SecretStr
from langchain_openai import AzureOpenAIEmbeddings
from ..utils.configs import EMBEDDING_MODEL, API_VERSION, AZURE_ENDPOINT

_embeddings = None


def get_embeddings() -> AzureOpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _raw_key = os.getenv('API_KEY')
        api_key = SecretStr(_raw_key) if _raw_key else None
        _embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=AZURE_ENDPOINT,
            azure_deployment=EMBEDDING_MODEL,
            api_version=API_VERSION,
            api_key=api_key,
        )
    return _embeddings


# Backward-compatible module-level access
class _LazyEmbeddings:
    def __getattr__(self, name):
        return getattr(get_embeddings(), name)

embeddings = _LazyEmbeddings()


def embed(text: str) -> list[float]:
    return get_embeddings().embed_query(text)


if __name__ == "__main__":
    vector = embed("Apple relies on TSMC for chip manufacturing.")
    print(f"Embedding dim: {len(vector)}")
