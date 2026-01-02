import json
import os
import re
from collections import Counter
from etape2 import CATEGORIES

def extract_remaining_other():
    """Extrait les descriptions encore classées comme 'other' avec les nouveaux mots-clés"""
    from etape2 import classify_change
    
    remaining_other = []
    
    for filename in os.listdir("output"):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join("output", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = data if isinstance(data, list) else [data]
        
        for item in items:
            if "ai_analysis" in item and "details" in item["ai_analysis"]:
                for detail in item["ai_analysis"]["details"]:
                    # Tester avec la classification actuelle
                    category = classify_change(detail["description"])
                    if category == "other":
                        remaining_other.append(detail["description"])
    
    return remaining_other

def analyze_remaining_patterns(descriptions):
    """Analyse les motifs dans les descriptions restantes pour trouver des mots-clés manquants"""
    
    # Mots-clés suggérés pour chaque catégorie existante
    performance_keywords = [
        "lazy", "eager", "allocation", "reduce", "optimize", "fast", "efficient",
        "improve", "cache", "memory", "throughput", "latency", "speed", "scalability",
        "contention", "bottleneck", "overhead", "resource", "cpu", "io", "disk",
        "network", "bandwidth", "compression", "decompression", "serialize", "deserialize"
    ]
    
    bug_fix_keywords = [
        "incorrect", "properly", "missing", "wrong", "broken", "exception", "null",
        "empty", "invalid", "fail", "failure", "crash", "hang", "deadlock", "race",
        "leak", "overflow", "underflow", "corrupt", "damage", "uninitialized", "unbound",
        "undefined", "malformed", "truncated", "incomplete", "stale", "outdated", "deprecated"
    ]
    
    new_feature_keywords = [
        "create", "implement", "provide", "extend", "offer", "introduce", "enable",
        "support", "allow", "add", "introduce", "export", "import", "generate", "build",
        "construct", "establish", "setup", "configure", "initialize", "register", "subscribe"
    ]
    
    security_keywords = [
        "secure", "protect", "validate", "verify", "check", "control", "restrict",
        "authenticate", "authorize", "encrypt", "decrypt", "hash", "sign", "verify",
        "audit", "permission", "access", "login", "password", "token", "certificate",
        "firewall", "filter", "block", "prevent", "detect", "alert", "monitor"
    ]
    
    # Analyser les descriptions restantes
    remaining_text = " ".join(descriptions).lower()
    
    suggestions = {
        "performance": [],
        "bug_fix": [],
        "new_feature": [],
        "security": []
    }
    
    # Chercher les mots-clés manquants dans chaque catégorie
    for keyword in performance_keywords:
        if keyword in remaining_text and keyword not in CATEGORIES["performance"]:
            count = remaining_text.count(keyword)
            if count > 5:  # Seulement si apparaît fréquemment
                suggestions["performance"].append((keyword, count))
    
    for keyword in bug_fix_keywords:
        if keyword in remaining_text and keyword not in CATEGORIES["bug_fix"]:
            count = remaining_text.count(keyword)
            if count > 5:
                suggestions["bug_fix"].append((keyword, count))
    
    for keyword in new_feature_keywords:
        if keyword in remaining_text and keyword not in CATEGORIES["new_feature"]:
            count = remaining_text.count(keyword)
            if count > 5:
                suggestions["new_feature"].append((keyword, count))
    
    for keyword in security_keywords:
        if keyword in remaining_text and keyword not in CATEGORIES["security"]:
            count = remaining_text.count(keyword)
            if count > 5:
                suggestions["security"].append((keyword, count))
    
    return suggestions

def main():
    print("🔍 Analyse des descriptions restantes dans 'other'...")
    remaining_other = extract_remaining_other()
    print(f"📊 Encore {len(remaining_other)} descriptions dans 'other'")
    
    print("\n🔤 Analyse des motifs pour trouver des mots-clés manquants...")
    suggestions = analyze_remaining_patterns(remaining_other)
    
    print("\n💡 Suggestions de mots-clés à ajouter aux catégories existantes:")
    
    total_new_keywords = 0
    for category, keywords in suggestions.items():
        if keywords:
            print(f"\n📂 {category.upper()}:")
            # Trier par fréquence
            keywords.sort(key=lambda x: x[1], reverse=True)
            for keyword, freq in keywords[:15]:  # Top 15 par catégorie
                print(f"  - {keyword} (fréquence: {freq})")
                total_new_keywords += 1
    
    print(f"\n📈 Total suggestions: {total_new_keywords} nouveaux mots-clés")
    
    # Générer le code CATEGORIES mis à jour
    print("\n🔄 Génération du CATEGORIES enrichi:")
    print("CATEGORIES = {")
    
    # Catégories existantes avec nouveaux mots-clés
    categories_with_new = {
        "performance": ["lazy", "eager", "allocation", "reduce", "optimize", "fast", "efficient", "improve", "cache", "memory", "throughput", "latency", "speed", "scalability", "contention", "bottleneck", "overhead", "resource", "cpu", "io", "disk", "network", "bandwidth", "compression", "decompression", "serialize", "deserialize"],
        "bug_fix": ["incorrect", "properly", "missing", "wrong", "broken", "exception", "null", "empty", "invalid", "fail", "failure", "crash", "hang", "deadlock", "race", "leak", "overflow", "underflow", "corrupt", "damage", "uninitialized", "unbound", "undefined", "malformed", "truncated", "incomplete", "stale", "outdated", "deprecated"],
        "new_feature": ["create", "implement", "provide", "extend", "offer", "introduce", "enable", "support", "allow", "add", "export", "import", "generate", "build", "construct", "establish", "setup", "configure", "initialize", "register", "subscribe"],
        "security": ["secure", "protect", "validate", "verify", "check", "control", "restrict", "authenticate", "authorize", "encrypt", "decrypt", "hash", "sign", "audit", "permission", "access", "login", "password", "token", "certificate", "firewall", "filter", "block", "prevent", "detect", "alert", "monitor"]
    }
    
    for category, new_keywords in categories_with_new.items():
        # Filtrer seulement les mots-clés qui apparaissent vraiment
        relevant_keywords = [kw for kw in new_keywords if any(kw in desc.lower() for desc in remaining_other[:1000])]  # Échantillon pour performance
        
        if relevant_keywords:
            print(f'    "{category}": [')
            # Garder les mots-clés existants
            existing_keywords = CATEGORIES.get(category, [])
            for kw in existing_keywords:
                print(f'        "{kw}",')
            # Ajouter les nouveaux
            for kw in relevant_keywords[:10]:  # Limiter à 10 nouveaux par catégorie
                print(f'        "{kw}",')
            print("    ],")
    
    print("}")

if __name__ == "__main__":
    main()
