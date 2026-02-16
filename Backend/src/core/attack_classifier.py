from .attack_registry import ATTACK_REGISTRY

def classify_attack(query: str):
    q = query.lower()

    for attack in ATTACK_REGISTRY.values():
        for alias in attack["aliases"]:
            if alias in q:
                return attack

    return None
