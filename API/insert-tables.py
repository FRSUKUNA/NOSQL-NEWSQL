import json
import os
from pathlib import Path
from pymongo import MongoClient
from mongo import MONGO_URI, client, db, collection_version

def import_json_files_to_mongodb():
    """Importe tous les fichiers JSON du dossier output vers la collection versions MongoDB"""
    
    output_dir = Path("output")
    
    if not output_dir.exists():
        print(f"Le dossier {output_dir} n'existe pas.")
        return
    
    json_files = list(output_dir.glob("*.json"))
    
    if not json_files:
        print(f"Aucun fichier JSON trouvé dans {output_dir}")
        return
    
    print(f"Importation de {len(json_files)} fichiers JSON vers MongoDB...")
    print(f"Base de données: VT")
    print(f"Collection: versions")
    print("=" * 60)
    
    total_documents = 0
    
    try:
        # Vider la collection existante (optionnel - commenter si vous voulez ajouter sans remplacer)
        print("🗑️  Vidage de la collection 'versions'...")
        result = collection_version.delete_many({})
        print(f"   {result.deleted_count} documents supprimés")
        
        for json_file in json_files:
            print(f"\n📄 Traitement de: {json_file.name}")
            
            try:
                # Lire le fichier JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Vérifier si les données sont une liste ou un dictionnaire
                if isinstance(data, list):
                    documents = data
                elif isinstance(data, dict):
                    documents = [data]
                else:
                    print(f"   ⚠️  Format de données non supporté dans {json_file.name}")
                    continue
                
                # Insérer les documents dans MongoDB
                if documents:
                    result = collection_version.insert_many(documents)
                    documents_count = len(result.inserted_ids)
                    total_documents += documents_count
                    print(f"   ✅ {documents_count} documents insérés")
                else:
                    print(f"   ℹ️  Aucun document à insérer")
                    
            except Exception as e:
                print(f"   ❌ Erreur lors du traitement de {json_file.name}: {e}")
        
        print(f"\n" + "=" * 60)
        print(f"🎉 Importation terminée!")
        print(f"📊 Total de documents insérés: {total_documents}")
        
        # Vérification
        count_in_db = collection_version.count_documents({})
        print(f"📋 Documents dans la collection 'versions': {count_in_db}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la connexion à MongoDB: {e}")
    
    finally:
        # Fermer la connexion
        client.close()
        print("🔌 Connexion MongoDB fermée")

def show_collection_stats():
    """Affiche des statistiques sur la collection versions"""
    try:
        print("\n📊 Statistiques de la collection 'versions':")
        print("-" * 40)
        
        total_count = collection_version.count_documents({})
        print(f"Total documents: {total_count}")
        
        if total_count > 0:
            # Compter par type de base de données
            pipeline = [
                {"$group": {"_id": "$database", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            db_stats = list(collection_version.aggregate(pipeline))
            
            print("\nRépartition par base de données:")
            for stat in db_stats:
                print(f"  {stat['_id']}: {stat['count']} documents")
            
            # Afficher un exemple de document
            sample = collection_version.find_one()
            print(f"\nExemple de document (base: {sample.get('database', 'N/A')}):")
            print(json.dumps(sample, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage des statistiques: {e}")

if __name__ == "__main__":
    print("📥 Importation des fichiers JSON vers MongoDB")
    print("=" * 60)
    
    import_json_files_to_mongodb()
    show_collection_stats()
