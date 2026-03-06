import pathlib

DB_URL = "ws://localhost:8000/rpc"
DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
MICA = DATA_DIR / "MICA.pdf"
OLLAMA = 'llama3.2:1b'
if __name__ == "__main__":
    print(DATA_DIR)
