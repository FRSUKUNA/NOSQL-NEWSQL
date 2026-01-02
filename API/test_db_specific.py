import json
import os
from etape2 import classify_change

def test_db_specific_improvement():
    """Teste l'amélioration spécifique pour Cassandra, MongoDB et CockroachDB"""
    
    # Fichiers à analyser
    files_to_test = {
        "cassandra": "cassandra_versions.json",
        "mongodb": "mongodb-versions.json", 
        "cockroachdb": "cockroachdb-versions.json"
    }
    
    print("📊 Analyse de l'impact sur les 3 bases de données principales:")
    print("=" * 70)
    
    total_improvement = 0
    
    for db_name, filename in files_to_test.items():
        filepath = os.path.join("output", filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = data if isinstance(data, list) else [data]
        
        total_other_before = 0
        total_other_after = 0
        total_changes = 0
        
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
        total_improvement += reduction
        
        print(f"\n🗄️  {db_name.upper()}:")
        print(f"   Total changements: {total_changes}")
        print(f"   'Other' avant: {total_other_before}")
        print(f"   'Other' après: {total_other_after}")
        print(f"   Réduction: {reduction} ({reduction_percent:.1f}%)")
        
        # Quelques exemples de classifications améliorées
        print(f"   📝 Exemples de nouvelles classifications:")
        examples_tested = 0
        for item in items[:3]:  # Tester sur les 3 premiers patches
            if "ai_analysis" in item and "details" in item["ai_analysis"]:
                for detail in item["ai_analysis"]["details"]:
                    if detail["category"] == "other":
                        new_category = classify_change(detail["description"])
                        if new_category != "other":
                            desc = detail["description"][:60]
                            print(f"      • {desc}... → {new_category}")
                            examples_tested += 1
                            if examples_tested >= 3:
                                break
                if examples_tested >= 3:
                    break
    
    print(f"\n🎯 AMÉLIORATION TOTALE: {total_improvement} changements reclassifiés")
    
    # Test sur quelques exemples typiques de chaque base de données
    print(f"\n🧪 Tests sur exemples spécifiques:")
    
    test_examples = {
        "cassandra": [
            "Add cursor based optimized compaction path",
            "Fix NPE when meta keyspace placements are empty",
            "Add cqlsh autocompletion for the identity mapping feature",
            "Improve debug around paused and disabled compaction"
        ],
        "mongodb": [
            "Add support for change streams with document pre-images",
            "Fix cursor cleanup on connection pool errors", 
            "Implement retryable writes for multi-document transactions",
            "Optimize aggregation pipeline for large datasets"
        ],
        "cockroachdb": [
            "Add support for spatial indexes on geo data types",
            "Fix SQL parser handling of foreign key constraints",
            "Implement changefeed with JSON schema validation",
            "Optimize distributed transaction commit protocol"
        ]
    }
    
    for db_name, examples in test_examples.items():
        print(f"\n🗄️  {db_name.upper()}:")
        for example in examples:
            category = classify_change(example)
            print(f"   📝 {example[:50]}... → {category}")

if __name__ == "__main__":
    test_db_specific_improvement()
