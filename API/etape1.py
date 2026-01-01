import json
import pandas as pd
from pathlib import Path

all_data = []
files_skipped = []

# ==================== LECTURE DES FICHIERS ====================
for file in Path("sources").glob("*.json"):
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

print(f"\n📁 Fichiers lus avec succès : {len(list(Path('sources').glob('*.json'))) - len(files_skipped)}")
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

print("\n📊 Dernières versions par base :")
print(latest_versions.to_string(index=False))
