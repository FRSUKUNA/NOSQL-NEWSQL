import json
import pandas as pd
from pathlib import Path

# ==================== CLASSIFICATION DES BASES DE DONNÉES ====================
class DatabaseClassifier:
    def __init__(self):
        self.classifications = {
            "key_value": ["Redis"],
            "distributed_sql": ["CockroachDB", "TiDB", "YugabyteDB"],
            "columnar": ["Cassandra"],
            "document": ["MongoDB"],
            "graph": ["Neo4j"]
        }
        
        self.types = {
            "NewSQL": ["CockroachDB", "TiDB", "YugabyteDB", "Neo4j"],
            "NoSQL": ["Cassandra", "MongoDB", "Redis"]
        }
    
    def classify_database(self, database_name):
        """Classifier une base de données par catégorie et type"""
        normalized_name = database_name.lower()
        
        category = None
        for cat_name, databases in self.classifications.items():
            if normalized_name in [db.lower() for db in databases]:
                category = cat_name
                break
        
        db_type = None
        for type_name, databases in self.types.items():
            if normalized_name in [db.lower() for db in databases]:
                db_type = type_name
                break
        
        return category, db_type

# Initialiser le classifier
classifier = DatabaseClassifier()

all_data = []
files_skipped = []

# ==================== LECTURE DES FICHIERS ====================
for file in Path("output").glob("*.json"):
    try:
        with open(file, "r", encoding="utf-8") as f:
            content = json.load(f)
            if isinstance(content, list):
                all_data.extend(content)
            else:
                all_data.append(content)
    except json.JSONDecodeError:
        print(f"⚠️ Fichier JSON invalide : {file}")
        files_skipped.append(file)
    except Exception as e:
        print(f"⚠️ Erreur inattendue dans {file} : {e}")
        files_skipped.append(file)

print(f"\n📁 Fichiers lus avec succès : {len(list(Path('output').glob('*.json'))) - len(files_skipped)}")
if files_skipped:
    print("⚠️ Fichiers ignorés :")
    for f in files_skipped:
        print("   -", f)

# ==================== DATAFRAME ====================
df = pd.DataFrame(all_data)

# ==================== NORMALISATION DES COLONNES ====================
COLUMN_ALIASES = {
    "patch_version": ["patch_version", "patch", "version", "release", "tag"],
    "database": ["database", "db", "name"],
    "date": ["date", "release_date", "published_at"],
    "major_version": ["major_version", "major", "version_major"]
}

for canonical, aliases in COLUMN_ALIASES.items():
    for col in aliases:
        if col in df.columns:
            df[canonical] = df[col]
            break

# ==================== CONVERSION DATE ====================
df["date"] = pd.to_datetime(
    df["date"].replace("Date non disponible", pd.NaT),
    errors="coerce"
)
df["date_valide"] = df["date"].notna()

# ==================== DERNIERE VERSION PAR DATABASE ====================
latest_versions_list = []

for db, group in df.groupby("database"):
    if group["date_valide"].any():
        # si au moins une date valide, prendre la plus récente
        latest_row = group[group["date_valide"]].sort_values("date").tail(1)
    else:
        # sinon prendre la version la plus haute
        def version_to_tuple(row):
            major = row["major_version"]
            patch = row["patch_version"]
            major_parts = [int(p) if p.isdigit() else 0 for p in str(major).split(".")]
            patch_parts = [int(p) if p.isdigit() else 0 for p in str(patch).split(".")]
            return tuple(major_parts + patch_parts)
        group["version_tuple"] = group.apply(version_to_tuple, axis=1)
        latest_row = group.sort_values("version_tuple").tail(1)

    latest_versions_list.append(latest_row)

latest_versions = pd.concat(latest_versions_list)[
    ["database", "major_version", "patch_version", "date"]
]

# ==================== AJOUT DE LA CLASSIFICATION ====================
# Ajouter les colonnes de classification
latest_versions["category"] = latest_versions["database"].apply(
    lambda x: classifier.classify_database(x)[0]
)
latest_versions["type"] = latest_versions["database"].apply(
    lambda x: classifier.classify_database(x)[1]
)

print("\n📊 Dernières versions par base avec classification :")
print(latest_versions.to_string(index=False))

# ==================== STATISTIQUES DE CLASSIFICATION ====================
print("\n📈 Statistiques de classification :")
print(f"Répartition par catégorie :")
category_counts = latest_versions["category"].value_counts()
for cat, count in category_counts.items():
    print(f"  {cat}: {count}")

print(f"\nRépartition par type :")
type_counts = latest_versions["type"].value_counts()
for typ, count in type_counts.items():
    print(f"  {typ}: {count}")

# ==================== MATRICE DE CLASSIFICATION ====================
print("\n🔲 Matrice de classification :")
print("Catégorie \\ Type | NewSQL | NoSQL")
print("-" * 40)

# Créer la matrice
categories = ["key_value", "distributed_sql", "columnar", "document", "graph"]
types = ["NewSQL", "NoSQL"]

for category in categories:
    newsql_dbs = latest_versions[
        (latest_versions["category"] == category) & 
        (latest_versions["type"] == "NewSQL")
    ]["database"].tolist()
    
    nosql_dbs = latest_versions[
        (latest_versions["category"] == category) & 
        (latest_versions["type"] == "NoSQL")
    ]["database"].tolist()
    
    newsql_str = ", ".join(newsql_dbs) if newsql_dbs else "-"
    nosql_str = ", ".join(nosql_dbs) if nosql_dbs else "-"
    
    print(f"{category:<15} | {newsql_str:<6} | {nosql_str}")

# ==================== SAUVEGARDE EN JSON ====================
# Convertir le DataFrame en dictionnaire pour la sauvegarde JSON
result_data = latest_versions.to_dict('records')

# Ajouter des métadonnées
output_json = {
    "metadata": {
        "total_databases": len(result_data),
        "categories_processed": list(latest_versions["category"].unique()),
        "types_processed": list(latest_versions["type"].unique()),
        "generation_date": pd.Timestamp.now().isoformat()
    },
    "databases": result_data,
    "statistics": {
        "by_category": category_counts.to_dict(),
        "by_type": type_counts.to_dict()
    }
}

# Sauvegarder le résultat en JSON
with open("latest_versions_with_classification.json", "w", encoding="utf-8") as f:
    json.dump(output_json, f, indent=2, ensure_ascii=False, default=str)

print(f"\n💾 Résultat sauvegardé dans: latest_versions_with_classification.json")
