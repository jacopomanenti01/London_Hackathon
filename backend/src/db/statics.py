import os

DB_URL = "ws://localhost:8000/rpc"
MICA = os.getenv("DOCUMENT_PATH", "")
OLLAMA = os.getenv("OLLAMA_MODEL", "llama3")
