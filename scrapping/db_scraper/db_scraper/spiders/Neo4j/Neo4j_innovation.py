import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
import re

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_neo4j_release_notes() -> List[Dict]:
    """Récupère toutes les notes de version depuis le changelog GitHub Neo4j."""
    try:
        # URL du changelog GitHub Neo4j
        url = "https://github.com/neo4j/neo4j/wiki/Neo4j-2025-changelog/"
        print(f"Récupération des notes de version depuis {url}...")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Récupérer le contenu principal de la page wiki GitHub
        content = soup.find('div', class_='markdown-body') or soup.find('article') or soup.find('main')
        if not content:
            print("Contenu principal non trouvé")
            return []
        
        all_versions = []
        current_version = None
        current_changes = []
        
        # Pattern pour détecter les versions (plus flexible)
        version_pattern = re.compile(r'(\d{4}\.\d{2}\.\d+)')
        
        # Parcourir tous les éléments
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'div']):
            element_text = element.get_text(strip=True)
            
            # Vérifier si c'est une ligne de version
            version_match = version_pattern.match(element_text)
            if version_match:
                # Sauvegarder la version précédente si elle existe
                if current_version and current_changes:
                    all_versions.append(current_version)
                
                version_str = version_match.group(1)
                print(f"Version trouvée: {version_str}")
                
                # Créer la nouvelle version
                current_version = {
                    'version': version_str,
                    'date': "Date non disponible",
                    'url': f"https://neo4j.com/docs/{version_str}/",
                    'download_url': f"https://neo4j.com/artifact/?edition=community&version={version_str}&platform=linux",
                    'changes_count': 0,
                    'changes': []
                }
                current_changes = []
            
            # Vérifier si c'est un changement (commence avec * ou - et contient du texte significatif)
            elif current_version and element_text and len(element_text) > 10:
                # Nettoyer la ligne de changement
                if element_text.startswith(('* ', '- ', '• ')):
                    change = element_text[2:].strip() if element_text.startswith(('* ', '- ')) else element_text[1:].strip()
                else:
                    change = element_text
                
                # Vérifier si le changement contient des mots-clés significatifs
                if any(keyword in change.lower() for keyword in ['fix', 'add', 'improve', 'update', 'remove', 'change', 'support', 'new', 'optimize', 'enhance']):
                    current_changes.append(change)
                    current_version['changes'] = current_changes.copy()
                    current_version['changes_count'] = len(current_changes)
            
            # Traiter les listes spécialement
            elif current_version and element.name in ['ul', 'ol']:
                for li in element.find_all('li'):
                    li_text = li.get_text(strip=True)
                    if li_text and len(li_text) > 10:
                        # Nettoyer le texte
                        if li_text.startswith(('* ', '- ', '• ')):
                            change = li_text[2:].strip() if li_text.startswith(('* ', '- ')) else li_text[1:].strip()
                        else:
                            change = li_text
                        
                        # Vérifier si le changement contient des mots-clés significatifs
                        if any(keyword in change.lower() for keyword in ['fix', 'add', 'improve', 'update', 'remove', 'change', 'support', 'new', 'optimize', 'enhance']):
                            current_changes.append(change)
                            current_version['changes'] = current_changes.copy()
                            current_version['changes_count'] = len(current_changes)
        
        # Ajouter la dernière version
        if current_version and current_changes:
            all_versions.append(current_version)
        
        # Si aucune version trouvée avec le pattern principal, essayer une approche plus large
        if not all_versions:
            print("Recherche alternative des versions...")
            all_text = content.get_text()
            
            # Chercher toutes les mentions de versions dans tout le texte
            version_matches = version_pattern.findall(all_text)
            unique_versions = list(set(version_matches))
            unique_versions.sort(reverse=True)  # Plus récent en premier
            
            for version_str in unique_versions[:20]:  # Limiter à 20 versions
                print(f"Version trouvée (alternative): {version_str}")
                
                # Chercher les changements associés à cette version
                version_changes = []
                lines = all_text.split('\n')
                
                for i, line in enumerate(lines):
                    if version_str in line:
                        # Ajouter cette ligne et les quelques lignes suivantes
                        for j in range(i, min(len(lines), i + 10)):
                            context_line = lines[j].strip()
                            if context_line and len(context_line) > 10:
                                # Nettoyer la ligne
                                if context_line.startswith(('* ', '- ', '• ')):
                                    change = context_line[2:].strip() if context_line.startswith(('* ', '- ')) else context_line[1:].strip()
                                else:
                                    change = context_line
                                
                                # Vérifier si c'est un changement significatif
                                if any(keyword in change.lower() for keyword in ['fix', 'add', 'improve', 'update', 'remove', 'change', 'support', 'new', 'optimize', 'enhance']):
                                    version_changes.append(change)
                
                all_versions.append({
                    'version': version_str,
                    'date': "Date non disponible",
                    'url': f"https://neo4j.com/docs/{version_str}/",
                    'download_url': f"https://neo4j.com/artifact/?edition=community&version={version_str}&platform=linux",
                    'changes_count': len(version_changes),
                    'changes': version_changes
                })
        
        # Tenter d'extraire des dates des changements si disponibles
        for version in all_versions:
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
        
        print(f"Total de versions trouvées: {len(all_versions)}")
        return all_versions
        
    except Exception as e:
        print(f"Erreur lors de la récupération des notes de version: {e}")
        return []

