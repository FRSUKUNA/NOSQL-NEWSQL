#!/usr/bin/env python3
"""
Script pour classifier les bases de données par catégorie et type.
"""

import pandas as pd
import json
from pathlib import Path

class DatabaseClassifier:
    def __init__(self):
        self.classifications = {
            # Catégories de bases de données
            "key_value": {
                "databases": ["Redis"],
                "description": "Bases de données clé-valeur",
                "characteristics": ["Simple key-value pairs", "High performance", "In-memory"]
            },
            "distributed_sql": {
                "databases": ["CockroachDB", "TiDB", "YugabyteDB"],
                "description": "Bases de données SQL distribuées",
                "characteristics": ["SQL compatibility", "Horizontal scaling", "ACID transactions", "Distributed architecture"]
            },
            "columnar": {
                "databases": ["Cassandra"],
                "description": "Bases de données column-family",
                "characteristics": ["Wide-column storage", "High write throughput", "Linear scalability", "No single point of failure"]
            },
            "document": {
                "databases": ["MongoDB"],
                "description": "Bases de données document",
                "characteristics": ["JSON/BSON documents", "Flexible schema", "Rich queries", "Horizontal scaling"]
            },
            "graph": {
                "databases": ["Neo4j"],
                "description": "Bases de données graphe",
                "characteristics": ["Graph structures", "Relationship-focused", "ACID compliance", "Cypher query language"]
            }
        }
        
        # Types NewSQL vs NoSQL
        self.types = {
            "NewSQL": {
                "databases": ["CockroachDB", "TiDB", "YugabyteDB", "Neo4j"],
                "description": "Bases de données distribuées avec garanties ACID et compatibilité SQL",
                "characteristics": ["ACID transactions", "SQL interface", "Horizontal scaling", "Consistency guarantees"]
            },
            "NoSQL": {
                "databases": ["Cassandra", "MongoDB", "Redis"],
                "description": "Bases de données non-relationnelles avec focus sur la scalabilité",
                "characteristics": ["Flexible schema", "Eventual consistency", "High availability", "Horizontal scaling"]
            }
        }
    
    def classify_database(self, database_name):
        """Classifier une base de données par catégorie et type"""
        category = None
        category_info = None
        
        # Gérer les variations de noms (TiDB vs Tidb)
        normalized_name = database_name.lower()
        
        for cat_name, cat_info in self.classifications.items():
            if normalized_name in [db.lower() for db in cat_info["databases"]]:
                category = cat_name
                category_info = cat_info
                break
        
        db_type = None
        type_info = None
        
        for type_name, type_data in self.types.items():
            if normalized_name in [db.lower() for db in type_data["databases"]]:
                db_type = type_name
                type_info = type_data
                break
        
        return {
            "database": database_name,
            "category": category,
            "category_info": category_info,
            "type": db_type,
            "type_info": type_info
        }
    
    def load_latest_versions(self):
        """Charger les dernières versions des bases de données"""
        versions = []
        output_dir = Path("output")
        
        for file_path in output_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data and len(data) > 0:
                    latest = data[0]  # Prendre la première version (la plus récente)
                    versions.append({
                        "database": latest.get("database", "Unknown"),
                        "major_version": latest.get("major_version", "N/A"),
                        "patch_version": latest.get("patch_version", "N/A"),
                        "date": latest.get("date", "N/A"),
                        "file": file_path.name
                    })
            except Exception as e:
                print(f"Erreur lors de la lecture de {file_path}: {e}")
        
        return versions
    
    def generate_classification_report(self):
        """Générer un rapport de classification complet"""
        print("🔍 CLASSIFICATION DES BASES DE DONNÉES")
        print("=" * 60)
        
        # Charger les dernières versions
        versions = self.load_latest_versions()
        
        # Classifier chaque base de données
        classifications = []
        for version in versions:
            classification = self.classify_database(version["database"])
            classification.update(version)
            classifications.append(classification)
        
        # Créer un DataFrame pour un affichage facile
        df = pd.DataFrame(classifications)
        
        # Afficher le tableau de classification
        print("\n📊 TABLEAU DE CLASSIFICATION")
        print("-" * 60)
        for _, row in df.iterrows():
            print(f"🗄️  {row['database']}")
            print(f"   Catégorie: {row['category'] or 'Non classifiée'}")
            print(f"   Type: {row['type'] or 'Non classifié'}")
            print(f"   Version: {row['patch_version']}")
            print(f"   Date: {row['date']}")
            print()
        
        # Afficher les détails par catégorie
        print("\n📋 DÉTAILS PAR CATÉGORIE")
        print("=" * 60)
        
        for cat_name, cat_info in self.classifications.items():
            print(f"\n🏷️  {cat_name.upper().replace('_', ' ')}")
            print(f"   Description: {cat_info['description']}")
            print(f"   Caractéristiques: {', '.join(cat_info['characteristics'])}")
            print(f"   Bases de données: {', '.join(cat_info['databases'])}")
        
        # Afficher les détails par type
        print("\n\n📋 DÉTAILS PAR TYPE (NewSQL vs NoSQL)")
        print("=" * 60)
        
        for type_name, type_info in self.types.items():
            print(f"\n🏷️  {type_name}")
            print(f"   Description: {type_info['description']}")
            print(f"   Caractéristiques: {', '.join(type_info['characteristics'])}")
            print(f"   Bases de données: {', '.join(type_info['databases'])}")
        
        # Statistiques
        print("\n\n📈 STATISTIQUES")
        print("=" * 60)
        
        category_counts = {}
        type_counts = {}
        
        for classification in classifications:
            cat = classification['category'] or 'Non classifié'
            typ = classification['type'] or 'Non classifié'
            
            category_counts[cat] = category_counts.get(cat, 0) + 1
            type_counts[typ] = type_counts.get(typ, 0) + 1
        
        print("Répartition par catégorie:")
        for cat, count in category_counts.items():
            print(f"  {cat}: {count}")
        
        print("\nRépartition par type:")
        for typ, count in type_counts.items():
            print(f"  {typ}: {count}")
        
        # Sauvegarder le rapport
        self.save_classification_report(classifications)
        
        return classifications
    
    def save_classification_report(self, classifications):
        """Sauvegarder le rapport de classification"""
        report = {
            "classification_date": pd.Timestamp.now().isoformat(),
            "categories": self.classifications,
            "types": self.types,
            "database_classifications": classifications,
            "summary": {
                "total_databases": len(classifications),
                "categories": list(set(c['category'] for c in classifications if c['category'])),
                "types": list(set(c['type'] for c in classifications if c['type']))
            }
        }
        
        with open("database_classification.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Rapport sauvegardé dans: database_classification.json")
    
    def create_classification_matrix(self):
        """Créer une matrice de classification"""
        print("\n🔲 MATRICE DE CLASSIFICATION")
        print("=" * 60)
        
        # Créer la matrice
        categories = list(self.classifications.keys())
        types = list(self.types.keys())
        
        matrix = {}
        for category in categories:
            matrix[category] = {}
            for db_type in types:
                matrix[category][db_type] = []
        
        # Remplir la matrice
        for category, cat_info in self.classifications.items():
            for db in cat_info["databases"]:
                for db_type, type_info in self.types.items():
                    if db in type_info["databases"]:
                        matrix[category][db_type].append(db)
        
        # Afficher la matrice
        print("Catégorie \\ Type | NewSQL | NoSQL")
        print("-" * 40)
        
        for category, types_data in matrix.items():
            newsql_dbs = ", ".join(types_data["NewSQL"]) if types_data["NewSQL"] else "-"
            nosql_dbs = ", ".join(types_data["NoSQL"]) if types_data["NoSQL"] else "-"
            print(f"{category:<15} | {newsql_dbs:<6} | {nosql_dbs}")

def main():
    """Fonction principale"""
    classifier = DatabaseClassifier()
    classifications = classifier.generate_classification_report()
    classifier.create_classification_matrix()

if __name__ == "__main__":
    main()
