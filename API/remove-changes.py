import json
import os
from pathlib import Path

def remove_changes_key_from_json_files():
    """Supprime la clé 'changes' de tous les fichiers JSON dans le dossier output"""
    
    output_dir = Path("output")
    
    if not output_dir.exists():
        print(f"Le dossier {output_dir} n'existe pas.")
        return
    
    json_files = list(output_dir.glob("*.json"))
    
    if not json_files:
        print(f"Aucun fichier JSON trouvé dans {output_dir}")
        return
    
    print(f"Traitement de {len(json_files)} fichiers JSON...")
    
    for json_file in json_files:
        print(f"\nTraitement de: {json_file.name}")
        
        try:
            # Lire le fichier JSON
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Compter les occurrences de la clé 'changes' avant suppression
            changes_count = count_nested_keys(data, 'changes')
            print(f"  Clés 'changes' trouvées: {changes_count}")
            
            # Supprimer récursivement toutes les clés 'changes'
            data_modified = remove_key_recursively(data, 'changes')
            
            # Compter les occurrences après suppression pour vérification
            changes_count_after = count_nested_keys(data_modified, 'changes')
            
            if changes_count > 0:
                # Écrire le fichier modifié
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data_modified, f, indent=2, ensure_ascii=False)
                
                print(f"  ✅ {changes_count} clé(s) 'changes' supprimée(s)")
                print(f"  Fichier sauvegardé: {json_file}")
            else:
                print(f"  ℹ️  Aucune clé 'changes' à supprimer")
                
        except Exception as e:
            print(f"  ❌ Erreur lors du traitement de {json_file}: {e}")

def remove_key_recursively(obj, key_to_remove):
    """Supprime récursivement une clé d'un objet JSON imbriqué"""
    if isinstance(obj, dict):
        # Créer une copie du dictionnaire sans la clé à supprimer
        new_dict = {}
        for key, value in obj.items():
            if key != key_to_remove:
                # Appliquer récursivement sur les valeurs
                new_dict[key] = remove_key_recursively(value, key_to_remove)
        return new_dict
    elif isinstance(obj, list):
        # Appliquer récursivement sur chaque élément de la liste
        return [remove_key_recursively(item, key_to_remove) for item in obj]
    else:
        # Retourner les valeurs primitives inchangées
        return obj

def count_nested_keys(obj, key_to_count):
    """Compte le nombre d'occurrences d'une clé dans un objet JSON imbriqué"""
    count = 0
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == key_to_count:
                count += 1
            count += count_nested_keys(value, key_to_count)
    elif isinstance(obj, list):
        for item in obj:
            count += count_nested_keys(item, key_to_count)
    return count

if __name__ == "__main__":
    print("🗑️  Suppression de la clé 'changes' des fichiers JSON")
    print("=" * 50)
    remove_changes_key_from_json_files()
    print("\n✅ Opération terminée!")