def detect_section_type(title: str) -> str:
    """Détecte le type de section en fonction du titre."""
    title_lower = title.lower()
    
    if any(keyword in title_lower for keyword in ['performance', 'optimization', 'speed', 'fast']):
        return 'performance'
    elif any(keyword in title_lower for keyword in ['security', 'vulnerability', 'fix', 'patch']):
        return 'security'
    elif any(keyword in title_lower for keyword in ['feature', 'new', 'added', 'introduced']):
        return 'feature'
    elif any(keyword in title_lower for keyword in ['graph algorithm', 'algorithm', 'cypher', 'query']):
        return 'algorithm'
    elif any(keyword in title_lower for keyword in ['api', 'driver', 'protocol']):
        return 'api'
    elif any(keyword in title_lower for keyword in ['breaking change', 'deprecated', 'removed']):
        return 'breaking_change'
    else:
        return 'general'

def extract_innovations(sections: List[Dict]) -> Dict[str, List[str]]:
    """Extrait les innovations des sections de notes de version."""
    innovations = {
        'performance_improvements': [],
        'security_fixes': [],
        'new_features': [],
        'graph_algorithms': [],
        'api_changes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    innovation_keywords = {
        'performance_improvements': ['performance', 'optimization', 'speed', 'fast', 'improved', 'faster'],
        'security_fixes': ['security', 'vulnerability', 'fix', 'patch', 'secure', 'authentication'],
        'new_features': ['feature', 'new', 'added', 'introduced', 'support for'],
        'graph_algorithms': ['graph algorithm', 'algorithm', 'cypher', 'query', 'traversal'],
        'api_changes': ['api', 'driver', 'protocol', 'interface', 'endpoint'],
        'breaking_changes': ['breaking change', 'deprecated', 'removed', 'changed']
    }
    
    for section in sections:
        section_text = ' '.join(section['content'])
        section_type = section['type']
        
        # Ajouter le contenu à la catégorie appropriée
        if section_type in innovations:
            innovations[section_type].extend([
                f"{section['title']}: {content}"
                for content in section['content']
                if len(content) > 20
            ])
        
        # Recherche supplémentaire par mots-clés
        for category, keywords in innovation_keywords.items():
            if any(keyword in section_text.lower() for keyword in keywords):
                if category not in innovations or section_type != category:
                    innovations[category].extend([
                        f"{section['title']}: {content}"
                        for content in section['content']
                        if len(content) > 20 and any(keyword in content.lower() for keyword in keywords)
                    ])
    
    # Nettoyer les doublons
    for category in innovations:
        innovations[category] = list(set(innovations[category]))
    
    return innovations

def analyze_innovations(all_innovations: Dict) -> Dict:
    """Analyse les innovations et génère des insights."""
    analysis = {
        'summary': {},
        'key_innovations': {},
        'trends': {}
    }
    
    # Résumé par catégorie
    for category, innovations in all_innovations.items():
        analysis['summary'][category] = {
            'count': len(innovations),
            'items': innovations[:5]  # Top 5 par catégorie
        }
    
    # Innovations clés
    all_items = []
    for category, innovations in all_innovations.items():
        for item in innovations:
            all_items.append({
                'category': category,
                'content': item
            })
    
    # Trier par pertinence (longueur et mots-clés)
    all_items.sort(key=lambda x: len(x['content']), reverse=True)
    analysis['key_innovations'] = all_items[:10]
    
    # Tendances
    analysis['trends'] = {
        'most_active_category': max(all_innovations.keys(), key=lambda k: len(all_innovations[k])),
        'total_innovations': sum(len(innovations) for innovations in all_innovations.values())
    }
    
    return analysis

