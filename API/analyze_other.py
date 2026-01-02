import json
import re
from collections import Counter, defaultdict
import os

def extract_other_descriptions():
    """Extrait toutes les descriptions classées comme 'other' des fichiers JSON"""
    other_descriptions = []
    
    # Parcourir tous les fichiers JSON dans le dossier output
    for filename in os.listdir("output"):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join("output", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Traiter les données (liste ou dictionnaire)
        items = data if isinstance(data, list) else [data]
        
        for item in items:
            if "ai_analysis" in item and "details" in item["ai_analysis"]:
                for detail in item["ai_analysis"]["details"]:
                    if detail["category"] == "other":
                        other_descriptions.append(detail["description"])
    
    return other_descriptions

def extract_keywords(text):
    """Extrait les mots-clés pertinents d'un texte"""
    # Convertir en minuscules
    text = text.lower()
    
    # Extraire les mots significatifs (plus de 2 caractères)
    words = re.findall(r'\b[a-z]{3,}\b', text)
    
    # Filtrer les mots communs non pertinents
    stop_words = {
        'the', 'and', 'for', 'are', 'with', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 
        'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new',
        'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'use', 'her', 'him', 'his',
        'let', 'put', 'say', 'she', 'too', 'very', 'when', 'your', 'cassandra', 'mongodb',
        'redis', 'neo4j', 'cockroachdb', 'tidb', 'yugabyte', 'database', 'version', 'patch',
        'update', 'support', 'allow', 'enable', 'introduce', 'add', 'fix', 'bug', 'error',
        'issue', 'fail', 'crash', 'hang', 'race', 'deadlock', 'performance', 'optimize',
        'latency', 'throughput', 'scalability', 'speed', 'faster', 'timeout', 'metrics',
        'security', 'auth', 'authentication', 'authorization', 'permission', 'vulnerability',
        'cve', 'encryption', 'secure', 'feature', 'new', 'initial'
    }
    
    return [word for word in words if word not in stop_words]

def suggest_categories(keywords_freq):
    """Suggère des catégories basées sur les mots-clés fréquents"""
    suggestions = {
        "performance": [],
        "bug_fix": [],
        "new_feature": [],
        "security": [],
        "refactoring": [],
        "maintenance": [],
        "monitoring": [],
        "configuration": [],
        "testing": [],
        "documentation": []
    }
    
    # Mots-clés typiques par catégorie
    category_keywords = {
        "performance": ["reduce", "improve", "optimize", "cache", "memory", "allocation", "fast", "efficient", "contention", "throughput"],
        "bug_fix": ["incorrect", "properly", "missing", "wrong", "broken", "fail", "exception", "null", "empty", "invalid"],
        "new_feature": ["extend", "implement", "create", "provide", "offer", "introduce", "enable", "support"],
        "security": ["protect", "validate", "check", "verify", "secure", "restrict", "control"],
        "refactoring": ["refactor", "restructure", "reorganize", "cleanup", "simplify", "modularize"],
        "maintenance": ["upgrade", "migrate", "compatibility", "deprecated", "remove", "replace"],
        "monitoring": ["metric", "log", "track", "monitor", "observe", "report", "statistics"],
        "configuration": ["config", "setting", "option", "parameter", "property", "tune"],
        "testing": ["test", "verify", "validate", "check", "assert"],
        "documentation": ["document", "comment", "explain", "guide", "readme"]
    }
    
    for keyword, freq in keywords_freq.items():
        for category, related_keywords in category_keywords.items():
            if keyword in related_keywords:
                suggestions[category].append((keyword, freq))
    
    return suggestions

def main():
    print("🔍 Extraction des descriptions classées comme 'other'...")
    other_descriptions = extract_other_descriptions()
    print(f"📊 Trouvé {len(other_descriptions)} descriptions classées comme 'other'")
    
    print("\n🔤 Analyse des mots-clés...")
    all_keywords = []
    for desc in other_descriptions:
        all_keywords.extend(extract_keywords(desc))
    
    keyword_freq = Counter(all_keywords)
    print(f"📈 {len(keyword_freq)} mots-clés uniques trouvés")
    
    print("\n🎯 Top 50 des mots-clés les plus fréquents:")
    for keyword, freq in keyword_freq.most_common(50):
        print(f"  {keyword}: {freq}")
    
    print("\n💡 Suggestions de nouvelles catégories et mots-clés:")
    suggestions = suggest_categories(keyword_freq)
    
    for category, keywords in suggestions.items():
        if keywords:
            print(f"\n📂 {category.upper()}:")
            for keyword, freq in sorted(keywords, key=lambda x: x[1], reverse=True)[:10]:
                print(f"  - {keyword} (fréquence: {freq})")
    
    # Générer le code mis à jour pour CATEGORIES
    print("\n🔄 Génération des suggestions pour enrichir CATEGORIES...")
    
    # Suggestions basées sur les mots-clés fréquents
    new_keywords = {
        "performance": ["reduce", "contention", "allocation", "cache", "memory", "fast", "efficient", "improve"],
        "bug_fix": ["incorrect", "properly", "missing", "wrong", "broken", "fail", "exception", "null", "empty", "invalid"],
        "new_feature": ["extend", "implement", "create", "provide", "offer"],
        "refactoring": ["refactor", "restructure", "reorganize", "cleanup", "simplify", "modularize"],
        "maintenance": ["upgrade", "migrate", "compatibility", "deprecated", "remove", "replace"],
        "monitoring": ["metric", "log", "track", "monitor", "observe", "report", "statistics"],
        "configuration": ["config", "setting", "option", "parameter", "property", "tune"],
        "testing": ["test", "verify", "validate", "check", "assert"]
    }
    
    print("\n📝 Suggestions pour CATEGORIES dans etape2.py:")
    print("CATEGORIES = {")
    for category, keywords in new_keywords.items():
        if any(kw in keyword_freq for kw in keywords):
            print(f'    "{category}": [')
            # Combiner avec les mots-clés existants si nécessaire
            existing_keywords = []
            if category in ["performance", "bug_fix", "new_feature", "security"]:
                # Garder les mots-clés existants pour ces catégories
                pass
            suggested_keywords = [f'        "{kw}"' for kw in keywords if kw in keyword_freq]
            print(",\n".join(suggested_keywords))
            print("    ],")
    print("}")

if __name__ == "__main__":
    main()
