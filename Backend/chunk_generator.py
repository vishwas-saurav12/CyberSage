import json


INPUT_FILE = "src/data/attacks.json"
OUTPUT_FILE = "src/data/chunks.json"


def safe_join(arr):
    if not arr:
        return "Not Available"
    return ", ".join(arr)


def list_to_bullets(arr):
    if not arr:
        return "Not Available"
    return "\n".join([f"- {item}" for item in arr])


def generate_overview_chunk(attack):
    text = f"""
Attack Name: {attack['attack_name']}
Also Known As: {safe_join(attack.get('aliases', []))}

Attack Type: {safe_join(attack.get('attack_type', []))}
Attack Vector: {attack.get('attack_vector', 'Not Available')}

Technical Overview:
{attack.get('technical_summary', 'Not Available')}

Threat Actor: {attack.get('threat_actor_type', 'Unknown')}
Attack Scale: {attack.get('attack_scale', 'Unknown')}

Tags:
{safe_join(attack.get('attack_tags', []))}
"""

    return create_chunk(attack, text, "overview")


def generate_attack_flow_chunk(attack):
    timeline = []

    for key in [
        "year",
        "patch_release_date",
        "attack_launch_period",
        "initial_compromise_period",
        "malicious_update_distribution",
        "disclosure_date",
    ]:
        if key in attack:
            timeline.append(f"{key.replace('_', ' ').title()}: {attack[key]}")

    text = f"""
Attack Execution Flow for {attack['attack_name']}

Vulnerabilities Exploited:
{list_to_bullets(attack.get('vulnerabilities_exploited', []))}

Attack Steps:
{list_to_bullets(attack.get('attack_flow', []))}

Timeline:
{list_to_bullets(timeline)}
"""

    return create_chunk(attack, text, "attack_flow")


def generate_prevention_chunk(attack):
    text = f"""
Prevention Strategies for {attack['attack_name']}

Recommended Security Measures:
{list_to_bullets(attack.get('prevention_measures', []))}

Key Lessons Learned:
{list_to_bullets(attack.get('lessons_learned', []))}
"""

    return create_chunk(attack, text, "prevention")


def generate_impact_chunk(attack):
    impact = attack.get("impact", {})

    impact_text = "\n".join(
        [f"{key.replace('_', ' ').title()}: {value}" for key, value in impact.items()]
    )

    text = f"""
Impact Analysis of {attack['attack_name']}

Affected Sectors:
{safe_join(attack.get('target_sector', []))}

Targeted Organizations:
{safe_join(attack.get('target_organizations', []))}

Attack Impact:
{impact_text}

Detection Techniques:
{list_to_bullets(attack.get('detection_method', []))}
"""

    return create_chunk(attack, text, "impact_detection")


def generate_user_guidance_chunk(attack):
    text = f"""
User Safety Guidance Based on {attack['attack_name']}

Recommended Personal Safety Actions:
{list_to_bullets(attack.get('user_safety_tips', []))}
"""

    return create_chunk(attack, text, "user_guidance")


def create_chunk(attack, text, chunk_type):
    return {
        "text": text.strip(),
        "metadata": {
            "attack_id": attack["attack_id"],
            "attack_name": attack["attack_name"],
            "chunk_type": chunk_type,
            "attack_type": attack.get("attack_type", []),
            "severity_level": attack.get("severity_level", "Unknown"),
        },
    }


def generate_chunks(attacks):
    chunks = []

    for attack in attacks:
        chunks.append(generate_overview_chunk(attack))
        chunks.append(generate_attack_flow_chunk(attack))
        chunks.append(generate_prevention_chunk(attack))
        chunks.append(generate_impact_chunk(attack))
        chunks.append(generate_user_guidance_chunk(attack))

    return chunks


def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        attacks = json.load(f)

    chunks = generate_chunks(attacks)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2)

    print(f"✅ Generated {len(chunks)} chunks")


if __name__ == "__main__":
    main()
