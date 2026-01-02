import json
import pymongo
from pymongo import MongoClient
from datetime import datetime
import os

# Importer les coordonnées MongoDB depuis mongo.py
try:
    from mongo import MONGO_URI
    connection_string = MONGO_URI
except ImportError:
    # Fallback vers localhost si mongo.py n'existe pas
    connection_string = "mongodb://localhost:27017/"
    print("⚠️ mongo.py non trouvé, utilisation de localhost par défaut")

class MongoDBInserter:
    def __init__(self, connection_string=connection_string, database_name="VT"):
        """
        Initialise la connexion à MongoDB
        
        Args:
            connection_string: Chaîne de connexion MongoDB
            database_name: Nom de la base de données
        """
        self.connection_string = connection_string
        self.database_name = database_name
        self.client = None
        self.db = None
        
    def connect(self):
        """Établit la connexion à MongoDB"""
        try:
            self.client = MongoClient(self.connection_string)
            # Test la connexion
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            print("✅ Connexion à MongoDB établie avec succès")
            return True
        except Exception as e:
            print(f"❌ Erreur de connexion à MongoDB: {e}")
            return False
    
    def check_data_exists(self, collection_name="tables"):
        """
        Vérifie si les données existent déjà dans la collection
        
        Returns:
            bool: True si des données existent, False sinon
        """
        try:
            collection = self.db[collection_name]
            
            # Vérifier si des données de bases existent
            database_count = collection.count_documents({'_type': 'database'})
            
            if database_count > 0:
                print(f"🔍 {database_count} entrées de bases de données trouvées dans la collection")
                
                # Afficher les bases existantes
                existing_databases = list(collection.find({'_type': 'database'}, {'database': 1, 'major_version': 1, 'patch_version': 1}))
                print("📋 Bases de données existantes:")
                for db in existing_databases:
                    print(f"   - {db.get('database', 'N/A')} v{db.get('major_version', 'N/A')}.{db.get('patch_version', 'N/A')}")
                
                return True
            else:
                print("📋 Aucune donnée de base de données trouvée dans la collection")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors de la vérification: {e}")
            return False
    
    def insert_json_data(self, json_file_path, collection_name="tables", force_overwrite=False):
        """
        Insère les données du fichier JSON dans MongoDB
        
        Args:
            json_file_path: Chemin vers le fichier JSON
            collection_name: Nom de la collection
            force_overwrite: Force l'écrasement des données existantes
        """
        try:
            # Vérifier si les données existent déjà
            data_exists = self.check_data_exists(collection_name)
            
            if data_exists and not force_overwrite:
                print("⚠️ Des données existent déjà dans la collection.")
                response = input("Voulez-vous écraser les données existantes ? (o/n): ").lower()
                if response != 'o':
                    print("❌ Opération annulée")
                    return False
            
            # Lire le fichier JSON
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            print(f"📁 Fichier JSON lu: {json_file_path}")
            
            # Obtenir la collection
            collection = self.db[collection_name]
            
            # Supprimer toutes les anciennes données si écrasement
            if data_exists and (force_overwrite or True):  # True car on a confirmé l'écrasement
                print("🗑️ Suppression des anciennes données...")
                collection.delete_many({})
                print("✅ Anciennes données supprimées")
            
            # Insérer les métadonnées
            metadata = data.get('metadata', {})
            metadata['_type'] = 'metadata'
            metadata['inserted_at'] = datetime.now()
            collection.insert_one(metadata)
            print("✅ Métadonnées insérées")
            
            # Insérer les statistiques
            statistics = data.get('statistics', {})
            statistics['_type'] = 'statistics'
            statistics['inserted_at'] = datetime.now()
            collection.insert_one(statistics)
            print("✅ Statistiques insérées")
            
            # Insérer les données des bases de données
            databases = data.get('databases', [])
            
            # Ajouter des champs supplémentaires pour chaque base de données
            for db in databases:
                db['_type'] = 'database'
                db['inserted_at'] = datetime.now()
                # Convertir les dates NaT en null
                if db.get('date') == 'NaT':
                    db['date'] = None
                else:
                    # Convertir la date en format ISO si elle existe
                    try:
                        if db['date']:
                            db['date'] = datetime.strptime(db['date'], '%Y-%m-%d %H:%M:%S').isoformat()
                    except:
                        db['date'] = None
            
            # Insérer les nouvelles données
            if databases:
                result = collection.insert_many(databases)
                print(f"✅ {len(result.inserted_ids)} bases de données insérées")
            else:
                print("⚠️ Aucune donnée de base de données à insérer")
            
            return True
            
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion: {e}")
            return False
    
    def get_collection_stats(self, collection_name="tables"):
        """Affiche les statistiques de la collection"""
        try:
            collection = self.db[collection_name]
            
            stats = {
                'total_documents': collection.count_documents({}),
                'metadata': collection.count_documents({'_type': 'metadata'}),
                'statistics': collection.count_documents({'_type': 'statistics'}),
                'databases': collection.count_documents({'_type': 'database'})
            }
            
            print("\n📊 Statistiques de la collection:")
            print(f"  Total des documents: {stats['total_documents']}")
            print(f"  Métadonnées: {stats['metadata']}")
            print(f"  Statistiques: {stats['statistics']}")
            print(f"  Bases de données: {stats['databases']}")
            
            return stats
            
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des statistiques: {e}")
            return None
    
    def close(self):
        """Ferme la connexion à MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 Connexion à MongoDB fermée")

def main():
    """Fonction principale"""
    # Configuration
    json_file = "latest_versions_with_classification.json"
    collection_name = "tables"
    
    # Vérifier si le fichier JSON existe
    if not os.path.exists(json_file):
        print(f"❌ Fichier JSON introuvable: {json_file}")
        print("Veuillez d'abord exécuter etape1.py pour générer le fichier JSON")
        return
    
    # Créer l'instance de l'inséreur
    inserter = MongoDBInserter()
    
    try:
        # Se connecter à MongoDB
        if not inserter.connect():
            return
        
        # Insérer les données avec vérification
        if inserter.insert_json_data(json_file, collection_name):
            # Afficher les statistiques
            inserter.get_collection_stats(collection_name)
            print(f"\n🎉 Données insérées avec succès dans la base 'VT', collection '{collection_name}'!")
        
    finally:
        # Fermer la connexion
        inserter.close()

if __name__ == "__main__":
    main()
