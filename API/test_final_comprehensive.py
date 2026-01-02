import json
import os
from etape2 import classify_change

def test_final_comprehensive_improvement():
    """Test final de toutes les améliorations apportées"""
    
    print("🎯 TEST FINAL - AMÉLIORATION COMPRÉHENSIVE")
    print("=" * 60)
    
    total_other_before = 0
    total_other_after = 0
    total_changes = 0
    
    # Analyser tous les fichiers
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
                        # Tester avec la nouvelle classification
                        new_category = classify_change(detail["description"])
                        if new_category != "other":
                            total_other_after += 1
    
    reduction = total_other_before - total_other_after
    reduction_percent = (reduction / total_other_before * 100) if total_other_before > 0 else 0
    
    print(f"📊 RÉSULTATS FINAUX:")
    print(f"   Total changements analysés: {total_changes:,}")
    print(f"   'Other' avant améliorations: {total_other_before:,}")
    print(f"   'Other' après améliorations: {total_other_after:,}")
    print(f"   Réduction totale: {reduction:,} ({reduction_percent:.1f}%)")
    
    # Distribution finale des catégories
    print(f"\n📈 Distribution finale des catégories:")
    category_counts = {
        "performance": 0,
        "bug_fix": 0,
        "new_feature": 0,
        "security": 0,
        "refactoring": 0,
        "maintenance": 0,
        "monitoring": 0,
        "configuration": 0,
        "testing": 0,
        "other": 0
    }
    
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
                    # Reclassifier avec le nouveau système
                    new_category = classify_change(detail["description"])
                    category_counts[new_category] += 1
    
    # Trier et afficher
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    for category, count in sorted_categories:
        percentage = (count / total_changes * 100) if total_changes > 0 else 0
        print(f"   {category:15}: {count:6,} ({percentage:5.1f}%)")
    
    # Tests sur exemples spécifiques
    print(f"\n🧪 Tests sur exemples avancés:")
    
    advanced_examples = [
        "Add cursor based optimized compaction path for better throughput",
        "Fix NPE when meta keyspace placements are empty before CMS initialization", 
        "Implement changefeed with JSON schema validation and TLS encryption",
        "Prevent unauthorized access through SQL injection attacks",
        "Refactor connection pool cleanup to avoid resource leaks",
        "Upgrade dependency versions for security compatibility",
        "Add comprehensive monitoring metrics collection and export",
        "Configure environment variable overrides for deployment flexibility",
        "Add unit tests with mock objects for edge case validation",
        "Deprecate legacy authentication method in favor of OAuth2"
    ]
    
    for example in advanced_examples:
        category = classify_change(example)
        print(f"   📝 {example[:60]}... → {category}")
    
    return reduction_percent, category_counts

if __name__ == "__main__":
    improvement, distribution = test_final_comprehensive_improvement()
    print(f"\n🏆 AMÉLIORATION TOTALE: {improvement:.1f}% de réduction de la catégorie 'other'")
    print(f"   ✅ Passage de {distribution['other'] + (distribution['other'] * 100 / (100 - improvement)):.0f} à {distribution['other']} dans 'other'")