def generate_innovation_report() -> Dict:
    """Génère un rapport complet sur les innovations Neo4j organisé par version."""
    print("Début de l'analyse des innovations Neo4j...")
    
    # Charger les versions depuis le fichier JSON
    try:
        with open('neo4j_versions.json', 'r', encoding='utf-8') as f:
            versions_data = json.load(f)
            versions = versions_data.get('versions', [])
    except FileNotFoundError:
        print("Erreur: Fichier neo4j_versions.json non trouvé. Exécutez d'abord Neo4j_versions.py")
        return {'error': 'Fichier neo4j_versions.json non trouvé'}
    
    if not versions:
        print("Aucune version trouvée dans le fichier JSON.")
        return {'error': 'Aucune version disponible'}
    
    # Analyser les 5 dernières versions
    latest_versions = versions[:5]
    
    # Structure organisée par version
    versions_with_innovations = []
    all_innovations = {
        'performance_improvements': [],
        'security_fixes': [],
        'new_features': [],
        'graph_algorithms': [],
        'api_changes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    for version_info in latest_versions:
        version = f"{version_info['version']}.{version_info['patch']}"
        print(f"\nAnalyse de la version {version}...")
        
        # Récupérer les notes de version
        sections = get_neo4j_release_notes(version)
        
        if sections:
            # Extraire les innovations pour cette version
            innovations = extract_innovations(sections)
            
            # Créer l'entrée pour cette version
            version_entry = {
                'version': version,
                'date': version_info['date'],
                'url': version_info['url'],
                'sections_count': len(sections),
                'innovations': innovations,
                'total_innovations': sum(len(innovations[cat]) for cat in innovations)
            }
            
            versions_with_innovations.append(version_entry)
            
            # Ajouter aux totaux globaux
            for category in all_innovations:
                all_innovations[category].extend(innovations[category])
        else:
            print(f"Aucune section trouvée pour la version {version}")
            versions_with_innovations.append({
                'version': version,
                'date': version_info['date'],
                'url': version_info['url'],
                'sections_count': 0,
                'innovations': {cat: [] for cat in all_innovations.keys()},
                'total_innovations': 0
            })
    
    # Nettoyer les doublons dans les totaux globaux
    for category in all_innovations:
        all_innovations[category] = list(set(all_innovations[category]))
    
    # Analyser les innovations globales
    analysis = analyze_innovations(all_innovations)
    
    # Créer le rapport final avec la nouvelle structure
    report = {
        'report_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'summary': {
            'total_versions_analyzed': len(versions_with_innovations),
            'total_innovations': sum(v['total_innovations'] for v in versions_with_innovations),
            'versions_with_innovations': len([v for v in versions_with_innovations if v['total_innovations'] > 0])
        },
        'versions': versions_with_innovations,
        'global_analysis': {
            'innovations_by_category': all_innovations,
            'analysis': analysis
        }
    }

    # Sauvegarder le rapport
    output_file = 'neo4j_innovations_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\nRapport d'innovations sauvegardé dans {output_file}")
    print(f"Versions analysées: {len(versions_with_innovations)}")
    print(f"Total d'innovations trouvées: {report['summary']['total_innovations']}")
    print(f"Versions avec innovations: {report['summary']['versions_with_innovations']}")

    return report

def extract_changes(changes_list: List[str]) -> Dict[str, List[str]]:
    """Extrait les changements des listes de changements."""
    changes = {
        'performance_improvements': [],
        'security_fixes': [],
        'new_features': [],
        'graph_algorithms': [],
        'api_changes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    change_keywords = {
        'performance_improvements': ['performance', 'optimization', 'speed', 'fast', 'improved', 'faster'],
        'security_fixes': ['security', 'vulnerability', 'fix', 'patch', 'secure', 'authentication'],
        'new_features': ['feature', 'new', 'added', 'introduced', 'support for'],
        'graph_algorithms': ['graph algorithm', 'algorithm', 'cypher', 'query', 'traversal'],
        'api_changes': ['api', 'driver', 'protocol', 'interface', 'endpoint'],
        'breaking_changes': ['breaking change', 'deprecated', 'removed', 'changed']
    }
    
    for change_text in changes_list:
        change_lower = change_text.lower()
        
        # Catégoriser le changement
        categorized = False
        for category, keywords in change_keywords.items():
            if any(keyword in change_lower for keyword in keywords):
                changes[category].append(change_text)
                categorized = True
                break
        
        # Si non catégorisé, mettre dans other_improvements
        if not categorized:
            changes['other_improvements'].append(change_text)
    
    # Nettoyer les doublons
    for category in changes:
        changes[category] = list(set(changes[category]))
    
    return changes

def analyze_changes(all_changes: Dict) -> Dict:
    """Analyse les changements et génère des insights."""
    analysis = {
        'summary': {},
        'key_changes': {},
        'trends': {}
    }
    
    # Résumé par catégorie
    for category, changes in all_changes.items():
        analysis['summary'][category] = {
            'count': len(changes),
            'items': changes[:5]  # Top 5 par catégorie
        }
    
    # Changements clés
    all_items = []
    for category, changes in all_changes.items():
        for item in changes:
            all_items.append({
                'category': category,
                'content': item
            })
    
    # Trier par pertinence (longueur et mots-clés)
    all_items.sort(key=lambda x: len(x['content']), reverse=True)
    analysis['key_changes'] = all_items[:10]
    
    # Tendances
    analysis['trends'] = {
        'most_active_category': max(all_changes.keys(), key=lambda k: len(all_changes[k])),
        'total_changes': sum(len(changes) for changes in all_changes.values())
    }
    
    return analysis

