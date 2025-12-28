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
    """Récupère les propriétés ACID/consistency de Neo4j depuis la documentation officielle."""
    print("Récupération des propriétés ACID/consistency de Neo4j...")
    
    url = "https://neo4j.com/blog/graph-database/acid-vs-base-consistency-models-explained/"
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
        
        # Trouver les sections ACID dans la page - approche plus large
        # Chercher dans les titres h2, h3, h4 et les paragraphes
        content = soup.find('article') or soup.find('main') or soup.find('div', class_='content') or soup
        
        # Chercher les mots-clés ACID dans tout le contenu
        all_text = content.get_text()
        
        # Patterns plus larges pour trouver les définitions
        acid_patterns = {
            'atomicity': [
                r'atomicity[:\s]*([^.!?]*[.!?])',
                r'atomic[:\s]*([^.!?]*[.!?])',
                r'atomicity.*?means.*?([^.!?]*[.!?])'
            ],
            'consistency': [
                r'consistency[:\s]*([^.!?]*[.!?])',
                r'consistent[:\s]*([^.!?]*[.!?])',
                r'consistency.*?means.*?([^.!?]*[.!?])'
            ],
            'isolation': [
                r'isolation[:\s]*([^.!?]*[.!?])',
                r'isolated[:\s]*([^.!?]*[.!?])',
                r'isolation.*?means.*?([^.!?]*[.!?])'
            ],
            'durability': [
                r'durability[:\s]*([^.!?]*[.!?])',
                r'durable[:\s]*([^.!?]*[.!?])',
                r'durability.*?means.*?([^.!?]*[.!?])'
            ]
        }
        
        # Essayer de trouver les définitions avec les patterns
        for prop, patterns in acid_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    acid_properties[prop] = matches[0].strip()
                    print(f"Trouvé {prop}: {acid_properties[prop][:100]}...")
                    break
        
        # Alternative: chercher dans les sections avec des titres contenant ACID
        if not any(acid_properties.values()):
            print("Recherche alternative dans les sections...")
            for heading in content.find_all(['h1', 'h2', 'h3', 'h4']):
                heading_text = heading.get_text().lower()
                if any(acid in heading_text for acid in ['acid', 'atomicity', 'consistency', 'isolation', 'durability']):
                    # Prendre les paragraphes suivants
                    next_element = heading.next_sibling
                    while next_element and next_element.name not in ['h1', 'h2', 'h3', 'h4']:
                        if next_element.name == 'p':
                            text = next_element.get_text(strip=True)
                            if len(text) > 20:  # Ignorer les textes trop courts
                                # Déterminer de quelle propriété ACID il s'agit
                                if 'atomic' in heading_text:
                                    acid_properties['atomicity'] = text
                                elif 'consist' in heading_text:
                                    acid_properties['consistency'] = text
                                elif 'isolat' in heading_text:
                                    acid_properties['isolation'] = text
                                elif 'durabil' in heading_text:
                                    acid_properties['durability'] = text
                        next_element = next_element.next_sibling
        
        print("Propriétés ACID récupérées avec succès")
        
    except Exception as e:
        print(f"Erreur lors de la récupération des propriétés ACID: {str(e)}")
    
    return acid_properties

def get_neo4j_versions() -> List[dict]:
    """Récupère les versions de Neo4j depuis la documentation officielle."""
    print("Récupération des versions de Neo4j...")
    
    url = "https://neo4j.com/developer/kb/neo4j-supported-versions/"
    
    versions = []
    
    try:
        print(f"Connexion à {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Chercher les tableaux ou listes de versions
        # Neo4j utilise souvent des tableaux pour afficher les versions supportées
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                
                if len(cells) >= 2:
                    # Essayer d'extraire la version depuis la première cellule
                    version_text = cells[0].get_text(strip=True)
                    
                    # Nettoyer et extraire le numéro de version
                    version_match = re.search(r'(\d+\.\d+(\.\d+)?)', version_text)
                    if version_match:
                        version = version_match.group(1)
                        
                        # Séparer les parties de la version
                        parts = version.split('.')
                        major_version = parts[0]
                        patch_version = '.'.join(parts[1:]) if len(parts) > 1 else '0'
                        
                        # Essayer d'extraire la date depuis la deuxième cellule
                        date_text = cells[1].get_text(strip=True)
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                        
                        if date_match:
                            formatted_date = date_match.group(1)
                        else:
                            # Essayer d'autres formats de date
                            date_patterns = [
                                r'(\d{1,2}/\d{1,2}/\d{4})',
                                r'(\w+ \d{1,2}, \d{4})',
                                r'(\w+ \d{4})'
                            ]
                            
                            formatted_date = "Date non disponible"
                            for pattern in date_patterns:
                                if re.search(pattern, date_text):
                                    formatted_date = date_text
                                    break
                        
                        # Vérifier si la version n'existe pas déjà
                        if not any(v['version'] == major_version and v['patch'] == patch_version for v in versions):
                            versions.append({
                                'version': major_version,
                                'patch': patch_version,
                                'date': formatted_date,
                                'url': f"https://neo4j.com/docs/{version}/",
                                'download_url': f"https://neo4j.com/artifact/?edition=community&version={version}&platform=linux"
                            })
                            
                            print(f"Trouvé: {version} - {formatted_date}")
        
        # Si aucun tableau trouvé, essayer de chercher dans les listes ou paragraphes
        if not versions:
            print("Recherche alternative des versions...")
            
            # Chercher les patterns de version dans tout le texte
            content = soup.get_text()
            version_pattern = re.compile(r'(\d+\.\d+(\.\d+)?)')
            found_versions = version_pattern.findall(content)
            
            # Extraire les versions uniques
            unique_versions = list(set([v[0] for v in found_versions]))
            unique_versions.sort(reverse=True)  # Plus récent en premier
            
            for version in unique_versions[:20]:  # Limiter à 20 versions
                parts = version.split('.')
                major_version = parts[0]
                patch_version = '.'.join(parts[1:]) if len(parts) > 1 else '0'
                
                versions.append({
                    'version': major_version,
                    'patch': patch_version,
                    'date': "Date non disponible",
                    'url': f"https://neo4j.com/docs/{version}/",
                    'download_url': f"https://neo4j.com/artifact/?edition=community&version={version}&platform=linux"
                })
                
                print(f"Trouvé: {version} - Date non disponible")
                    
    except Exception as e:
        print(f"Erreur lors de la récupération des versions: {str(e)}")
    
    return versions
    
def main():
    # Récupérer les propriétés ACID/consistency
    acid_properties = get_acid_properties()
    
    # Récupérer les versions
    versions = get_neo4j_versions()
    
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
    output_file = 'neo4j_versions.json'
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