import os
import requests
import chromadb
from sentence_transformers import SentenceTransformer

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

# Connect to Chroma
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(name="cyber_attacks")

# Load embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "mistral"


def retrieve_context(query):
    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    context = "\n\n".join(results["documents"][0])
    return context


def generate_answer(query, context):

    prompt = f"""
You are a cybersecurity expert AI assistant.

Use ONLY the context below to answer the question.
If the answer is not in the context, say you don't know.

Context:
{context}

Question:
{query}

Answer clearly and professionally:
"""

    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        }
    )

    return response.json()["response"]


while True:
    query = input("\nAsk question (type 'exit' to quit): ")

    if query.lower() == "exit":
        break

    context = retrieve_context(query)
    answer = generate_answer(query, context)

    print("\n🧠 AI Response:\n")
    print(answer)
    print("\n" + "="*50)