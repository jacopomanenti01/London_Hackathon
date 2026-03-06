import os
from surrealdb import Surreal
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import json

from .statics import DB_URL, MICA,OLLAMA

USER = os.getenv("DB_USER", "root")
PSW = os.getenv("DB_PSW", "root")


# ── 1. Load document ──────────────────────────────────────
def load_document(path: str):
    loader = PyPDFLoader(path)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return splitter.split_documents(docs)


# ── 2. Extract entities and relationships via LLM ─────────
def extract_graph(text: str, llm) -> dict:
    prompt = PromptTemplate.from_template("""
Extract entities and relationships from the following text.
Return ONLY a JSON object with this exact structure:
{{
  "entities": [
    {{"id": "unique_id", "type": "Person|Organization|Concept|Location", "name": "entity name"}}
  ],
  "relationships": [
    {{"from": "entity_id", "to": "entity_id", "type": "relationship type"}}
  ]
}}

Text:
{text}

JSON:
""")

    chain = prompt | llm
    result = chain.invoke({"text": text})

    # extract JSON from response
    start = result.find("{")
    end = result.rfind("}") + 1
    return json.loads(result[start:end])


# ── 3. Store graph in SurrealDB ───────────────────────────
def store_graph(conn: Surreal, graph: dict):
    for entity in graph.get("entities", []):
        conn.query(f"""
            CREATE entity:{entity['id']} SET
                name = '{entity['name']}',
                type = '{entity['type']}'
        """)

    # store relationships as graph edges
    for rel in graph.get("relationships", []):
        conn.query(f"""
            RELATE entity:{rel['from']}->relationship->entity:{rel['to']}
            SET type = '{rel['type']}'
        """)


# ── 4. Query the graph ────────────────────────────────────
def query_graph(conn: Surreal, entity_name: str):
    result = conn.query(f"""
        SELECT *, ->relationship->entity.* AS related
        FROM entity
        WHERE name = '{entity_name}'
    """)
    return result


# ── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    # connect to SurrealDB
    conn = Surreal(DB_URL)
    conn.signin({"username": USER, "password": PSW})
    conn.use("langchain", "knowledge_graph")

    # load and split document
    chunks = load_document(MICA)
    print(f"Loaded {len(chunks)} chunks")

    # init LLM
    llm = OllamaLLM(model=OLLAMA)

    # extract and store graph from each chunk
    for i, chunk in enumerate(chunks):
        print(f"Processing chunk {i+1}/{len(chunks)}...")
        try:
            graph = extract_graph(chunk.page_content, llm)
            store_graph(conn, graph)
        except Exception as e:
            print(f"Skipping chunk {i+1}: {e}")

    print("✅ Knowledge graph built!")

    # example query
    results = query_graph(conn, "Jacopo")
    print("Graph query result:", results)
