import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
import re
import time

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_cockroachdb_release_notes(version: str) -> List[Dict]:
    """Récupère les notes de version pour une version spécifique de CockroachDB."""
    try:
        # URL des release notes CockroachDB
        url = f"https://www.cockroachlabs.com/docs/releases/v{version}"
        print(f"Récupération des notes de version pour CockroachDB v{version}...")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Récupérer le contenu principal
        content = soup.find('article') or soup.find('main') or soup.find('div', class_='markdown-body')
        if not content:
            print(f"Contenu principal non trouvé pour la version {version}")
            return []
        
        sections = []
        current_section = {'title': 'Introduction', 'content': [], 'type': 'general'}
        
        # Parser le contenu
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'li', 'div']):
            element_text = element.get_text(strip=True)
            
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                # Sauvegarder la section précédente si elle contient du contenu
                if current_section['content']:
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
            elif element_text and len(element_text) > 15:
                # Ajouter le contenu à la section courante
                current_section['content'].append(element_text)
        
        # Ajouter la dernière section si elle contient du contenu
        if current_section['content']:
            sections.append(current_section)
        
        # Si peu de sections, chercher dans les listes
        if len(sections) < 3:
            print(f"Recherche alternative pour v{version}...")
            lists = content.find_all(['ul', 'ol'])
            
            for list_element in lists:
                items = list_element.find_all('li')
                list_content = [item.get_text(strip=True) for item in items if len(item.get_text(strip=True)) > 15]
                
                if list_content:
                    sections.append({
                        'title': 'Release Notes',
                        'content': list_content,
                        'type': 'general',
                        'version': version
                    })
        
        print(f"Sections trouvées pour v{version}: {len(sections)}")
        return sections
        
    except Exception as e:
        print(f"Erreur lors de la récupération des notes de version v{version}: {e}")
        return []

def detect_section_type(title: str) -> str:
    """Détecte le type de section en fonction du titre."""
    title_lower = title.lower()
    
    # Catégories spécifiques à CockroachDB
    if any(keyword in title_lower for keyword in ['performance', 'optimization', 'speed', 'latency', 'throughput']):
        return 'performance'
    elif any(keyword in title_lower for keyword in ['security', 'vulnerability', 'authentication', 'authorization', 'encryption']):
        return 'security'
    elif any(keyword in title_lower for keyword in ['feature', 'new', 'added', 'introduced', 'enhancement']):
        return 'feature'
    elif any(keyword in title_lower for keyword in ['sql', 'query', 'statement', 'syntax']):
        return 'sql_features'
    elif any(keyword in title_lower for keyword in ['distributed', 'replication', 'cluster', 'node', 'geo']):
        return 'distribution'
    elif any(keyword in title_lower for keyword in ['availability', 'failover', 'recovery', 'backup', 'restore']):
        return 'high_availability'
    elif any(keyword in title_lower for keyword in ['bug', 'fix', 'fixed', 'issue', 'problem']):
        return 'bug_fixes'
    elif any(keyword in title_lower for keyword in ['breaking', 'deprecated', 'removed', 'changed']):
        return 'breaking_changes'
    else:
        return 'general'

