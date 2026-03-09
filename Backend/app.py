from fastapi import FastAPI, HTTPException  # type: ignore
from pydantic import BaseModel, ValidationError
from typing import List
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

import json
import os

import chromadb  # type: ignore
from sentence_transformers import SentenceTransformer  # type: ignore
from ollama import chat  # type: ignore

from src.core.attack_classifier import classify_attack
from src.rag.retriever import retrieve_chunks
from src.rag.confidence import compute_confidence
from src.rag.response_builder import build_response


# ==============================
# APP INITIALIZATION
# ==============================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# PATH & DATABASE
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

model = SentenceTransformer("all-MiniLM-L6-v2")

client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_collection(name="cyber_attacks")


# ==============================
# SCHEMAS
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

    if not query:
        error_response("EMPTY_QUERY", "Query cannot be empty.")

    if is_malicious_query(query):
        error_response("MALICIOUS_QUERY", "Query contains unsafe instructions.")

    # Step 1 — Attack classification
    attack = classify_attack(query)

    if not attack:
        error_response(
            "CLASSIFICATION_FAILED",
            "Unable to classify attack. Please be more specific."
        )

    # Step 2 — Query embedding
    query_embedding = model.encode([query]).tolist()

    # Step 3 — Retrieve chunks
    try:
        chunks, distances = retrieve_chunks(
            collection=collection,
            query_embedding=query_embedding,
            attack_id=attack["attack_id"]
        )
    except Exception:
        # fallback in case retriever returns only chunks
        chunks = retrieve_chunks(
            collection=collection,
            query_embedding=query_embedding,
            attack_id=attack["attack_id"]
        )
        distances = [0.5] * len(chunks)

    if not chunks:
        error_response(
            "NO_RELEVANT_CHUNKS",
            "No relevant knowledge found."
        )

    # Step 4 — Context creation
    context = "\n\n".join(chunks[:3])

    # Step 5 — Prompt
    prompt = f"""
You are a cybersecurity analyst.

Use the provided context to answer the question.

Rules:
- Only use the context
- Do not invent information
- Return STRICT JSON
- No explanations outside JSON

Context:
{context}

Return JSON:

{{
"summary": "short explanation of the attack",
"attack_vector": "how the attack spreads",
"impact": "what damage the attack causes",
"prevention": ["step1","step2","step3"]
}}
"""

    # Step 6 — Call Ollama
    try:
        llm_response = chat(
            model="llama3.2:3b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0}
        )

        content = llm_response["message"]["content"].strip()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama generation failed: {str(e)}"
        )

    # Step 7 — Extract JSON safely
    try:
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        json_text = content[json_start:json_end]

        raw_output = json.loads(json_text)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LLM_JSON_ERROR",
                "message": "Model returned invalid JSON."
            }
        )

    # Step 8 — Validate structure
    try:
        validated_output = LLMResponseModel(**raw_output)

    except ValidationError:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "LLM_SCHEMA_ERROR",
                "message": "LLM response schema invalid."
            }
        )

    # Step 9 — Compute confidence
    confidence = compute_confidence(distances)

    # Step 10 — Final response
    return build_response(
        attack=attack,
        llm_output=validated_output.dict(),
        confidence=confidence
    )