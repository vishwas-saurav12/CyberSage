def retrieve_chunks(collection, query_embedding, attack_id: str, top_k: int = 5):
    """
    Retrieve only chunks related to a specific attack_id
    """
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        where={"attack_id": attack_id}
    )

    documents = results.get("documents", [[]])[0]
    return documents
