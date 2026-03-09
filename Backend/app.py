from fastapi import FastAPI, HTTPException # type: ignore
from pydantic import BaseModel, ValidationError
from typing import List
from fastapi.middleware.cors import CORSMiddleware   # type: ignore

import json
import os

import chromadb  # type: ignore
from sentence_transformers import SentenceTransformer  # type: ignore
from ollama import chat   # type: ignore

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
    allow_origins=["*"],  # Restrict in production
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

# Persistent Chroma Client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_collection(name="cyber_attacks")


# ==============================
# REQUEST / RESPONSE SCHEMAS
# ==============================

class QueryRequest(BaseModel):
    query: str


class LLMResponseModel(BaseModel):
    summary: str
    attack_vector: str
    impact: str
    prevention: List[str]


# ==============================
# SECURITY HELPERS
# ==============================

def is_malicious_query(query: str) -> bool:
    blocked_keywords = [
        "ignore previous instructions",
        "system prompt",
        "developer message",
        "reveal hidden",
        "print full context",
        "bypass rules",
        "show raw prompt",
    ]

    query_lower = query.lower()
    return any(keyword in query_lower for keyword in blocked_keywords)


def error_response(code: str, message: str):
    raise HTTPException(
        status_code=400,
        detail={
            "error_code": code,
            "message": message
        }
    )


# ==============================
# CHAT ENDPOINT
# ==============================

@app.post("/chat")
def chat_endpoint(payload: QueryRequest):

    query = payload.query.strip()

    # Validate query
    if not query:
        error_response(
            "EMPTY_QUERY",
            "Query cannot be empty."
        )

    # Prompt injection protection
    if is_malicious_query(query):
        error_response(
            "MALICIOUS_QUERY",
            "Query contains unsafe instructions."
        )

    # Step 1: Classify attack
    attack = classify_attack(query)

    if not attack:
        error_response(
            "CLASSIFICATION_FAILED",
            "Unable to classify attack. Please be more specific."
        )

    # Step 2: Generate embedding
    query_embedding = model.encode([query]).tolist()

    # Step 3: Retrieve relevant chunks
    chunks, distances = retrieve_chunks(
        collection=collection,
        query_embedding=query_embedding,
        attack_id=attack["attack_id"]
    )

    if not chunks:
        error_response(
            "NO_RELEVANT_CHUNKS",
            "No relevant knowledge found for this attack."
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

    # Step 7: Validate LLM JSON Output
    try:
        raw_output = json.loads(llm_response["message"]["content"])
        validated_output = LLMResponseModel(**raw_output)

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LLM_JSON_ERROR",
                "message": "LLM returned malformed JSON."
            }
        )

    except ValidationError:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LLM_SCHEMA_ERROR",
                "message": "LLM response structure invalid."
            }
        )

    # Step 8: Compute confidence
    confidence = compute_confidence(distances)

    # Step 9: Return final structured response
    return build_response(
        attack=attack,
        llm_output=validated_output.dict(),
        confidence=confidence
    )