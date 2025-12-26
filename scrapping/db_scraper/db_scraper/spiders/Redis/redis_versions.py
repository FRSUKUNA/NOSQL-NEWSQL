import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time
from typing import Dict, List, Optional

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_acid_properties() -> Dict[str, str]:
    """Récupère les propriétés ACID/consistency de Redis depuis la documentation officielle."""
    print("Récupération des propriétés ACID/consistency de Redis...")
    
    url = "https://redis.io/glossary/acid-transactions/"
    acid_properties = {
        'atomicity': '',
        'consistency': '',
        'isolation': '',
        'durability': ''
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trouver les sections ACID dans la page
        for h3 in soup.find_all('h3'):
            text = h3.get_text().lower()
            if 'atomicity' in text:
                acid_properties['atomicity'] = h3.find_next('p').get_text(strip=True)
            elif 'consistency' in text:
                acid_properties['consistency'] = h3.find_next('p').get_text(strip=True)
            elif 'isolation' in text:
                acid_properties['isolation'] = h3.find_next('p').get_text(strip=True)
            elif 'durability' in text:
                acid_properties['durability'] = h3.find_next('p').get_text(strip=True)
        
        print("Propriétés ACID récupérées avec succès")
        
    except Exception as e:
        print(f"Erreur lors de la récupération des propriétés ACID: {str(e)}")
    
    return acid_properties

def get_redis_versions() -> List[dict]:
    print("Récupération des versions de Redis...")
    
    # URL de la page des versions de Redis
    base_url = "https://raw.githubusercontent.com/redis/redis/"
    tags_url = "https://api.github.com/repos/redis/redis/tags"
    
    versions = []
    
    try:
        # Récupérer les tags de version depuis GitHub API
        print("Connexion à l'API GitHub...")
        response = requests.get(tags_url, headers=headers, timeout=30)
        response.raise_for_status()
        tags = response.json()
        
        # Filtrer les versions (format X.Y.Z)
        version_pattern = re.compile(r'^\d+\.\d+\.\d+$')
        
        for tag in tags:
            version = tag['name'].replace('v', '')  # Enlever le 'v' du début
            
            # Vérifier si c'est une version valide (format X.Y.Z)
            if version_pattern.match(version):
                # Séparer les parties de la version
                parts = version.split('.')
                major_version = parts[0]  # Premier chiffre
                patch_version = '.'.join(parts[1:])  # Le reste
                
                # Récupérer la date du commit
                commit_url = tag['commit']['url']
                commit_response = requests.get(commit_url, headers=headers, timeout=30)
                
                if commit_response.status_code == 200:
                    commit_data = commit_response.json()
                    date_str = commit_data['commit']['committer']['date']
                    # Formater la date
                    date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                else:
                    formatted_date = "Date non disponible"
                
                versions.append({
                    'version': major_version,  # Seulement le premier chiffre
                    'patch': patch_version,    # Le reste de la version
                    'date': formatted_date,
                    'url': f"https://github.com/redis/redis/releases/tag/v{version}",
                    'download_url': f"https://download.redis.io/releases/redis-{version}.tar.gz"
                })
                
                print(f"Trouvé: {version} - {formatted_date}")
                
                # Limiter le nombre de versions à récupérer pour les tests
                if len(versions) >= 20:  # Augmentez ce nombre si nécessaire
                    break
                    
    except Exception as e:
        print(f"Erreur lors de la récupération des versions: {str(e)}")
    
    return versions
    
def main():
    # Récupérer les propriétés ACID/consistency
    acid_properties = get_acid_properties()
    
    # Récupérer les versions
    versions = get_redis_versions()
    
    if not versions:
        print("Aucune version trouvée.")
        return
    
    # Trier les versions par numéro de version (du plus récent au plus ancien)
    versions.sort(key=lambda x: [int(n) for n in x['version'].split('.')], reverse=True)
    
    # Préparer les données à sauvegarder
    output_data = {
        'acid_properties': acid_properties,
        'versions': versions,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    
    # Sauvegarder dans un fichier JSON
    output_file = 'redis_versions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n{len(versions)} versions trouvées et sauvegardées dans {output_file}")
    print("\nPropriétés ACID/consistency récupérées:")
    for prop, value in acid_properties.items():
        print(f"- {prop.capitalize()}: {value[:100]}..." if len(value) > 100 else f"- {prop.capitalize()}: {value}")
    
    print("\nAperçu des versions :")
    for i, ver in enumerate(versions[:5], 1):
        print(f"{i}. Version: {ver['version']}.{ver['patch']} (Maj: {ver['version']}, Patch: {ver['patch']}) - {ver['date']}")
    if len(versions) > 5:
        print(f"... et {len(versions) - 5} versions supplémentaires")

if __name__ == "__main__":
    main()
