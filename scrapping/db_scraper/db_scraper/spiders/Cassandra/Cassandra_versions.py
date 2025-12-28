import requests
import re
import json
from datetime import datetime
from typing import Dict, List, Optional

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_cassandra_versions() -> List[dict]:
    """Récupère les versions de Cassandra depuis le fichier CHANGES.txt."""
    print("Récupération des versions de Cassandra...")
    
    # Utiliser l'URL raw pour obtenir le contenu brut du fichier
    url = "https://raw.githubusercontent.com/apache/cassandra/trunk/CHANGES.txt"
    
    versions = []
    
    try:
        print(f"Connexion à {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        content = response.text
        lines = content.split('\n')
        
        current_version = None
        current_changes = []
        version_pattern = re.compile(r'^(\d+\.\d+)(?:\.(\d+))?(?:\.(\d+))?$')
        
        for line in lines:
            line = line.strip()
            
            # Vérifier si c'est une ligne de version
            version_match = version_pattern.match(line)
            if version_match:
                # Sauvegarder la version précédente si elle existe
                if current_version and current_changes:
                    versions.append(current_version)
                
                # Extraire les parties de la version
                major = version_match.group(1)
                minor = version_match.group(2) if version_match.group(2) else "0"
                patch = version_match.group(3) if version_match.group(3) else "0"
                
                version_str = f"{major}.{minor}"
                if version_match.group(3):
                    version_str += f".{patch}"
                
                current_version = {
                    'version': major,
                    'patch': f"{minor}.{patch}" if version_match.group(3) else minor,
                    'full_version': version_str,
                    'date': "Date non disponible",
                    'url': f"https://cassandra.apache.org/doc/{version_str}/",
                    'download_url': f"https://cassandra.apache.org/_download/",
                    'changes_count': 0,
                    'changes': []
                }
                current_changes = []
                print(f"Trouvé version: {version_str}")
            
            # Vérifier si c'est un changement (commence par * et contient CASSANDRA-)
            elif current_version and line.startswith('* ') and 'CASSANDRA-' in line:
                # Nettoyer la ligne de changement
                change = line[2:].strip()  # Enlever le "* "
                current_changes.append(change)
                current_version['changes'] = current_changes.copy()
                current_version['changes_count'] = len(current_changes)
            
            # Vérifier si c'est une ligne de merge
            elif current_version and line.startswith('Merged from'):
                # C'est une information de merge, on l'ajoute comme changement spécial
                current_changes.append(f"[MERGE] {line}")
                current_version['changes'] = current_changes.copy()
                current_version['changes_count'] = len(current_changes)
        
        # Ajouter la dernière version
        if current_version and current_changes:
            versions.append(current_version)
        
        # Si aucune version trouvée avec le pattern principal, essayer une approche alternative
        if not versions:
            print("Recherche alternative des versions...")
            
            # Chercher tous les patterns de version dans le texte
            all_versions = version_pattern.findall(content)
            
            # Créer des entrées de version uniques
            unique_versions = {}
            for match in all_versions:
                major = match[0]
                minor = match[1] if match[1] else "0"
                patch = match[2] if match[2] else "0"
                
                version_str = f"{major}.{minor}"
                if match[2]:
                    version_str += f".{patch}"
                
                if version_str not in unique_versions:
                    unique_versions[version_str] = {
                        'version': major,
                        'patch': f"{minor}.{patch}" if match[2] else minor,
                        'full_version': version_str,
                        'date': "Date non disponible",
                        'url': f"https://cassandra.apache.org/doc/{version_str}/",
                        'download_url': f"https://cassandra.apache.org/_download/",
                        'changes_count': 0,
                        'changes': []
                    }
            
            versions = list(unique_versions.values())
            versions.sort(key=lambda x: [int(n) for n in x['full_version'].split('.')], reverse=True)
            
            for version in versions[:20]:  # Limiter à 20 versions
                print(f"Trouvé: {version['full_version']} - Date non disponible")
        
        # Tenter d'extraire des dates des changements si disponibles
        for version in versions:
            dates_found = []
            for change in version['changes']:
                # Chercher des patterns de date dans les changements
                date_patterns = [
                    r'(\d{4}-\d{2}-\d{2})',
                    r'(\d{1,2}/\d{1,2}/\d{4})',
                    r'(\w+ \d{1,2}, \d{4})',
                    r'(\w+ \d{4})'
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, change)
                    dates_found.extend(matches)
            
            if dates_found:
                version['date'] = dates_found[0]  # Prendre la première date trouvée
        
    except Exception as e:
        print(f"Erreur lors de la récupération des versions: {str(e)}")
    
    return versions

def get_cassandra_properties() -> Dict[str, str]:
    """Récupère les propriétés de consistency de Cassandra depuis la documentation officielle."""
    print("Récupération des propriétés de consistency de Cassandra...")
    
    # Adapter les catégories pour correspondre aux concepts de consistency Cassandra
    properties = {
        'strong_consistency': '',
        'eventual_consistency': '',
        'consistency_levels': '',
        'tunable_consistency': '',
        'write_operations': '',
        'read_operations': ''
    }
    
    try:
        # URL de la documentation officielle Apache Cassandra sur la consistency
        url = "https://cassandra.apache.org/doc/latest/cassandra/architecture/guarantees.html"
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraire le contenu principal
        content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
        
        all_text = content.get_text()
        
        # Patterns adaptés pour Cassandra consistency
        consistency_patterns = {
            'strong_consistency': [
                r'strong consistency[:\s]*([^.!?]*[.!?])',
                r'linearizable consistency[:\s]*([^.!?]*[.!?])',
                r'strict consistency[:\s]*([^.!?]*[.!?])'
            ],
            'eventual_consistency': [
                r'eventual consistency[:\s]*([^.!?]*[.!?])',
                r'eventually consistent[:\s]*([^.!?]*[.!?])',
                r'weak consistency[:\s]*([^.!?]*[.!?])'
            ],
            'consistency_levels': [
                r'consistency levels?[:\s]*([^.!?]*[.!?])',
                r'levels of consistency[:\s]*([^.!?]*[.!?])',
                r'ONE.*?QUORUM.*?ALL[:\s]*([^.!?]*[.!?])'
            ],
            'tunable_consistency': [
                r'tunable consistency[:\s]*([^.!?]*[.!?])',
                r'tunable[:\s]*([^.!?]*[.!?])',
                r'configurable consistency[:\s]*([^.!?]*[.!?])',
                r'per operation[:\s]*([^.!?]*[.!?])'
            ],
            'write_operations': [
                r'write operations?[:\s]*([^.!?]*[.!?])',
                r'write consistency[:\s]*([^.!?]*[.!?])',
                r'writes?[:\s]*([^.!?]*[.!?])'
            ],
            'read_operations': [
                r'read operations?[:\s]*([^.!?]*[.!?])',
                r'read consistency[:\s]*([^.!?]*[.!?])',
                r'reads?[:\s]*([^.!?]*[.!?])'
            ]
        }
        
        # Chercher les patterns dans le texte
        for prop, patterns in consistency_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, all_text, re.IGNORECASE)
                if matches:
                    properties[prop] = matches[0].strip()
                    break
        
        # Si rien trouvé, essayer une recherche par sections
        if not any(properties.values()):
            print("Recherche alternative des propriétés...")
            
            # Chercher des sections spécifiques
            headings = content.find_all(['h1', 'h2', 'h3', 'h4'])
            
            for heading in headings:
                heading_text = heading.get_text(strip=True).lower()
                
                # Chercher le contenu après chaque titre pertinent
                if any(keyword in heading_text for keyword in ['consistency', 'guarantees', 'levels', 'tunable', 'strong', 'eventual']):
                    next_elements = []
                    current = heading.next_sibling
                    
                    # Collecter les prochains éléments jusqu'au prochain titre
                    while current and current.name not in ['h1', 'h2', 'h3', 'h4']:
                        if hasattr(current, 'get_text'):
                            text = current.get_text(strip=True)
                            if text and len(text) > 20:
                                next_elements.append(text)
                        current = current.next_sibling
                    
                    section_text = ' '.join(next_elements)
                    
                    # Assigner le contenu à la propriété appropriée
                    if 'strong' in heading_text and not properties['strong_consistency']:
                        properties['strong_consistency'] = section_text[:300] + "..." if len(section_text) > 300 else section_text
                    elif 'eventual' in heading_text and not properties['eventual_consistency']:
                        properties['eventual_consistency'] = section_text[:300] + "..." if len(section_text) > 300 else section_text
                    elif 'levels' in heading_text and not properties['consistency_levels']:
                        properties['consistency_levels'] = section_text[:300] + "..." if len(section_text) > 300 else section_text
                    elif 'tunable' in heading_text and not properties['tunable_consistency']:
                        properties['tunable_consistency'] = section_text[:300] + "..." if len(section_text) > 300 else section_text
                    elif 'write' in heading_text and not properties['write_operations']:
                        properties['write_operations'] = section_text[:300] + "..." if len(section_text) > 300 else section_text
                    elif 'read' in heading_text and not properties['read_operations']:
                        properties['read_operations'] = section_text[:300] + "..." if len(section_text) > 300 else section_text
        
        # Dernière tentative : recherche par mots-clés spécifiques à Cassandra
        if not any(properties.values()):
            print("Recherche par mots-clés Cassandra...")
            
            keywords_mapping = {
                'strong_consistency': ['strong consistency', 'linearizable', 'strict consistency', 'serializable'],
                'eventual_consistency': ['eventual consistency', 'eventually consistent', 'weak consistency', 'eventual'],
                'consistency_levels': ['ONE', 'QUORUM', 'ALL', 'LOCAL_QUORUM', 'EACH_QUORUM', 'consistency levels'],
                'tunable_consistency': ['tunable', 'configurable', 'per operation', 'adjustable consistency'],
                'write_operations': ['write', 'write consistency', 'write operations', 'writes'],
                'read_operations': ['read', 'read consistency', 'read operations', 'reads']
            }
            
            for prop, keywords in keywords_mapping.items():
                if not properties[prop]:
                    for keyword in keywords:
                        lines = all_text.split('\n')
                        for line in lines:
                            if keyword.lower() in line.lower() and len(line) > 30:
                                properties[prop] = line.strip()
                                break
                        if properties[prop]:
                            break
        
        # Si toujours rien trouvé, fournir des informations par défaut sur Cassandra
        if not any(properties.values()):
            print("Utilisation des informations par défaut sur Cassandra consistency...")
            properties = {
                'strong_consistency': 'Cassandra provides strong consistency when using QUORUM or ALL consistency levels for both read and write operations in the same data center.',
                'eventual_consistency': 'Cassandra provides eventual consistency when using lower consistency levels like ONE or when reads and writes use different consistency levels.',
                'consistency_levels': 'Cassandra supports multiple consistency levels: ONE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM, LOCAL_ONE for read operations and ANY, ONE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM for write operations.',
                'tunable_consistency': 'Cassandra offers tunable consistency, allowing developers to specify the desired consistency level on a per-operation basis.',
                'write_operations': 'Write operations in Cassandra can use ANY, ONE, QUORUM, ALL, LOCAL_QUORUM, or EACH_QUORUM consistency levels.',
                'read_operations': 'Read operations in Cassandra can use ONE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM, or LOCAL_ONE consistency levels.'
            }
        
    except Exception as e:
        print(f"Erreur lors de la récupération des propriétés: {str(e)}")
        
        # En cas d'erreur, utiliser les informations par défaut
        properties = {
            'strong_consistency': 'Cassandra provides strong consistency when using QUORUM or ALL consistency levels for both read and write operations in the same data center.',
            'eventual_consistency': 'Cassandra provides eventual consistency when using lower consistency levels like ONE or when reads and writes use different consistency levels.',
            'consistency_levels': 'Cassandra supports multiple consistency levels: ONE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM, LOCAL_ONE for read operations and ANY, ONE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM for write operations.',
            'tunable_consistency': 'Cassandra offers tunable consistency, allowing developers to specify the desired consistency level on a per-operation basis.',
            'write_operations': 'Write operations in Cassandra can use ANY, ONE, QUORUM, ALL, LOCAL_QUORUM, or EACH_QUORUM consistency levels.',
            'read_operations': 'Read operations in Cassandra can use ONE, QUORUM, ALL, LOCAL_QUORUM, EACH_QUORUM, or LOCAL_ONE consistency levels.'
        }
    
    return properties

