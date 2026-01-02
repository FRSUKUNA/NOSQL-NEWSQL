import json
from pathlib import Path
from pymongo import MongoClient
from mongo import MONGO_URI, client, db, collection_version

def sync_new_patches():
    """Compare les fichiers JSON avec la base de données et ajoute uniquement les nouveaux patches"""
    
    output_dir = Path("output")
    
    if not output_dir.exists():
        print(f"Le dossier {output_dir} n'existe pas.")
        return
    
    json_files = list(output_dir.glob("*.json"))
    
    if not json_files:
        print(f"Aucun fichier JSON trouvé dans {output_dir}")
        return
    
    print("🔄 Synchronisation des nouveaux patches")
    print("=" * 50)
    
    try:
        # Récupérer tous les documents existants de la base de données
        existing_patches = get_existing_patches()
        print(f"📋 Patches existants dans la base: {len(existing_patches)}")
        
        total_new_patches = 0
        total_processed = 0
        
        for json_file in json_files:
            print(f"\n📄 Traitement de: {json_file.name}")
            
            try:
                # Lire le fichier JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Normaliser en liste
                if isinstance(data, dict):
                    documents = [data]
                elif isinstance(data, list):
                    documents = data
                else:
                    print(f"   ⚠️  Format non supporté")
                    continue
                
                new_patches = []
                
                for doc in documents:
                    total_processed += 1
                    
                    # Créer une clé unique pour comparaison
                    db_name = doc.get('database')
                    patch_version = doc.get('patch_version')
                    
                    if not db_name or not patch_version:
                        continue
                    
                    unique_key = f"{db_name}_{patch_version}"
                    
                    # Vérifier si le patch existe déjà
                    if unique_key not in existing_patches:
                        new_patches.append(doc)
                        existing_patches[unique_key] = doc
                
                # Insérer uniquement les nouveaux patches
                if new_patches:
                    result = collection_version.insert_many(new_patches)
                    new_count = len(result.inserted_ids)
                    total_new_patches += new_count
                    print(f"   ✅ {new_count} nouveaux patches ajoutés")
                else:
                    print(f"   ℹ️  Aucun nouveau patch trouvé")
                    
            except Exception as e:
                print(f"   ❌ Erreur: {e}")
        
        print(f"\n" + "=" * 50)
        print(f"🎉 Synchronisation terminée!")
        print(f"📊 Documents traités: {total_processed}")
        print(f"🆕 Nouveaux patches ajoutés: {total_new_patches}")
        
        # Statistiques finales
        final_count = collection_version.count_documents({})
        print(f"📋 Total documents dans la base: {final_count}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation: {e}")
    
    finally:
        client.close()
        print("🔌 Connexion MongoDB fermée")

def get_existing_patches():
    """Récupère tous les patches existants et les indexe par database_patch_version"""
    existing_patches = {}
    
    try:
        # Récupérer tous les documents
        cursor = collection_version.find({}, {"database": 1, "patch_version": 1})
        
        for doc in cursor:
            db_name = doc.get('database')
            patch_version = doc.get('patch_version')
            
            if db_name and patch_version:
                unique_key = f"{db_name}_{patch_version}"
                existing_patches[unique_key] = doc
                
    except Exception as e:
        print(f"⚠️  Erreur lors de la récupération des patches existants: {e}")
    
    return existing_patches

def generate_comprehensive_stats():
    """Génère un fichier JSON avec des statistiques complètes de la base de données"""
    
    print("\n📊 Génération des statistiques complètes...")
    
    try:
        # Statistiques globales
        total_docs = collection_version.count_documents({})
        
        # Nombre de bases de données distinctes
        databases = collection_version.distinct("database")
        
        stats = {
            "summary": {
                "total_databases": len(databases),
                "total_versions": total_docs,
                "generation_date": "2025-01-02"
            },
            "databases": {}
        }
        
        # Statistiques par base de données
        for db_name in databases:
            db_stats = analyze_database(db_name)
            stats["databases"][db_name] = db_stats
        
        # Sauvegarder les statistiques dans un fichier JSON
        output_file = "database_statistics.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Statistiques sauvegardées dans: {output_file}")
        
        # Afficher un résumé
        print(f"\n📋 Résumé:")
        print(f"  Bases de données: {len(databases)}")
        print(f"  Total versions: {total_docs}")
        
        for db_name, db_stat in stats["databases"].items():
            print(f"  {db_name}: {db_stat['major_versions_count']} versions majeures, {db_stat['total_patches']} patches")
        
        return stats
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération des statistiques: {e}")
        return None

