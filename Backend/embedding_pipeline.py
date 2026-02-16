import json
import os
import chromadb # type: ignore
from sentence_transformers import SentenceTransformer # type: ignore

# ------------------ PATH SETUP ------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
CHUNKS_PATH = os.path.join(BASE_DIR, "src", "data", "chunks.json")

# ------------------ CHROMA CLIENT ------------------

client = chromadb.PersistentClient(path=CHROMA_PATH)

# IMPORTANT: wipe existing collection to avoid duplicates
try:
    client.delete_collection(name="cyber_attacks")
except Exception:
    pass  # collection may not exist yet

collection = client.get_or_create_collection(name="cyber_attacks")

# ------------------ MODEL ------------------

model = SentenceTransformer("all-MiniLM-L6-v2")

# ------------------ LOAD CHUNKS ------------------

with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
    chunks = json.load(f)

if not isinstance(chunks, list):
    raise ValueError("chunks.json must contain a list of chunk objects")

documents = []
metadatas = []
ids = []

for i, chunk in enumerate(chunks):
    if "text" not in chunk or "metadata" not in chunk:
        raise ValueError(f"Invalid chunk format at index {i}")

    documents.append(chunk["text"])

    metadata = chunk["metadata"]
    cleaned_metadata = {}

    for key, value in metadata.items():
        if isinstance(value, list):
            cleaned_metadata[key] = ", ".join(map(str, value))
        else:
            cleaned_metadata[key] = value

    metadatas.append(cleaned_metadata)
    ids.append(f"chunk_{i}")

# ------------------ EMBEDDINGS ------------------

embeddings = model.encode(documents).tolist()

collection.add(
    documents=documents,
    embeddings=embeddings,
    metadatas=metadatas,
    ids=ids
)

# ------------------ CONFIRMATION ------------------

print(f"✅ Stored {len(documents)} chunks into ChromaDB")
print(f"📂 Database Path: {CHROMA_PATH}")
