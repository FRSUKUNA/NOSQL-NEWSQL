import json
from datetime import datetime

# Fichier d'entrée (normalisé)
input_file = "sources/mongodb-versions.json"

# Fichier de sortie (nettoyé)
output_file = "sources/mongodb-versions.json"

cleaned_data = []

with open(input_file, "r", encoding="utf-8") as f:
    data = json.load(f)
    for doc in data:
        # Supprime si changes est vide ou absent
        if not doc.get("changes"):
            continue

        # Reformater la date si elle existe
        date_str = doc.get("date")
        if date_str:
            try:
                # Essaye de parser avec différents formats possibles
                parsed_date = datetime.strptime(date_str, "%Y-%m-%d")  # ex : 2025-06-04
                doc["date"] = parsed_date.strftime("%b %d, %Y")  # ex : Jun 04, 2025
            except ValueError:
                # Si la date n'est pas dans le format attendu, on laisse telle quelle
                pass

        cleaned_data.append(doc)

# Sauvegarde le JSON nettoyé
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

print(f"[✅] {len(cleaned_data)} documents nettoyés et sauvegardés dans {output_file}")