def analyze_database(db_name):
    """Analyse une base de données spécifique"""
    
    # Tous les documents pour cette base
    docs = list(collection_version.find({"database": db_name}))
    
    # Versions majeures distinctes
    major_versions = list(set(doc.get('major_version', 'N/A') for doc in docs))
    major_versions.sort()
    
    # Grouper par version majeure
    versions_grouped = {}
    for doc in docs:
        major_ver = doc.get('major_version', 'N/A')
        if major_ver not in versions_grouped:
            versions_grouped[major_ver] = []
        versions_grouped[major_ver].append(doc)
    
    # Analyser chaque version majeure
    versions_analysis = {}
    total_patches = len(docs)
    
    for major_ver, patches in versions_grouped.items():
        version_stats = analyze_major_version(major_ver, patches)
        versions_analysis[major_ver] = version_stats
    
    # Statistiques globales pour la base de données
    db_stats = {
        "major_versions_count": len(major_versions),
        "major_versions": major_versions,
        "total_patches": total_patches,
        "versions": versions_analysis,
        "global_stats": calculate_global_stats(docs)
    }
    
    return db_stats

def analyze_major_version(major_version, patches):
    """Analyse une version majeure spécifique"""
    
    patches_analysis = {}
    
    for patch in patches:
        patch_version = patch.get('patch_version', 'N/A')
        patch_stats = analyze_patch(patch)
        patches_analysis[patch_version] = patch_stats
    
    # Calculer les statistiques globales pour cette version majeure
    version_stats = {
        "patches_count": len(patches),
        "patches": patches_analysis,
        "version_totals": calculate_version_totals(patches)
    }
    
    return version_stats

def analyze_patch(patch):
    """Analyse un patch spécifique"""
    
    patch_stats = {
        "patch_version": patch.get('patch_version', 'N/A'),
        "date": patch.get('date', 'N/A'),
        "ai_analysis": {},
        "acid_consistency": {},
        "innovation_count": 0,
        "alerts_count": 0
    }
    
    # Analyse AI
    ai_analysis = patch.get('ai_analysis', {})
    if ai_analysis:
        if 'dominant_type' in ai_analysis:
            patch_stats["ai_analysis"]["dominant_type"] = ai_analysis['dominant_type']
        
        if 'summary' in ai_analysis:
            summary = ai_analysis['summary']
            patch_stats["ai_analysis"]["summary"] = summary
            
            # Compter les innovations (new_feature)
            if 'new_feature' in summary:
                patch_stats["innovation_count"] = summary['new_feature']
    
    # ACID consistency
    acid_features = patch.get('acid_consistency_features', {})
    if acid_features:
        # Compter les features ACID
        acid_count = 0
        if isinstance(acid_features, dict):
            acid_count = len([k for k, v in acid_features.items() if v])
        elif isinstance(acid_features, list):
            acid_count = len(acid_features)
        
        patch_stats["acid_consistency"] = {
            "features_count": acid_count,
            "features": acid_features
        }
    
    # Alerts
    alerts = patch.get('alerts', [])
    if alerts:
        patch_stats["alerts_count"] = len(alerts) if isinstance(alerts, list) else 1
    
    return patch_stats