def generate_change_report() -> Dict:
    """Génère un rapport complet sur les changements Neo4j organisé par version."""
    print("Début de l'analyse des changements Neo4j...")
    
    # Récupérer toutes les versions depuis le changelog
    all_versions = get_neo4j_release_notes()
    
    if not all_versions:
        print("Aucune version trouvée dans le changelog.")
        return {'error': 'Aucune version disponible'}
    
    # Trier les versions par numéro de version (du plus récent au plus ancien)
    all_versions.sort(key=lambda x: [int(n) for n in x['version'].split('.')], reverse=True)
    
    # Prendre TOUTES les versions trouvées (plus de limite)
    latest_versions = all_versions
    
    # Structure organisée par version
    versions_with_changes = []
    all_changes = {
        'performance_improvements': [],
        'security_fixes': [],
        'new_features': [],
        'graph_algorithms': [],
        'api_changes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    for version_info in latest_versions:
        version = version_info['version']
        print(f"\nAnalyse de la version {version}...")
        
        if version_info['changes']:
            # Extraire les changements pour cette version
            changes = extract_changes(version_info['changes'])
            
            # Créer l'entrée pour cette version
            version_entry = {
                'version': version,
                'date': version_info['date'],
                'url': version_info['url'],
                'download_url': version_info['download_url'],
                'changes_count': version_info['changes_count'],
                'changes': changes,
                'total_changes': sum(len(changes[cat]) for cat in changes)
            }
            
            versions_with_changes.append(version_entry)
            
            # Ajouter aux totaux globaux
            for category in all_changes:
                all_changes[category].extend(changes[category])
        else:
            print(f"Aucun changement trouvé pour la version {version}")
            versions_with_changes.append({
                'version': version,
                'date': version_info['date'],
                'url': version_info['url'],
                'download_url': version_info['download_url'],
                'changes_count': 0,
                'changes': {cat: [] for cat in all_changes.keys()},
                'total_changes': 0
            })
    
    # Nettoyer les doublons dans les totaux globaux
    for category in all_changes:
        all_changes[category] = list(set(all_changes[category]))
    
    # Analyser les changements globaux
    analysis = analyze_changes(all_changes)
    
    # Créer le rapport final avec la nouvelle structure
    report = {
        'report_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'summary': {
            'total_versions_analyzed': len(versions_with_changes),
            'total_changes': sum(v['total_changes'] for v in versions_with_changes),
            'versions_with_changes': len([v for v in versions_with_changes if v['total_changes'] > 0])
        },
        'versions': versions_with_changes,
        'global_analysis': {
            'changes_by_category': all_changes,
            'analysis': analysis
        }
    }

    # Sauvegarder le rapport
    output_file = 'neo4j_changes_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\nRapport de changements sauvegardé dans {output_file}")
    print(f"Versions analysées: {len(versions_with_changes)}")
    print(f"Total de changements trouvés: {report['summary']['total_changes']}")
    print(f"Versions avec changements: {report['summary']['versions_with_changes']}")

    return report

def main():
    """Fonction principale pour exécuter l'analyse des changements."""
    print("=== Analyse des Changements Neo4j ===")

    # Générer le rapport de changements
    report = generate_change_report()

    if 'error' in report:
        print(f"Erreur: {report['error']}")
        return

    # Afficher un résumé par version
    print("\n=== Résumé des Changements par Version ===")
    for version_info in report['versions']:
        print(f"\nVersion {version_info['version']} ({version_info['date']}):")
        print(f"  Total de changements: {version_info['total_changes']}")
        
        for category, changes in version_info['changes'].items():
            if changes:
                print(f"  {category.replace('_', ' ').title()}: {len(changes)} items")
                for item in changes[:2]:  # Top 2 par catégorie
                    print(f"    - {item[:80]}...")

    # Afficher les tendances globales
    print(f"\n=== Tendances Globales ===")
    global_analysis = report['global_analysis']['analysis']
    
    print(f"Total de versions analysées: {report['summary']['total_versions_analyzed']}")
    print(f"Versions avec changements: {report['summary']['versions_with_changes']}")
    print(f"Total de changements: {report['summary']['total_changes']}")
    print(f"Catégorie la plus active: {global_analysis['trends']['most_active_category'].replace('_', ' ').title()}")

    print(f"\n=== Top 5 Changements Clés ===")
    for i, change in enumerate(global_analysis['key_changes'][:5], 1):
        print(f"{i}. [{change['category'].replace('_', ' ').title()}] {change['content'][:100]}...")

if __name__ == "__main__":
    main()