def main():
    """Fonction principale pour exécuter le scraping des versions Cassandra."""
    print("=== Extraction des Versions Cassandra ===")
    
    # Récupérer les propriétés de consistency
    consistency_properties = get_cassandra_properties()
    
    # Récupérer les versions
    versions = get_cassandra_versions()
    
    if not versions:
        print("Aucune version trouvée.")
        return
    
    # Trier les versions par numéro de version (du plus récent au plus ancien)
    versions.sort(key=lambda x: [int(n) for n in x['full_version'].split('.')], reverse=True)
    
    # Préparer les données à sauvegarder
    output_data = {
        'consistency_properties': consistency_properties,
        'versions': versions,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'total_versions': len(versions),
        'total_changes': sum(v['changes_count'] for v in versions)
    }
    
    # Sauvegarder dans un fichier JSON
    output_file = 'cassandra_versions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n{len(versions)} versions trouvées et sauvegardées dans {output_file}")
    print(f"Total des changements: {output_data['total_changes']}")
    
    print("\nPropriétés de consistency récupérées:")
    for prop, value in consistency_properties.items():
        print(f"- {prop.replace('_', ' ').title()}: {value[:100]}..." if len(value) > 100 else f"- {prop.replace('_', ' ').title()}: {value}")
    
    print("\nAperçu des versions :")
    for i, ver in enumerate(versions[:5], 1):
        print(f"{i}. Version: {ver['full_version']} (Maj: {ver['version']}, Patch: {ver['patch']}) - {ver['date']} - {ver['changes_count']} changements")
    if len(versions) > 5:
        print(f"... et {len(versions) - 5} versions supplémentaires")

if __name__ == "__main__":
    main()