def calculate_global_stats(docs):
    """Calcule les statistiques globales pour une base de données"""
    
    total_innovation = 0
    total_acid_features = 0
    total_alerts = 0
    
    ai_types_count = {}
    
    for doc in docs:
        # Innovation
        ai_analysis = doc.get('ai_analysis', {})
        if 'summary' in ai_analysis and 'new_feature' in ai_analysis['summary']:
            total_innovation += ai_analysis['summary']['new_feature']
        
        # Type dominant
        if 'dominant_type' in ai_analysis:
            dominant_type = ai_analysis['dominant_type']
            ai_types_count[dominant_type] = ai_types_count.get(dominant_type, 0) + 1
        
        # ACID features
        acid_features = doc.get('acid_consistency_features', {})
        if isinstance(acid_features, dict):
            total_acid_features += len([k for k, v in acid_features.items() if v])
        elif isinstance(acid_features, list):
            total_acid_features += len(acid_features)
        
        # Alerts
        alerts = doc.get('alerts', [])
        if alerts:
            total_alerts += len(alerts) if isinstance(alerts, list) else 1
    
    return {
        "total_innovation": total_innovation,
        "total_acid_features": total_acid_features,
        "total_alerts": total_alerts,
        "ai_types_distribution": ai_types_count
    }

def calculate_version_totals(patches):
    """Calcule les totaux pour une version majeure"""
    
    total_innovation = 0
    total_acid_features = 0
    total_alerts = 0
    
    for patch in patches:
        # Innovation
        ai_analysis = patch.get('ai_analysis', {})
        if 'summary' in ai_analysis and 'new_feature' in ai_analysis['summary']:
            total_innovation += ai_analysis['summary']['new_feature']
        
        # ACID features
        acid_features = patch.get('acid_consistency_features', {})
        if isinstance(acid_features, dict):
            total_acid_features += len([k for k, v in acid_features.items() if v])
        elif isinstance(acid_features, list):
            total_acid_features += len(acid_features)
        
        # Alerts
        alerts = patch.get('alerts', [])
        if alerts:
            total_alerts += len(alerts) if isinstance(alerts, list) else 1
    
    return {
        "total_innovation": total_innovation,
        "total_acid_features": total_acid_features,
        "total_alerts": total_alerts
    }

def show_sync_stats():
    """Affiche des statistiques détaillées après synchronisation"""
    try:
        print("\n📊 Statistiques après synchronisation:")
        print("-" * 40)
        
        # Total par base de données
        pipeline = [
            {"$group": {"_id": "$database", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        db_stats = list(collection_version.aggregate(pipeline))
        
        print("Répartition par base de données:")
        for stat in db_stats:
            print(f"  {stat['_id']}: {stat['count']} versions")
        
        # Versions les plus récentes par base de données
        print("\nDernières versions par base de données:")
        for db_stat in db_stats:
            db_name = db_stat['_id']
            
            # Trouver la version la plus récente pour cette base
            latest = collection_version.find_one(
                {"database": db_name},
                sort=[("patch_version", -1)]
            )
            
            if latest:
                print(f"  {db_name}: {latest.get('patch_version', 'N/A')}")
                
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage des statistiques: {e}")

def check_duplicates():
    """Vérifie s'il y a des doublons dans la base de données"""
    try:
        print("\n🔍 Vérification des doublons:")
        print("-" * 30)
        
        # Pipeline pour trouver les doublons
        pipeline = [
            {"$group": {
                "_id": {"database": "$database", "patch_version": "$patch_version"},
                "count": {"$sum": 1},
                "docs": {"$push": "$_id"}
            }},
            {"$match": {"count": {"$gt": 1}}}
        ]
        
        duplicates = list(collection_version.aggregate(pipeline))
        
        if duplicates:
            print(f"⚠️  {len(duplicates)} doublons trouvés:")
            for dup in duplicates[:5]:  # Limiter l'affichage
                print(f"  {dup['_id']['database']} {dup['_id']['patch_version']}: {dup['count']} occurrences")
        else:
            print("✅ Aucun doublon trouvé")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

if __name__ == "__main__":
    print("🔄 Synchronisation intelligente des patches")
    print("=" * 50)
    
    sync_new_patches()
    
    # Afficher les statistiques (nécessite une nouvelle connexion)
    try:
        client = MongoClient(MONGO_URI)
        db = client["VT"]
        collection_version = db["versions"]
        
        show_sync_stats()
        check_duplicates()
        
        # Générer le fichier JSON complet avec statistiques
        generate_comprehensive_stats()
        
    except Exception as e:
        print(f"⚠️  Impossible d'afficher les statistiques: {e}")
    finally:
        if 'client' in locals():
            client.close()
