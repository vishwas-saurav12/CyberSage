import os
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

# Use PersistentClient (IMPORTANT)
client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_collection(name="cyber_attacks")

model = SentenceTransformer("all-MiniLM-L6-v2")

print("✅ Connected to Cyber Attack Knowledge Base")

while True:
    query = input("\nAsk question (type 'exit' to quit): ")

    if query.lower() == "exit":
        break

    query_embedding = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=3
    )

    print("\n🔎 Top Matching Knowledge:\n")

    for doc in results["documents"][0]:
        print(doc)
        print("\n-------------------------\n")
