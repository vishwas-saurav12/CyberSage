from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import json
import os

import chromadb
from sentence_transformers import SentenceTransformer
from ollama import chat

from src.core.attack_classifier import classify_attack
from src.rag.retriever import retrieve_chunks
from src.rag.confidence import compute_confidence
from src.rag.response_builder import build_response


# ==============================
# APP INITIALIZATION
# ==============================

app = FastAPI()

# CORS Middleware (Required for Web + Phone)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Use specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# PATH & DATABASE SETUP
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# Load embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")

# Persistent Chroma Client (must match embedding pipeline)
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_collection(name="cyber_attacks")


# ==============================
# REQUEST SCHEMA
# ==============================

class QueryRequest(BaseModel):
    query: str


# ==============================
# CHAT ENDPOINT
# ==============================

@app.post("/chat")
def chat_endpoint(payload: QueryRequest):
    query = payload.query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query cannot be empty."
        )

    # Step 1: Classify attack
    attack = classify_attack(query)
    if not attack:
        raise HTTPException(
            status_code=400,
            detail="Unable to classify attack. Please be more specific."
        )

    # Step 2: Generate embedding
    query_embedding = model.encode([query]).tolist()

    # Step 3: Retrieve relevant chunks
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

    # Step 4: Build context
    context = "\n\n".join(chunks)

    # Step 5: LLM Prompt
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

    # Step 6: Call Local LLM (Ollama)
    llm_response = chat(
        model="mistral",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0}
    )

    try:
        llm_output = json.loads(llm_response["message"]["content"])
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="LLM returned invalid JSON."
        )

    # Step 7: Compute confidence
    confidence = compute_confidence(len(chunks))

    # Step 8: Build final structured response
    return build_response(
        attack=attack,
        llm_output=llm_output,
        confidence=confidence
    )