def extract_innovations(sections: List[Dict]) -> Dict[str, List[str]]:
    """Extrait les innovations des sections de notes de version."""
    innovations = {
        'performance_improvements': [],
        'security_enhancements': [],
        'new_sql_features': [],
        'distribution_improvements': [],
        'high_availability_features': [],
        'bug_fixes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    innovation_keywords = {
        'performance_improvements': ['performance', 'optimization', 'faster', 'speed', 'latency', 'throughput', 'improved'],
        'security_enhancements': ['security', 'authentication', 'authorization', 'encryption', 'rbac', 'ssl', 'tls'],
        'new_sql_features': ['sql', 'query', 'statement', 'function', 'operator', 'syntax', 'command'],
        'distribution_improvements': ['distributed', 'replication', 'cluster', 'geo', 'region', 'zone', 'partition'],
        'high_availability_features': ['availability', 'failover', 'recovery', 'backup', 'restore', 'resilience'],
        'bug_fixes': ['bug', 'fix', 'fixed', 'issue', 'resolved', 'corrected'],
        'breaking_changes': ['breaking', 'deprecated', 'removed', 'incompatible', 'changed']
    }
    
    # Mapper les types de section aux catégories d'innovation
    type_to_category = {
        'performance': 'performance_improvements',
        'security': 'security_enhancements',
        'sql_features': 'new_sql_features',
        'distribution': 'distribution_improvements',
        'high_availability': 'high_availability_features',
        'bug_fixes': 'bug_fixes',
        'breaking_changes': 'breaking_changes',
        'feature': 'new_sql_features'
    }
    
    for section in sections:
        section_text = ' '.join(section['content'])
        section_type = section['type']
        
        # Ajouter le contenu à la catégorie appropriée basée sur le type
        if section_type in type_to_category:
            category = type_to_category[section_type]
            innovations[category].extend([
                f"{section['title']}: {content[:200]}"
                for content in section['content']
                if len(content) > 25
            ])
        
        # Recherche supplémentaire par mots-clés pour affiner
        for category, keywords in innovation_keywords.items():
            if any(keyword in section_text.lower() for keyword in keywords):
                relevant_content = [
                    f"{section['title']}: {content[:200]}"
                    for content in section['content']
                    if len(content) > 25 and any(keyword in content.lower() for keyword in keywords)
                ]
                innovations[category].extend(relevant_content)
    
    # Nettoyer les doublons tout en préservant l'ordre
    for category in innovations:
        seen = set()
        unique_items = []
        for item in innovations[category]:
            # Créer une clé unique basée sur les 100 premiers caractères
            key = item[:100]
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        innovations[category] = unique_items
    
    return innovations

def analyze_innovations(all_innovations: Dict) -> Dict:
    """Analyse les innovations et génère des insights."""
    analysis = {
        'summary': {},
        'key_innovations': [],
        'trends': {}
    }
    
    # Résumé par catégorie
    for category, innovations in all_innovations.items():
        analysis['summary'][category] = {
            'count': len(innovations),
            'items': innovations[:5]  # Top 5 par catégorie
        }
    
    # Innovations clés (toutes catégories confondues)
    all_items = []
    for category, innovations in all_innovations.items():
        for item in innovations:
            all_items.append({
                'category': category,
                'content': item
            })
    
    # Trier par longueur (considérer les plus détaillées comme plus importantes)
    all_items.sort(key=lambda x: len(x['content']), reverse=True)
    analysis['key_innovations'] = all_items[:15]
    
    # Tendances
    if all_innovations:
        most_active = max(all_innovations.keys(), key=lambda k: len(all_innovations[k]))
        analysis['trends'] = {
            'most_active_category': most_active,
            'total_innovations': sum(len(innovations) for innovations in all_innovations.values()),
            'categories_with_innovations': len([cat for cat, items in all_innovations.items() if items])
        }
    
    return analysis

