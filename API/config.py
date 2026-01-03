# ==================== CONFIGURATION MONGODB ====================

# URI de connexion MongoDB Atlas
# Pour obtenir votre URI : https://cloud.mongodb.com → Connect → Drivers
MONGO_URI = "mongodb+srv://omarmesid_db_user:VEILLE123!@vt.2ed0h6t.mongodb.net/"

# Nom de la base de données
DATABASE_NAME = "VT"

# Noms des collections
COLLECTION_TABLES = "tables"
COLLECTION_VERSIONS = "versions"

# ==================== CONFIGURATION API ====================

# Port du serveur Django (par défaut : 8000)
API_PORT = 8000

# Hôte du serveur (par défaut : 127.0.0.1 pour local)
API_HOST = "127.0.0.1"

# Base URL de l'API
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# ==================== ROUTES API DISPONIBLES ====================

API_ENDPOINTS = {
    "status": {
        "path": "/api/",
        "method": "GET",
        "description": "Health check de l'API",
        "response_example": {"status": "ok"}
    },
    "technologies_list": {
        "path": "/api/technologies/",
        "method": "GET", 
        "description": "Liste de toutes les technologies disponibles",
        "response_example": {"technologies": ["MongoDB", "Redis", "..."]}
    },
    "versions": {
        "path": "/api/technologies/<tech>/versions/",
        "method": "GET",
        "description": "Récupère toutes les versions d'une technologie spécifique",
        "response_example": [{"database": "MongoDB", "major_version": "7.0", "...": "..."}]
    }
}

# ==================== TECHNOLOGIES DISPONIBLES ====================

# Liste des technologies supportées (sensible à la casse !)
# ⚠️ Les noms doivent correspondre EXACTEMENT aux noms dans la BDD
AVAILABLE_TECHNOLOGIES = [
    "MongoDB",
    "Neo4j", 
    "Redis",
    "Tidb",
    "YugabyteDB",
    "Cassandra",
    "CockroachDB"
]

# Aliases en minuscules pour la liste affichée (optionnel)
TECHNOLOGIES_DISPLAY = [
    "cassandra",
    "cockroachdb", 
    "mongodb",
    "neo4j",
    "redis",
    "tidb",
    "yugabyte"
]

# ==================== PARAMÈTRES REQUÊTES MONGODB ====================

# Nom du champ pour identifier la technologie dans la BDD
# Actuellement : "database" (ex: {"database": "MongoDB"})
# Si votre BDD utilise "tech", changez en : TECH_FIELD_NAME = "tech"
TECH_FIELD_NAME = "database"

# Exclure le champ _id dans les réponses JSON
EXCLUDE_ID_FIELD = True

# Projection MongoDB (champs à exclure/inclure)
MONGO_PROJECTION = {"_id": 0} if EXCLUDE_ID_FIELD else {}

# ==================== MESSAGES DE L'API ====================

# Messages de succès
SUCCESS_MESSAGES = {
    "api_ok": "ok",
    "data_retrieved": "Data retrieved successfully"
}

# Messages d'erreur
ERROR_MESSAGES = {
    "no_data": "no data found for this technology",
    "invalid_tech": "technology not found",
    "connection_failed": "failed to connect to database",
    "invalid_request": "invalid request"
}

# ==================== CONFIGURATION SSL MONGODB ====================

# Activer les options SSL personnalisées
# Mettre à True si vous avez des erreurs SSL avec MongoDB Atlas
USE_CUSTOM_SSL = True

# Options SSL pour MongoDB (utile pour résoudre les problèmes de connexion)
MONGO_SSL_OPTIONS = {
    "tls": True,
    "tlsAllowInvalidCertificates": True,
    "tlsAllowInvalidHostnames": True,
    "serverSelectionTimeoutMS": 15000,
    "connectTimeoutMS": 20000,
    "socketTimeoutMS": 20000
}

# ==================== PARAMÈTRES DE SÉCURITÉ ====================

# ⚠️ EN PRODUCTION : Utiliser des variables d'environnement !
# Exemple : MONGO_URI = os.getenv('MONGO_URI')

# Activer CORS (si vous avez un frontend séparé)
ENABLE_CORS = False

# Domaines autorisés pour CORS
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080"
]

# ==================== DOCUMENTATION DE L'API ====================

API_DOCUMENTATION = f"""
╔══════════════════════════════════════════════════════════════╗
║            API DJANGO - MONGODB ATLAS                        ║
║                 Documentation complète                       ║
╚══════════════════════════════════════════════════════════════╝

📍 BASE URL: {API_BASE_URL}

═══════════════════════════════════════════════════════════════

🔗 ENDPOINTS DISPONIBLES:

1️⃣  Health Check (Status)
   ├─ URL      : {API_BASE_URL}/api/
   ├─ Méthode  : GET
   ├─ Réponse  : {{"status": "ok"}}
   └─ Usage    : Vérifier que l'API fonctionne

2️⃣  Liste des technologies
   ├─ URL      : {API_BASE_URL}/api/technologies/
   ├─ Méthode  : GET
   ├─ Réponse  : {{"technologies": ["mongodb", "redis", ...]}}
   └─ Usage    : Obtenir la liste complète des technologies

3️⃣  Versions d'une technologie
   ├─ URL      : {API_BASE_URL}/api/technologies/<tech>/versions/
   ├─ Méthode  : GET
   ├─ Paramètre: <tech> = nom de la technologie (sensible à la casse!)
   ├─ Réponse  : [{{"database": "MongoDB", "major_version": "7.0", ...}}]
   └─ Usage    : Récupérer toutes les versions d'une technologie

═══════════════════════════════════════════════════════════════

📊 EXEMPLES D'URLS COMPLÈTES:

✅ Health Check:
   {API_BASE_URL}/api/

✅ Liste des technologies:
   {API_BASE_URL}/api/technologies/

✅ Versions par technologie:
"""

