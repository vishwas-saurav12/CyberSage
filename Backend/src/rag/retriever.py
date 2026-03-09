def retrieve_chunks(collection, query_embedding, attack_id):

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=5,
        where={"attack_id": attack_id}
    )

    documents = results["documents"][0]
    distances = results["distances"][0]

    return documents, distances