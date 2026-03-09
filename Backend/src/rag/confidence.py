def compute_confidence(distances):

    if not distances:
        return 0.0

    # Convert distance to similarity
    similarities = [1 - d for d in distances]

    avg_similarity = sum(similarities) / len(similarities)

    return round(avg_similarity, 2)