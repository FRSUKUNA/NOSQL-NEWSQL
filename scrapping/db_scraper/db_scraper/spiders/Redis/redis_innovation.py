import requests
from bs4 import BeautifulSoup
import json
import re
import os
import sys
import time
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Configuration pour gérer l'encodage dans la console Windows
if sys.platform.startswith('win'):
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_all_releases(max_pages: int = 8) -> List[Dict]:
    """Récupère les versions de Redis depuis GitHub (limité à 8 pages par défaut)"""
    print(f"🔍 Récupération des versions (max {max_pages} pages)...")
    
    all_releases = []
    page = 1
    session = requests.Session()
    session.headers.update(headers)
    
    while page <= max_pages:
        url = f"https://github.com/redis/redis/releases?page={page}"
        print(f"📄 Page {page}/{max_pages}...", end=' ', flush=True)
        
        try:
            # Timeout court et pas de vérification SSL pour plus de rapidité
            response = session.get(url, timeout=10, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            # Essayer différents sélecteurs pour trouver les éléments de version
            release_elements = (
                soup.select('div.Box--condensed') or  # Ancien sélecteur
                soup.select('div.Box.Box--condensed') or  # Nouveau format
                soup.select('div.Box')  # Format plus large
            )
            
            if not release_elements:
                print("Aucune version trouvée sur cette page, fin du parcours.")
                break
                
            for element in release_elements:
                try:
                    # Extraire le numéro de version - essayer plusieurs sélecteurs
                    version_tag = (
                        element.select_one('a.Link--primary') or
                        element.select_one('a[href*="/releases/tag/"]') or
                        element.select_one('h2 a') or
                        element.select_one('a[href^="/redis/redis/releases/tag/"]')
                    )
                    if not version_tag:
                        continue
                        
                    version_text = version_tag.text.strip().replace('v', '')
                    
                    # Nettoyer et valider le numéro de version
                    version_text = re.sub(r'[^0-9.]', '', version_text)  # Ne garder que les chiffres et points
                    version_parts = version_text.split('.')
                    
                    # S'assurer qu'on a au moins 2 parties numériques (ex: 7.0, 6.2, etc.)
                    if len(version_parts) < 2:
                        continue
                        
                    # Vérifier que les deux premières parties sont des nombres
                    if not (version_parts[0].isdigit() and version_parts[1].isdigit()):
                        continue
                        
                    # Extraire la date
                    date_tag = element.select_one('relative-time')
                    if not date_tag:
                        formatted_date = "Date non disponible"
                    else:
                        date_str = date_tag['datetime']
                        date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    # Préparer les données de la version
                    version_data = {
                        'version': version_parts[0],
                        'patch': '.'.join(version_parts[1:]) if len(version_parts) > 1 else '0',
                        'date': formatted_date,
                        'url': f"https://github.com/redis/redis/releases/tag/v{version_text}",
                        'download_url': f"https://download.redis.io/releases/redis-{version_text}.tar.gz"
                    }
                    
                    all_releases.append(version_data)
                    print(f"Version trouvée: {version_text} - {formatted_date}")
                    
                except Exception as e:
                    print(f"Erreur lors du traitement d'une version: {str(e)}")
                    continue
            
            # Vérifier s'il y a une page suivante (essayer plusieurs sélecteurs)
            next_buttons = [
                soup.select_one('a.next_page'),
                soup.select_one('a[rel="next"]'),
                soup.select_one('a[data-ga-click^="Next"]')
            ]
            next_page = next((btn for btn in next_buttons if btn), None)
            
            # Vérifier si le bouton est désactivé ou absent
            if not next_page or 'disabled' in next_page.get('class', []) or 'disabled' in next_page.get('aria-disabled', ''):
                print("Dernière page atteinte.")
                break
                
            page += 1
            time.sleep(0.2)  # Temps d'attente minimal entre les requêtes
            
        except requests.RequestException as e:
            print(f"\n⚠️ Erreur lors de la récupération de la page {page}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                if e.response.status_code == 429:  # Too Many Requests
                    retry_after = int(e.response.headers.get('Retry-After', 5))
                    print(f"⚠️ Trop de requêtes. Attente de {retry_after} secondes...")
                    time.sleep(retry_after)
                    continue
            break
        except Exception as e:
            print(f"\n❌ Erreur inattendue: {str(e)}")
            break
            
        page += 1  # Passer à la page suivante
    
    return all_releases

def load_redis_versions(use_github: bool = True) -> List[Dict]:
    """Charge les versions de Redis depuis GitHub ou depuis le fichier local"""
    if use_github:
        return get_all_releases()
    else:
        try:
            with open('redis_versions.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('versions', [])
        except FileNotFoundError:
            print("⚠️ Fichier redis_versions.json non trouvé. Utilisation de GitHub...")
            return get_all_releases()
        except Exception as e:
            print(f"Erreur lors du chargement des versions: {str(e)}")
            return []

def get_release_notes(version: Dict) -> List[Dict]:
    """Récupère les notes de version pour une version spécifique de Redis depuis GitHub."""
    try:
        # Gérer le format de version (certaines versions ont un format spécial)
        version_str = f"{version['version']}.{version['patch']}" if version['patch'] != '0' else version['version']
        
        # Essayer différents formats de tags
        tag_variants = [
            f"{version['version']}.{version['patch']}",  # Format standard (ex: 7.0.0)
            f"{version['version']}-{version['patch']}",  # Format alternatif (ex: 7-0-0)
            f"{version_str}",                            # Format d'origine
            f"v{version_str}",                           # Avec préfixe 'v'
            f"redis-{version_str}"                       # Avec préfixe 'redis-'
        ]
        
        # Ajouter une variante sans le dernier numéro de version si nécessaire
        if version['patch'] != '0' and '.' in version['patch']:
            major, minor = version['patch'].split('.', 1)
            tag_variants.append(f"{version['version']}.{major}")
        
        # Essayer chaque variante jusqu'à ce qu'une fonctionne
        last_error = None
        for tag in tag_variants:
            release_url = f"https://github.com/redis/redis/releases/tag/{tag}"
            try:
                response = requests.head(release_url, headers=headers, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    break  # URL valide trouvée
            except:
                continue
        else:
            # Si aucune variante n'a fonctionné, utiliser la première
            tag = tag_variants[0]
            release_url = f"https://github.com/redis/redis/releases/tag/{tag}"
        print(f"Récupération des notes pour Redis {version_str}...")
        
        try:
            response = requests.get(release_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Vérifier si la page contient une erreur 404
            if "This is not the web page you are looking for" in response.text:
                print(f"  ⚠️  La page de version {version_str} semble être une redirection ou n'existe pas")
                return []
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Vérifier si la page contient un message d'erreur
            if soup.find('div', class_='markdown-body') is None and \
               soup.find('div', class_='release-body') is None:
                print(f"  ⚠️  Aucun contenu trouvé pour la version {version_str}")
                return []
                
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                print(f"  ❌ Version {version_str} non trouvée (404) - URL: {release_url}")
            else:
                print(f"  ❌ Erreur HTTP {e.response.status_code} pour la version {version_str}: {str(e)}")
            return []
        except requests.RequestException as e:
            print(f"  ❌ Erreur de requête pour la version {version_str}: {str(e)}")
            return []
        
        # Récupérer le contenu principal de la page de release
        content = soup.find('div', class_='markdown-body') or soup.find('div', class_='release-body')
        if not content:
            print(f"Contenu non trouvé pour la version {version_str}")
            return []
        
        sections = []
        current_section = {'title': 'Release Notes', 'content': [], 'type': 'general'}
        
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'li', 'pre', 'div']):
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                # Sauvegarder la section précédente
                if current_section['content']:
                    sections.append(current_section)
                
                # Détecter le type de section
                title = element.get_text(strip=True)
                section_type = detect_section_type(title)
                
                # Commencer une nouvelle section
                current_section = {
                    'title': title,
                    'content': [],
                    'type': section_type
                }
            else:
                # Ajouter le contenu à la section courante
                text = element.get_text('\n', strip=True)
                if text and len(text) > 10:  # Ignorer les textes trop courts
                    current_section['content'].append(text)
        
        # Ajouter la dernière section
        if current_section['content']:
            sections.append(current_section)
            
        return sections
        
    except requests.RequestException as e:
        print(f"Erreur lors de la récupération des notes pour la version {version_str}: {str(e)}")
        return []
    except Exception as e:
        print(f"Erreur inattendue pour la version {version_str}: {str(e)}")
        return []

def detect_section_type(title: str) -> str:
    """Détecte le type de section en fonction de son titre."""
    title_lower = title.lower()
    
    # Catégories d'innovations
    if any(x in title_lower for x in ['feature', 'new', 'amélioration', 'améliorations', 'amélioré', 'améliorée']):
        return 'new_features'
    elif any(x in title_lower for x in ['fix', 'bug', 'correction', 'correctif', 'résolution']):
        return 'bug_fixes'
    elif any(x in title_lower for x in ['performance', 'optimisation', 'rapidité', 'vitesse']):
        return 'performance'
    elif any(x in title_lower for x in ['security', 'sécurité', 'vulnérabilité']):
        return 'security'
    elif any(x in title_lower for x in ['breaking change', 'changement majeur', 'incompatibilité']):
        return 'breaking_changes'
    elif any(x in title_lower for x in ['deprecation', 'obsolescence', 'suppression']):
        return 'deprecations'
    else:
        return 'general'

def extract_innovations(sections: List[Dict]) -> Dict[str, List[Dict]]:
    """Extrait les innovations des sections de notes de version."""
    innovations = {
        'new_features': [],
        'bug_fixes': [],
        'performance': [],
        'security': [],
        'breaking_changes': [],
        'deprecations': [],
        'other': []
    }
    
    for section in sections:
        section_type = section.get('type', 'other')
        content = '\n'.join(section['content'])
        
        if section_type in innovations:
            innovations[section_type].append({
                'title': section['title'],
                'content': content
            })
        else:
            innovations['other'].append({
                'title': section['title'],
                'content': content
            })
    
    return innovations

def analyze_innovations(version_innovations: Dict[str, Dict]) -> Dict:
    """Analyse les innovations par version et génère des statistiques."""
    stats = {
        'total_versions': len(version_innovations),
        'total_innovations': 0,
        'by_category': {
            'new_features': 0,
            'bug_fixes': 0,
            'performance': 0,
            'security': 0,
            'breaking_changes': 0,
            'deprecations': 0,
            'other': 0
        },
        'versions': {}
    }
    
    for version, innovations in version_innovations.items():
        version_stats = {
            'total': 0,
            'by_category': {}
        }
        
        for category, items in innovations.items():
            count = len(items)
            version_stats['by_category'][category] = count
            version_stats['total'] += count
            stats['by_category'][category] += count
            stats['total_innovations'] += count
            
        stats['versions'][version] = version_stats
    
    return stats

def generate_innovation_report() -> Dict:
    """Génère un rapport complet sur les innovations de Redis par version."""
    print("🚀 Début de l'analyse des innovations de Redis...")
    
    # Charger les versions de Redis depuis GitHub (limité à 5 pages)
    versions = load_redis_versions(use_github=True)
    
    # Limiter le nombre de versions à analyser pour plus de rapidité
    max_versions = 15  # Augmenté à 15 pour couvrir plus de versions
    if len(versions) > max_versions:
        print(f"🚀 Limitation à {max_versions} versions pour l'analyse")
        versions = versions[:max_versions]
    if not versions:
        return {'error': 'Aucune version trouvée'}
    
    print(f"\n✅ {len(versions)} versions trouvées sur GitHub")
    
    # Trier les versions par numéro de version (du plus récent au plus ancien)
    def version_key(v):
        try:
            # Gérer les versions avec plusieurs parties (ex: 7.0.0, 6.2.14, etc.)
            version_parts = []
            # Ajouter la version majeure
            version_parts.append(int(v['version']))
            
            # Ajouter les parties du patch (ex: '2.14' -> [2, 14])
            if v['patch'] != '0':
                for part in v['patch'].split('.'):
                    version_parts.append(int(part) if part.isdigit() else 0)
            
            # Remplir avec des zéros pour assurer une comparaison correcte
            while len(version_parts) < 3:  # Au moins 3 parties pour la comparaison
                version_parts.append(0)
                
            return tuple(version_parts)
            
        except (ValueError, IndexError, AttributeError) as e:
            print(f"  ⚠️  Erreur de tri pour la version {v.get('version', '?')}.{v.get('patch', '?')}: {str(e)}")
            return (0, 0, 0)
    
    # Trier les versions (du plus récent au plus ancien)
    versions.sort(key=version_key, reverse=True)
    
    # Afficher les 10 premières versions pour vérification
    print("\n🔍 10 premières versions trouvées (du plus récent au plus ancien):")
    for v in versions[:10]:
        version_str = f"{v['version']}.{v['patch']}" if v['patch'] != '0' else v['version']
        print(f"  - Redis {version_str} ({v.get('date', 'date inconnue')})")
    
    # Limiter le nombre de versions à analyser pour les tests
    max_versions = 10  # À augmenter pour une analyse complète
    if len(versions) > max_versions:
        print(f"\n⚠️  Limitation à {max_versions} versions pour les tests (sur {len(versions)} au total)")
        versions = versions[:max_versions]
    
    all_innovations = {}
    
    try:
        # Récupérer les notes de version pour chaque version
        for version in versions:
            version_str = f"{version['version']}.{version['patch']}" if version['patch'] != '0' else version['version']
            print(f"\nTraitement de la version {version_str}...")
            
            # Récupérer les sections des notes de version
            sections = get_release_notes(version)
            if not sections:
                print(f"Aucune section trouvée pour la version {version_str}")
                continue
            
            # Extraire les innovations
            innovations = extract_innovations(sections)
            all_innovations[version_str] = innovations
            
            # Respecter les limites de taux de GitHub
            time.sleep(2)  # Augmenter le délai pour éviter d'être bloqué
        
        # Analyser les innovations
        analysis = analyze_innovations(all_innovations)
        
        # Créer le rapport final
        report = {
            'report_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'versions_analyzed': list(all_innovations.keys()),
            'analysis': analysis,
            'details': all_innovations
        }
        
        # Sauvegarder le rapport
        output_file = 'redis_github_innovations_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        
        print(f"\n✅ Rapport d'analyse des innovations sauvegardé dans {output_file}")
        return report
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération du rapport: {str(e)}"
        print(error_msg)
        return {'error': error_msg}

def generate_markdown_report(report: Dict):
    """Génère un rapport au format Markdown à partir du rapport JSON."""
    if 'error' in report:
        return f"# Erreur\n\n{report['error']}"
    
    markdown = ["# Rapport d'Innovations Redis\n"]
    
    # Résumé
    markdown.append("## Résumé\n")
    markdown.append(f"- **Versions analysées**: {len(report['analysis']['versions'])}")
    markdown.append(f"- **Total d'innovations**: {report['analysis']['total_innovations']}")
    markdown.append("\n### Par catégorie:")
    
    for category, count in report['analysis']['by_category'].items():
        if count > 0:
            markdown.append(f"- **{category.replace('_', ' ').title()}**: {count}")
    
    # Détails par version
    markdown.append("\n## Détails par version\n")
    
    for version, innovations in report['details'].items():
        markdown.append(f"### Redis {version}")
        
        for category, items in innovations.items():
            if items:
                markdown.append(f"\n#### {category.replace('_', ' ').title()} ({len(items)})\n")
                
                for item in items:
                    markdown.append(f"- **{item['title']}**")
                    # Limiter la longueur du contenu pour le rapport
                    content = item['content'][:200] + ('...' if len(item['content']) > 200 else '')
                    markdown.append(f"  > {content}")
        
        markdown.append("\n---\n")
    
    # Enregistrer le rapport Markdown
    output_file = 'redis_github_innovations_report.md'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(markdown))
    
    return output_file

def main():
    """Fonction principale pour exécuter l'analyse des innovations."""
    start_time = time.time()
    print("⚡ Analyse des innovations Redis (8 pages max)\n")
    
    # Désactiver les avertissements SSL
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Générer le rapport d'innovation
    report = generate_innovation_report()
    
    if 'error' in report:
        print(f"\n❌ Erreur: {report['error']}")
    else:
        # Afficher un résumé
        print("\n📊 RÉSULTATS")
        print(f"• Versions analysées: {len(report['analysis']['versions'])}")
        print(f"• Total d'innovations: {report['analysis']['total_innovations']}")
        
        print("\n📈 Répartition par catégorie:")
        for category, count in report['analysis']['by_category'].items():
            if count > 0:
                percentage = (count / report['analysis']['total_innovations']) * 100
                print(f"   • {category.replace('_', ' ').title()}: {count} ({percentage:.1f}%)")
        
        # Afficher les versions avec le plus d'innovations
        top_versions = sorted(
            [(v, data['total']) for v, data in report['analysis']['versions'].items() if data['total'] > 0],
            key=lambda x: x[1],
            reverse=True
        )[:5]  # Top 5 au lieu de 3
        
        if top_versions:
            print("\n🏆 Top 5 des versions avec le plus d'innovations:")
            for i, (version, count) in enumerate(top_versions, 1):
                print(f"   {i}. Redis {version}: {count} innovations")
        
        # Calculer et afficher le temps d'exécution
        exec_time = time.time() - start_time
        print(f"\n✅ Analyse terminée en {exec_time:.1f} secondes")
        print(f"📄 Rapport sauvegardé: redis_github_innovations_report.json")

if __name__ == "__main__":
    main()