# Ajouter dynamiquement les exemples pour chaque technologie
for tech in AVAILABLE_TECHNOLOGIES:
    API_DOCUMENTATION += f"   • {tech:15} → {API_BASE_URL}/api/technologies/{tech}/versions/\n"

API_DOCUMENTATION += f"""
═══════════════════════════════════════════════════════════════

⚠️  IMPORTANT - SENSIBILITÉ À LA CASSE:
   ✅ Correct  : /api/technologies/MongoDB/versions/
   ❌ Incorrect: /api/technologies/mongodb/versions/

═══════════════════════════════════════════════════════════════

📚 INFORMATIONS BASE DE DONNÉES:

   Base de données    : {DATABASE_NAME}
   Collection tables  : {COLLECTION_TABLES} ({len(AVAILABLE_TECHNOLOGIES)} technologies)
   Collection versions: {COLLECTION_VERSIONS} (836 versions)
   Champ technologie  : {TECH_FIELD_NAME}

═══════════════════════════════════════════════════════════════

🔐 CONFIGURATION REQUISE:

 . Lancer le serveur
      → python manage.py runserver

═══════════════════════════════════════════════════════════════

💡 STRUCTURE DES DONNÉES:

   Collection "tables":
   {{
     "database": "MongoDB",
     "category": "document", 
     "type": "NoSQL",
     "_type": "database"
   }}

   Collection "versions":
   {{
     "database": "MongoDB",
     "major_version": "7.0",
     "patch_version": "7.0.26",
     "date": "2025-11-21",
     "ai_analysis": {{
       "dominant_type": "bug_fix",
       "summary": {{...}},
       "details": [...]
     }}
   }}

═══════════════════════════════════════════════════════════════
"""

# ==================== FONCTIONS UTILITAIRES ====================

def print_api_info():
    """Afficher la documentation complète de l'API"""
    print(API_DOCUMENTATION)

def get_full_url(endpoint_key):
    """
    Obtenir l'URL complète d'un endpoint
    
    Args:
        endpoint_key (str): Clé de l'endpoint ('status', 'technologies_list', 'versions')
    
    Returns:
        str: URL complète
    """
    endpoint = API_ENDPOINTS.get(endpoint_key, {}).get("path", "")
    return f"{API_BASE_URL}{endpoint}"

def list_all_urls():
    """Lister toutes les URLs disponibles"""
    urls = []
    
    # URL Status
    urls.append({
        "name": "Health Check",
        "url": get_full_url("status"),
        "method": "GET"
    })
    
    # URL Technologies
    urls.append({
        "name": "Liste des technologies",
        "url": get_full_url("technologies_list"),
        "method": "GET"
    })
    
    # URLs Versions
    for tech in AVAILABLE_TECHNOLOGIES:
        urls.append({
            "name": f"Versions {tech}",
            "url": f"{API_BASE_URL}/api/technologies/{tech}/versions/",
            "method": "GET"
        })
    
    return urls

def print_all_urls():
    """Afficher toutes les URLs de manière formatée"""
    print("\n🔗 TOUTES LES URLs DISPONIBLES:\n")
    print("=" * 80)
    
    urls = list_all_urls()
    for i, endpoint in enumerate(urls, 1):
        print(f"{i:2d}. [{endpoint['method']}] {endpoint['name']}")
        print(f"    {endpoint['url']}")
        print()

def get_config_summary():
    """Résumé de la configuration actuelle"""
    return {
        "api_host": API_HOST,
        "api_port": API_PORT,
        "database": DATABASE_NAME,
        "collections": {
            "tables": COLLECTION_TABLES,
            "versions": COLLECTION_VERSIONS
        },
        "technologies_count": len(AVAILABLE_TECHNOLOGIES),
        "ssl_enabled": USE_CUSTOM_SSL,
        "tech_field": TECH_FIELD_NAME
    }

def print_config_summary():
    """Afficher le résumé de la configuration"""
    config = get_config_summary()
    print("\n⚙️  RÉSUMÉ DE LA CONFIGURATION:\n")
    print("=" * 50)
    print(f"API Host          : {config['api_host']}")
    print(f"API Port          : {config['api_port']}")
    print(f"Base de données   : {config['database']}")
    print(f"Collection tables : {config['collections']['tables']}")
    print(f"Collection versions: {config['collections']['versions']}")
    print(f"Technologies      : {config['technologies_count']}")
    print(f"SSL personnalisé  : {'✅ Activé' if config['ssl_enabled'] else '❌ Désactivé'}")
    print(f"Champ techno      : {config['tech_field']}")
    print("=" * 50)

# ==================== EXÉCUTION DIRECTE ====================

if __name__ == "__main__":
    """
    Exécuter ce fichier directement pour voir la documentation:
    python -m API.config
    """
    print("\n" + "=" * 80)
    print(" " * 20 + "🚀 API CONFIGURATION & DOCUMENTATION")
    print("=" * 80)
    
    # Afficher le résumé de la config
    print_config_summary()
    
    # Afficher toutes les URLs
    print_all_urls()
    
    # Afficher la documentation complète
    print("\n" + "=" * 80)
    print(" " * 25 + "📖 DOCUMENTATION COMPLÈTE")
    print("=" * 80)
    print_api_info()
    
    print("\n" + "=" * 80)
    print("💡 TIP: Pour utiliser cette config dans votre code:")
    print("   from API.config import MONGO_URI, AVAILABLE_TECHNOLOGIES, ...")
    print("=" * 80 + "\n")
