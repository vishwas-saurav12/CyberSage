from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel
import json
import os

import chromadb # type: ignore
from sentence_transformers import SentenceTransformer # type: ignore
from ollama import chat # type: ignore

from src.core.attack_classifier import classify_attack
from src.rag.retriever import retrieve_chunks
from src.rag.confidence import compute_confidence
from src.rag.response_builder import build_response

# ------------------ PATH SETUP ------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# ------------------ APP SETUP ------------------

app = FastAPI()

model = SentenceTransformer("all-MiniLM-L6-v2")

# IMPORTANT: PersistentClient (must match embedding pipeline)
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_collection(name="cyber_attacks")

# ------------------ SCHEMA ------------------

class QueryRequest(BaseModel):
    query: str

# ------------------ ENDPOINT ------------------

@app.post("/chat")
def chat_endpoint(payload: QueryRequest):
    query = payload.query.strip()

    attack = classify_attack(query)
    if not attack:
        raise HTTPException(
            status_code=400,
            detail="Unable to classify attack. Please be more specific."
        )

    query_embedding = model.encode([query]).tolist()

    chunks = retrieve_chunks(
        collection=collection,
        query_embedding=query_embedding,
        attack_id=attack["attack_id"]
    )

    if not chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant knowledge found."
        )

    context = "\n\n".join(chunks)

    prompt = f"""
You are a cybersecurity analyst.
Answer STRICTLY in valid JSON.
Do NOT include markdown or explanations.

Context:
{context}

Return JSON with:
summary (string)
attack_vector (string)
impact (string)
prevention (array of strings)
"""

    llm_response = chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    llm_output = json.loads(llm_response["message"]["content"])

    confidence = compute_confidence(len(chunks))

    return build_response(
        attack=attack,
        llm_output=llm_output,
        confidence=confidence
    )
