import json
import os
from etape2 import classify_change

def test_final_with_yugabyte():
    """Test final complet incluant les améliorations YugabyteDB"""
    
    print("🎯 TEST FINAL COMPLET - AVEC YUGABYTEDB")
    print("=" * 70)
    
    # Statistiques par base de données
    db_stats = {}
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
        
        db_name = filename.replace(".json", "").replace("-versions", "")
        db_stats[db_name] = {
            "total": 0,
            "other_before": 0,
            "other_after": 0,
            "categories": {}
        }
        
        for item in items:
            if "ai_analysis" in item and "details" in item["ai_analysis"]:
                for detail in item["ai_analysis"]["details"]:
                    total_changes += 1
                    db_stats[db_name]["total"] += 1
                    
                    if detail["category"] == "other":
                        total_other_before += 1
                        db_stats[db_name]["other_before"] += 1
                        
                        # Tester avec la nouvelle classification
                        new_category = classify_change(detail["description"])
                        if new_category != "other":
                            total_other_after += 1
                            db_stats[db_name]["other_after"] += 1
                        
                        # Compter les nouvelles catégories
                        if new_category not in db_stats[db_name]["categories"]:
                            db_stats[db_name]["categories"][new_category] = 0
                        db_stats[db_name]["categories"][new_category] += 1
    
    reduction = total_other_before - total_other_after
    reduction_percent = (reduction / total_other_before * 100) if total_other_before > 0 else 0
    
    print(f"📊 RÉSULTATS FINAUX TOUS BASES DE DONNÉES:")
    print(f"   Total changements analysés: {total_changes:,}")
    print(f"   'Other' avant: {total_other_before:,}")
    print(f"   'Other' après: {total_other_after:,}")
    print(f"   Réduction totale: {reduction:,} ({reduction_percent:.1f}%)")
    
    print(f"\n🗄️  DÉTAIL PAR BASE DE DONNÉES:")
    print("-" * 70)
    
    # Trier par nombre de réductions
    sorted_dbs = sorted(db_stats.items(), key=lambda x: x[1]["other_before"], reverse=True)
    
    for db_name, stats in sorted_dbs:
        reduction_db = stats["other_before"] - stats["other_after"]
        reduction_db_percent = (reduction_db / stats["other_before"] * 100) if stats["other_before"] > 0 else 0
        
        print(f"\n📊 {db_name.upper()}:")
        print(f"   Total changements: {stats['total']:,}")
        print(f"   'Other' avant: {stats['other_before']:,}")
        print(f"   'Other' après: {stats['other_after']:,}")
        print(f"   Réduction: {reduction_db:,} ({reduction_db_percent:.1f}%)")
        
        # Top 3 des nouvelles catégories pour cette base
        if stats["categories"]:
            top_categories = sorted(stats["categories"].items(), key=lambda x: x[1], reverse=True)[:3]
            print(f"   Top nouvelles catégories:")
            for category, count in top_categories:
                print(f"     • {category}: {count}")
    
    # Distribution finale globale
    print(f"\n📈 DISTRIBUTION FINALE GLOBALE:")
    print("-" * 70)
    
    global_categories = {
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
    
    # Recalculer les catégories globales
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
                    new_category = classify_change(detail["description"])
                    global_categories[new_category] += 1
    
    # Trier et afficher
    sorted_categories = sorted(global_categories.items(), key=lambda x: x[1], reverse=True)
    
    for category, count in sorted_categories:
        percentage = (count / total_changes * 100) if total_changes > 0 else 0
        print(f"   {category:15}: {count:6,} ({percentage:5.1f}%)")
    
    # Tests sur exemples YugabyteDB spécifiques
    print(f"\n🧪 TESTS SUR EXEMPLES YUGABYTEDB:")
    
    yugabyte_examples = [
        "Add YSQL support for distributed transactions with Raft consensus",
        "Fix tablet leader election during cluster network partition",
        "Implement YugaDB UI for cluster monitoring and administration",
        "Add IP-based firewall rules for secure cluster access",
        "Refactor tablet server service architecture for better scalability",
        "Enable automatic backup and DR snapshot replication",
        "Add Prometheus metrics collection for cluster health monitoring",
        "Configure runtime flags for YB-TServer bootstrap parameters",
        "Add integration tests for YCQL API compatibility validation",
        "Deprecate legacy shell tool in favor of new YB-CLI utility"
    ]
    
    for example in yugabyte_examples:
        category = classify_change(example)
        print(f"   📝 {example[:60]}... → {category}")
    
    return reduction_percent, global_categories

if __name__ == "__main__":
    improvement, final_distribution = test_final_with_yugabyte()
    print(f"\n🏆 AMÉLIORATION FINALE: {improvement:.1f}% de réduction globale")
    print(f"   ✅ Optimisation complète pour toutes les bases de données !")
