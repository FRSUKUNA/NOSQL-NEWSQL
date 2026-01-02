import json
import os
from etape2 import classify_change, CATEGORIES

def test_improvement():
    """Teste l'amélioration de la classification avec les nouveaux mots-clés"""
    
    # Quelques exemples de descriptions classées comme "other" auparavant
    test_cases = [
        "Change the eager reference counting of compression dictionaries to lazy",
        "Reduce contention in MemtableAllocator.allocate",
        "Add cursor based optimized compaction path",
        "Fix CompressionDictionary being closed while still in use",
        "Implement nodetool history",
        "Refactor the way we check if a transformation is allowed to be committed",
        "Upgrade snakeyaml to 2.4",
        "Add export, list, import sub-commands for nodetool compressiondictionary",
        "Remove deprecated configuration options",
        "Add support for ZSTD dictionary compression",
        "Improve debug around paused and disabled compaction",
        "Update Netty to 4.1.125.Final",
        "Extend nodetool verify to validate SAI files",
        "Avoid NPE when meta keyspace placements are empty",
        "Log queries scanning too many SSTables per read"
    ]
    
    print("🧪 Test des nouvelles classifications:")
    print("=" * 60)
    
    for description in test_cases:
        category = classify_change(description)
        print(f"📝 {description[:60]}...")
        print(f"   🏷️  Catégorie: {category}")
        print()
    
    # Compter combien de descriptions "other" peuvent maintenant être classées
    print("📊 Analyse de l'impact sur les fichiers existants:")
    
    total_other_before = 0
    total_other_after = 0
    total_changes = 0
    
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
                    total_changes += 1
                    if detail["category"] == "other":
                        total_other_before += 1
                        # Tester si la nouvelle classification fonctionne
                        new_category = classify_change(detail["description"])
                        if new_category != "other":
                            total_other_after += 1
    
    improvement = ((total_other_before - total_other_after) / total_other_before * 100) if total_other_before > 0 else 0
    
    print(f"📈 Statistiques:")
    print(f"   Total changements: {total_changes}")
    print(f"   'Other' avant: {total_other_before}")
    print(f"   'Other' après: {total_other_after}")
    print(f"   Amélioration: {improvement:.1f}%")
    
    print(f"\n🎯 Nouvelles catégories ajoutées:")
    for category in CATEGORIES.keys():
        if category not in ["performance", "bug_fix", "new_feature", "security", "other"]:
            print(f"   - {category}")

if __name__ == "__main__":
    test_improvement()