def generate_innovation_report() -> Dict:
    """Génère un rapport complet sur les innovations CockroachDB organisé par version."""
    print("="*70)
    print("Début de l'analyse des innovations CockroachDB...")
    print("="*70)
    
    # Charger les versions depuis le fichier JSON
    try:
        with open('cockroachdb_versions.json', 'r', encoding='utf-8') as f:
            versions_data = json.load(f)
            versions = versions_data.get('versions', [])
    except FileNotFoundError:
        print("❌ Erreur: Fichier cockroachdb_versions.json non trouvé.")
        print("📋 Exécutez d'abord CockroachDB_versions.py")
        return {'error': 'Fichier cockroachdb_versions.json non trouvé'}
    
    if not versions:
        print("Aucune version trouvée dans le fichier JSON.")
        return {'error': 'Aucune version disponible'}
    
    # Analyser les 6 dernières versions
    latest_versions = versions[:6]
    
    # Structure organisée par version
    versions_with_innovations = []
    all_innovations = {
        'performance_improvements': [],
        'security_enhancements': [],
        'new_sql_features': [],
        'distribution_improvements': [],
        'high_availability_features': [],
        'bug_fixes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    for version_info in latest_versions:
        version = version_info.get('full_version', f"{version_info['version']}.{version_info['patch']}")
        print(f"\n{'─'*70}")
        print(f"📦 Analyse de la version v{version}...")
        print(f"{'─'*70}")
        
        # Récupérer les notes de version
        sections = get_cockroachdb_release_notes(version)
        
        time.sleep(2)  # Respecter le serveur
        
        if sections:
            # Extraire les innovations pour cette version
            innovations = extract_innovations(sections)
            
            # Créer l'entrée pour cette version
            version_entry = {
                'version': version,
                'date': version_info.get('date', 'Date non disponible'),
                'release_type': version_info.get('release_type', 'N/A'),
                'url': version_info.get('url', ''),
                'sections_count': len(sections),
                'innovations': innovations,
                'total_innovations': sum(len(innovations[cat]) for cat in innovations)
            }
            
            versions_with_innovations.append(version_entry)
            
            # Ajouter aux totaux globaux
            for category in all_innovations:
                all_innovations[category].extend(innovations[category])
            
            print(f"✅ {version_entry['total_innovations']} innovations trouvées")
        else:
            print(f"⚠️  Aucune section trouvée pour la version v{version}")
            versions_with_innovations.append({
                'version': version,
                'date': version_info.get('date', 'Date non disponible'),
                'release_type': version_info.get('release_type', 'N/A'),
                'url': version_info.get('url', ''),
                'sections_count': 0,
                'innovations': {cat: [] for cat in all_innovations.keys()},
                'total_innovations': 0
            })
    
    # Nettoyer les doublons dans les totaux globaux
    for category in all_innovations:
        seen = set()
        unique_items = []
        for item in all_innovations[category]:
            key = item[:100]
            if key not in seen:
                seen.add(key)
                unique_items.append(item)
        all_innovations[category] = unique_items
    
    # Analyser les innovations globales
    analysis = analyze_innovations(all_innovations)
    
    # Créer le rapport final
    report = {
        'database': 'CockroachDB',
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
    output_file = 'cockroachdb_innovations_report.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

    print(f"\n{'='*70}")
    print(f"✅ Rapport d'innovations sauvegardé dans {output_file}")
    print(f"{'='*70}")
    print(f"📊 Statistiques:")
    print(f"  • Versions analysées: {len(versions_with_innovations)}")
    print(f"  • Total d'innovations: {report['summary']['total_innovations']}")
    print(f"  • Versions avec innovations: {report['summary']['versions_with_innovations']}")

    return report

def main():
    """Fonction principale pour exécuter l'analyse des innovations."""
    print("\n" + "="*70)
    print("🚀 ANALYSE DES INNOVATIONS COCKROACHDB")
    print("="*70 + "\n")

    # Générer le rapport d'innovations
    report = generate_innovation_report()

    if 'error' in report:
        print(f"\n❌ Erreur: {report['error']}")
        return

    # Afficher un résumé par version
    print("\n" + "="*70)
    print("📋 RÉSUMÉ DES INNOVATIONS PAR VERSION")
    print("="*70)
    
    for version_info in report['versions']:
        release_badge = "🟢" if version_info.get('release_type') == 'Regular' else "🔵"
        print(f"\n{release_badge} Version v{version_info['version']} ({version_info.get('release_type', 'N/A')}) - {version_info['date']}")
        print(f"   Total: {version_info['total_innovations']} innovations")
        
        for category, innovations in version_info['innovations'].items():
            if innovations:
                category_display = category.replace('_', ' ').title()
                print(f"   • {category_display}: {len(innovations)} items")
                
                # Afficher les 2 premiers items
                for item in innovations[:2]:
                    # Tronquer pour l'affichage
                    display_item = item[:90] + "..." if len(item) > 90 else item
                    print(f"     - {display_item}")

    # Afficher les tendances globales
    print(f"\n{'='*70}")
    print("📈 TENDANCES GLOBALES")
    print(f"{'='*70}")
    
    global_analysis = report['global_analysis']['analysis']
    
    print(f"Total de versions analysées: {report['summary']['total_versions_analyzed']}")
    print(f"Versions avec innovations: {report['summary']['versions_with_innovations']}")
    print(f"Total d'innovations: {report['summary']['total_innovations']}")
    
    most_active = global_analysis['trends']['most_active_category'].replace('_', ' ').title()
    print(f"Catégorie la plus active: {most_active}")

    print(f"\n{'='*70}")
    print("⭐ TOP 5 INNOVATIONS CLÉS")
    print(f"{'='*70}")
    
    for i, innovation in enumerate(global_analysis['key_innovations'][:5], 1):
        category = innovation['category'].replace('_', ' ').title()
        content = innovation['content'][:120] + "..." if len(innovation['content']) > 120 else innovation['content']
        print(f"\n{i}. [{category}]")
        print(f"   {content}")

    print(f"\n{'='*70}")
    print("✅ Analyse terminée avec succès!")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
