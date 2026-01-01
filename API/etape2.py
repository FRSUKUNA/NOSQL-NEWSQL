import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Union

# ==============================
# CONFIGURATION
# ==============================
INPUT_DIR = "sources"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# DICTIONNAIRE INTELLIGENT (IA MÉTIER)
# ==============================
CATEGORIES = {
    "performance": [
        "performance", "optimize", "latency", "throughput",
        "scalability", "speed", "faster", "timeout","feduce",
        "metrics", "eviction","improve","efficiency","improving"
    ],
    "bug_fix": [
        "fix", "bug","bugs", "crash", "hang", "race","fixed",
        "deadlock", "error", "fail", "issue","freaking fixes"
        "incorrect"
    ],
    "new_feature": [
        "add", "introduce", "new", "support","added",
        "enable", "feature", "initial", "allow"
    ],
    "security": [
        "security", "auth", "authentication",
        "authorization", "permission",
        "vulnerability", "cve", "encryption","secure",
        "sast"
    ]
}

# ==============================
# CLASSIFICATION D'UN CHANGEMENT
# ==============================
def classify_change(text: str) -> str:
    text = text.lower()
    scores = defaultdict(int)

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if re.search(rf"\b{kw}\b", text):
                scores[category] += 1

    if not scores:
        return "other"

    return max(scores, key=scores.get)

# ==============================
# ANALYSE D'UN PATCH COMPLET
# ==============================
def analyze_patch(patch: Dict) -> Dict:
    summary = {
        "performance": 0,
        "bug_fix": 0,
        "new_feature": 0,
        "security": 0,
        "other": 0
    }

    details = []

    for change in patch.get("changes", []):
        category = classify_change(change)
        summary[category] += 1
        details.append({
            "description": change,
            "category": category
        })

    patch["ai_analysis"] = {
        "dominant_type": max(summary, key=summary.get),
        "summary": summary,
        "details": details
    }

    return patch

# ==============================
# TRAITEMENT DES FICHIERS JSON
# ==============================
def process_files():
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(".json"):
            continue

        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Cas 1 : liste de patches
        if isinstance(data, list):
            analyzed_data = [analyze_patch(patch) for patch in data]

        # Cas 2 : un seul patch
        elif isinstance(data, dict):
            analyzed_data = analyze_patch(data)

        else:
            print(f"❌ Format inconnu : {filename}")
            continue

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analyzed_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Analyse IA terminée : {filename}")

# ==============================
# POINT D'ENTRÉE
# ==============================
if __name__ == "__main__":
    print("🚀 Démarrage analyse IA des patchs...\n")
    process_files()
    print("\n🎯 Analyse terminée. Fichiers enrichis dans /output")
