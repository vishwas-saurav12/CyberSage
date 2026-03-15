from fastapi import FastAPI, HTTPException  # type: ignore
from pydantic import BaseModel, ValidationError
from typing import List
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from collections import deque

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
    allow_origins=["*"],  # restrict later in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================
# PATH & DATABASE
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_DB_PATH = os.path.join(BASE_DIR, "chroma_db")

# Load embedding model once
model = SentenceTransformer("all-MiniLM-L6-v2")

# Persistent Chroma client
client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
collection = client.get_collection(name="cyber_attacks")


# ==============================
# CONVERSATION MEMORY
# ==============================

conversation_memory = deque(maxlen=6)


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


def build_memory_context():
    if not conversation_memory:
        return ""

    history = "\n".join(conversation_memory)

    return f"""
Conversation History:
{history}
"""


# ==============================
# CHAT ENDPOINT
# ==============================

@app.post("/chat")
def chat_endpoint(payload: QueryRequest):

    query = payload.query.strip()

    # ==============================
    # Validation
    # ==============================

    if not query:
        error_response("EMPTY_QUERY", "Query cannot be empty.")

    if is_malicious_query(query):
        error_response("MALICIOUS_QUERY", "Query contains unsafe instructions.")

    # Save user query to memory
    conversation_memory.append(f"User: {query}")

    # ==============================
    # Step 1 — Attack classification
    # ==============================

    attack = classify_attack(query)

    if not attack:
        error_response(
            "CLASSIFICATION_FAILED",
            "Unable to classify attack. Please be more specific."
        )

    # ==============================
    # Step 2 — Query embedding
    # ==============================

    query_embedding = model.encode([query]).tolist()

    # ==============================
    # Step 3 — Retrieve chunks
    # ==============================

    try:
        chunks, distances = retrieve_chunks(
            collection=collection,
            query_embedding=query_embedding,
            attack_id=attack["attack_id"]
        )

    except Exception:
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

    # ==============================
    # Step 4 — Smart chunk ranking
    # ==============================

    ranked_chunks = sorted(
        zip(chunks, distances),
        key=lambda x: x[1]
    )

    top_chunks = [c for c, _ in ranked_chunks[:3]]
    top_distances = [d for _, d in ranked_chunks[:3]]

    context = "\n\n".join(top_chunks)

    # ==============================
    # Step 5 — Prompt
    # ==============================

    memory_context = build_memory_context()

    prompt = f"""
You are a cybersecurity analyst.

{memory_context}

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

    # ==============================
    # Step 6 — Call Ollama
    # ==============================

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

    # ==============================
    # Step 7 — Extract JSON safely
    # ==============================

    try:
        json_start = content.find("{")
        json_end = content.rfind("}") + 1

        if json_start == -1 or json_end == -1:
            raise ValueError("JSON not found")

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

    # ==============================
    # Step 8 — Validate schema
    # ==============================

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

    # ==============================
    # Step 9 — Compute confidence
    # ==============================

    confidence = compute_confidence(top_distances)

    # ==============================
    # Save assistant response
    # ==============================

    conversation_memory.append(
        f"Assistant: {validated_output.summary}"
    )

    # ==============================
    # Step 10 — Final response
    # ==============================

    return build_response(
        attack=attack,
        llm_output=validated_output.dict(),
        confidence=confidence
    )