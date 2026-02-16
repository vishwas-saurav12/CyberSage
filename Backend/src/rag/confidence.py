def compute_confidence(num_chunks: int) -> float:
    """
    Simple, honest confidence calculation.
    Never returns 1.0
    """
    base = 0.6
    increment = num_chunks * 0.05
    return round(min(0.85, base + increment), 2)
