import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_neo4j_release_notes(version: str) -> List[Dict]:
    """Récupère les notes de version pour une version spécifique de Neo4j depuis GitHub."""
    try:
        # URL du changelog GitHub Neo4j
        url = "https://github.com/neo4j/neo4j/wiki/Neo4j-2025-changelog/"
        print(f"Récupération des notes de version pour Neo4j {version}...")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Récupérer le contenu principal de la page wiki GitHub
        content = soup.find('div', class_='markdown-body') or soup.find('article') or soup.find('main')
        if not content:
            print(f"Contenu principal non trouvé pour la version {version}")
            return []
        
        sections = []
        current_section = {'title': 'Introduction', 'content': [], 'type': 'general'}
        
        # Chercher spécifiquement les sections pour la version demandée
        version_found = False
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'div']):
            element_text = element.get_text(strip=True)
            
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                # Vérifier si cette section concerne notre version
                if version.replace('.', '') in element_text or any(part in element_text for part in version.split('.')):
                    version_found = True
                    print(f"Section trouvée pour la version {version}: {element_text}")
                
                # Sauvegarder la section précédente si elle contient du contenu
                if current_section['content'] and version_found:
                    sections.append(current_section)
                
                # Commencer une nouvelle section
                title = element_text
                section_type = detect_section_type(title)
                current_section = {
                    'title': title,
                    'content': [],
                    'type': section_type,
                    'version': version
                }
            elif version_found:
                # Ajouter le contenu à la section courante
                if element_text and len(element_text) > 10:
                    current_section['content'].append(element_text)
                
                # Traiter les listes spécialement
                if element.name in ['ul', 'ol']:
                    for li in element.find_all('li'):
                        li_text = li.get_text(strip=True)
                        if li_text and len(li_text) > 10:
                            current_section['content'].append(li_text)
        
        # Ajouter la dernière section si elle contient du contenu
        if current_section['content'] and version_found:
            sections.append(current_section)
        
        # Si aucune section spécifique trouvée, essayer une approche plus large
        if not sections:
            print(f"Recherche alternative pour la version {version}...")
            all_text = content.get_text()
            
            # Chercher des mentions de la version dans tout le texte
            version_mentions = []
            lines = all_text.split('\n')
            for i, line in enumerate(lines):
                if version.replace('.', '') in line or any(part in line for part in version.split('.')):
                    # Ajouter cette ligne et les quelques lignes suivantes
                    context_lines = []
                    for j in range(max(0, i-2), min(len(lines), i+5)):
                        context_line = lines[j].strip()
                        if context_line and len(context_line) > 10:
                            context_lines.append(context_line)
                    
                    if context_lines:
                        version_found = True
                        sections.append({
                            'title': f'Version {version} - Ligne {i+1}',
                            'content': context_lines,
                            'type': 'general',
                            'version': version
                        })
                        print(f"Contexte trouvé pour la version {version} (ligne {i+1})")
        
        print(f"Sections trouvées pour {version}: {len(sections)}")
        return sections
        
    except Exception as e:
        print(f"Erreur lors de la récupération des notes de version {version}: {e}")
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

def main():
    """Fonction principale pour exécuter l'analyse des innovations."""
    print("=== Analyse des Innovations Neo4j ===")

    # Générer le rapport d'innovations
    report = generate_innovation_report()

    if 'error' in report:
        print(f"Erreur: {report['error']}")
        return

    # Afficher un résumé par version
    print("\n=== Résumé des Innovations par Version ===")
    for version_info in report['versions']:
        print(f"\nVersion {version_info['version']} ({version_info['date']}):")
        print(f"  Total d'innovations: {version_info['total_innovations']}")
        
        for category, innovations in version_info['innovations'].items():
            if innovations:
                print(f"  {category.replace('_', ' ').title()}: {len(innovations)} items")
                for item in innovations[:2]:  # Top 2 par catégorie
                    print(f"    - {item[:80]}...")

    # Afficher les tendances globales
    print(f"\n=== Tendances Globales ===")
    global_analysis = report['global_analysis']['analysis']
    
    print(f"Total de versions analysées: {report['summary']['total_versions_analyzed']}")
    print(f"Versions avec innovations: {report['summary']['versions_with_innovations']}")
    print(f"Total d'innovations: {report['summary']['total_innovations']}")
    print(f"Catégorie la plus active: {global_analysis['trends']['most_active_category'].replace('_', ' ').title()}")

    print(f"\n=== Top 5 Innovations Clés ===")
    for i, innovation in enumerate(global_analysis['key_innovations'][:5], 1):
        print(f"{i}. [{innovation['category'].replace('_', ' ').title()}] {innovation['content'][:100]}...")

if __name__ == "__main__":
    main()