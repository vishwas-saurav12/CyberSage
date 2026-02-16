def build_response(
    attack: dict,
    llm_output: dict,
    confidence: float
):
    """
    Assemble final STRICT JSON response
    """
    return {
        "attack_name": attack["name"],
        "summary": llm_output["summary"],
        "attack_vector": llm_output["attack_vector"],
        "impact": llm_output["impact"],
        "prevention": llm_output["prevention"],
        "severity": attack["severity"],
        "confidence": confidence
    }
