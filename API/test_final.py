import json
import os
from etape2 import classify_change

def test_final_improvement():
    """Teste l'amélioration finale avec les mots-clés enrichis"""
    
    # Compter les "other" avant et après
    total_other_before = 0
    total_other_after = 0
    total_changes = 0
    
    print("📊 Analyse de l'impact final...")
    
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
                    # Compter les "other" originaux
                    if detail["category"] == "other":
                        total_other_before += 1
                        # Tester avec la nouvelle classification
                        new_category = classify_change(detail["description"])
                        if new_category != "other":
                            total_other_after += 1
    
    reduction = total_other_before - total_other_after
    reduction_percent = (reduction / total_other_before * 100) if total_other_before > 0 else 0
    
    print(f"📈 Résultats finaux:")
    print(f"   Total changements: {total_changes}")
    print(f"   'Other' avant: {total_other_before}")
    print(f"   'Other' après: {total_other_after}")
    print(f"   Réduction: {reduction} ({reduction_percent:.1f}%)")
    
    # Test sur quelques exemples spécifiques
    print(f"\n🧪 Tests sur exemples typiques:")
    
    test_examples = [
        "Change the eager reference counting of compression dictionaries to lazy",
        "Reduce contention in MemtableAllocator.allocate", 
        "Fix CompressionDictionary being closed while still in use",
        "Add export, list, import sub-commands for nodetool compressiondictionary",
        "Prevent unauthorized access to sensitive data",
        "Implement nodetool history",
        "Upgrade snakeyaml to 2.4",
        "Log queries scanning too many SSTables per read"
    ]
    
    for desc in test_examples:
        category = classify_change(desc)
        print(f"   📝 {desc[:50]}... → {category}")
    
    return reduction_percent

if __name__ == "__main__":
    improvement = test_final_improvement()
    print(f"\n🎯 Amélioration totale: {improvement:.1f}% de réduction de la catégorie 'other'")
