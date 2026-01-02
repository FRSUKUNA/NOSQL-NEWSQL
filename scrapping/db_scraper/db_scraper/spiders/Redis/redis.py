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


def _extract_releases_from_soup(soup: BeautifulSoup) -> List[Dict]:
    releases = []
    seen_versions = set()

    # GitHub change souvent la structure; le plus stable est de partir des liens /releases/tag/
    release_links = soup.select('a[href*="/redis/redis/releases/tag/"]') or soup.select('a[href*="/releases/tag/"]')
    for a in release_links:
        href = a.get('href', '').strip()
        text = a.get_text(strip=True)

        tag_candidate = text or (href.split('/')[-1] if href else '')
        m = re.search(r'v?(\d+\.\d+(?:\.\d+)*)', tag_candidate)
        if not m:
            continue

        version_text = m.group(1)
        if version_text in seen_versions:
            continue
        seen_versions.add(version_text)

        version_parts = version_text.split('.')
        if len(version_parts) < 2:
            continue
        if not (version_parts[0].isdigit() and version_parts[1].isdigit()):
            continue

        # La date est généralement dans le même bloc visuel; on prend le premier relative-time trouvé en parent
        date_tag = None
        parent = a
        for _ in range(0, 6):
            if parent is None:
                break
            date_tag = parent.select_one('relative-time')
            if date_tag:
                break
            parent = parent.parent

        if not date_tag or not date_tag.get('datetime'):
            formatted_date = "Date non disponible"
        else:
            date_str = date_tag['datetime']
            date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            formatted_date = date_obj.strftime('%Y-%m-%d')

        releases.append({
            'version': version_parts[0],
            'patch': '.'.join(version_parts[1:]) if len(version_parts) > 1 else '0',
            'date': formatted_date,
            'url': f"https://github.com{href}" if href.startswith('/') else f"https://github.com/redis/redis/releases/tag/v{version_text}",
            'download_url': f"https://download.redis.io/releases/redis-{version_text}.tar.gz"
        })

    return releases


def _get_releases_from_github_api(max_pages: int) -> List[Dict]:
    """Fallback via GitHub API (utile si GitHub renvoie un HTML non parseable)."""
    session = requests.Session()
    session.headers.update({
        **headers,
        'Accept': 'application/vnd.github+json'
    })

    all_releases: List[Dict] = []
    seen_versions = set()

    # 100 items/page max pour l'API
    for page in range(1, max_pages + 1):
        url = f"https://api.github.com/repos/redis/redis/releases?per_page=100&page={page}"
        try:
            resp = session.get(url, timeout=30)
            if resp.status_code == 403:
                # Rate limit probable
                break
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list) or not data:
                break

            for rel in data:
                tag = (rel.get('tag_name') or '').strip()
                m = re.search(r'v?(\d+\.\d+(?:\.\d+)*)', tag)
                if not m:
                    continue
                version_text = m.group(1)
                if version_text in seen_versions:
                    continue
                seen_versions.add(version_text)

                parts = version_text.split('.')
                if len(parts) < 2:
                    continue

                published = rel.get('published_at')
                if published and published.endswith('Z'):
                    try:
                        date_obj = datetime.strptime(published, '%Y-%m-%dT%H:%M:%SZ')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    except Exception:
                        formatted_date = "Date non disponible"
                else:
                    formatted_date = "Date non disponible"

                all_releases.append({
                    'version': parts[0],
                    'patch': '.'.join(parts[1:]) if len(parts) > 1 else '0',
                    'date': formatted_date,
                    'url': rel.get('html_url') or f"https://github.com/redis/redis/releases/tag/v{version_text}",
                    'download_url': f"https://download.redis.io/releases/redis-{version_text}.tar.gz"
                })

            # Si on a déjà beaucoup de releases, inutile de trop paginer
            if len(all_releases) >= 1000:
                break

        except Exception:
            break

    return all_releases

def get_all_releases(max_pages: int = 8) -> List[Dict]:
    """Récupère les versions de Redis depuis GitHub (limité à 8 pages par défaut)"""
    print(f"🔍 Récupération des versions (max {max_pages} pages)...")
    
    all_releases = []
    session = requests.Session()
    session.headers.update({
        **headers,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8'
    })
    
    for page in range(1, max_pages + 1):
        url = f"https://github.com/redis/redis/releases?page={page}"
        print(f"📄 Page {page}/{max_pages}...", end=' ', flush=True)
        
        try:
            response = session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')

            page_releases = _extract_releases_from_soup(soup)
            if not page_releases:
                print("Aucune version trouvée sur cette page (HTML).")
                # ne pas break immédiatement: si GitHub renvoie une page spéciale, on tente quand même les autres pages
            else:
                # Déduplication globale
                existing = {f"{r['version']}.{r['patch']}" for r in all_releases}
                for r in page_releases:
                    key = f"{r['version']}.{r['patch']}"
                    if key not in existing:
                        all_releases.append(r)
                        existing.add(key)
            
            print(f"OK ({len(all_releases)} total)")
            time.sleep(0.5)
            
        except requests.RequestException as e:
            print(f"\n⚠️ Erreur lors de la récupération de la page {page}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                retry_after = int(e.response.headers.get('Retry-After', 10))
                print(f"⚠️ Trop de requêtes. Attente de {retry_after} secondes...")
                time.sleep(retry_after)
                continue
            break
        except Exception as e:
            print(f"\n❌ Erreur inattendue: {str(e)}")
            break
    
    # Fallback API si aucune version trouvée via HTML
    if not all_releases:
        print("⚠️ Aucune version trouvée via HTML, tentative via GitHub API...")
        all_releases = _get_releases_from_github_api(max_pages=max_pages)

    return all_releases

def load_redis_versions(use_github: bool = True) -> List[Dict]:
    """Charge les versions de Redis depuis GitHub ou depuis le fichier local"""
    if use_github:
        return get_all_releases(max_pages=11)
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
        version_str = f"{version['version']}.{version['patch']}" if version.get('patch') and version['patch'] != '0' else version['version']
        release_url = version.get('url') or f"https://github.com/redis/redis/releases/tag/v{version_str}"
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
    if any(x in title_lower for x in ['performance', 'optimisation', 'rapidité', 'vitesse', 'latency', 'throughput']):
        return 'performance_improvements'
    elif any(x in title_lower for x in ['security', 'sécurité', 'vulnérabilité', 'cve']):
        return 'security_fixes'
    elif any(x in title_lower for x in ['feature', 'new', 'amélioration', 'améliorations', 'added', 'introduce']):
        return 'new_features'
    elif any(x in title_lower for x in ['api', 'protocol', 'client', 'command', 'interface']):
        return 'api_changes'
    elif any(x in title_lower for x in ['breaking change', 'changement majeur', 'incompatibilité', 'incompatible']):
        return 'breaking_changes'
    else:
        return 'other_improvements'

def extract_changes(sections: List[Dict]) -> Dict[str, List[str]]:
    """Extrait et catégorise les changements à partir des sections de notes de version."""
    changes = {
        'performance_improvements': [],
        'security_fixes': [],
        'new_features': [],
        'api_changes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    keyword_map = {
        'performance_improvements': ['performance', 'optimiz', 'faster', 'speed', 'latency', 'throughput', 'memory'],
        'security_fixes': ['security', 'cve', 'vulnerability', 'vuln', 'tls', 'ssl', 'auth'],
        'new_features': ['new', 'feature', 'introduc', 'add', 'support'],
        'api_changes': ['api', 'protocol', 'command', 'client', 'interface'],
        'breaking_changes': ['breaking', 'incompatible', 'deprecated', 'removed']
    }
    
    for section in sections:
        title = section.get('title', '').strip()
        section_type = section.get('type', 'other_improvements')
        
        for item in section.get('content', []):
            text = item.strip()
            if not text or len(text) < 10:
                continue
            
            change_line = f"{title}: {text}" if title else text
            lower = change_line.lower()
            
            if section_type in changes and section_type != 'other_improvements':
                changes[section_type].append(change_line)
                continue
            
            categorized = False
            for cat, kws in keyword_map.items():
                if any(kw in lower for kw in kws):
                    changes[cat].append(change_line)
                    categorized = True
                    break
            if not categorized:
                changes['other_improvements'].append(change_line)
    
    for cat in changes:
        changes[cat] = list(dict.fromkeys(changes[cat]))
    
    return changes

def analyze_changes(all_changes: Dict[str, List[str]]) -> Dict:
    """Analyse les changements et génère des statistiques globales."""
    analysis = {
        'summary': {},
        'key_changes': [],
        'trends': {}
    }
    
    for category, items in all_changes.items():
        analysis['summary'][category] = {
            'count': len(items),
            'items': items[:5]
        }
    
    flat = []
    for category, items in all_changes.items():
        for it in items:
            flat.append({'category': category, 'content': it})
    flat.sort(key=lambda x: len(x['content']), reverse=True)
    analysis['key_changes'] = flat[:10]
    
    analysis['trends'] = {
        'most_active_category': max(all_changes.keys(), key=lambda k: len(all_changes[k])) if all_changes else 'other_improvements',
        'total_changes': sum(len(v) for v in all_changes.values())
    }
    
    return analysis

def generate_change_report(max_pages: int = 11) -> Dict:
    """Génère un rapport complet sur les changements Redis par version."""
    print("🚀 Début de l'analyse des changements de Redis...")
    
    versions = get_all_releases(max_pages=max_pages)
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
    
    versions_with_changes = []
    all_changes = {
        'performance_improvements': [],
        'security_fixes': [],
        'new_features': [],
        'api_changes': [],
        'breaking_changes': [],
        'other_improvements': []
    }
    
    try:
        for version in versions:
            version_str = f"{version['version']}.{version['patch']}" if version.get('patch') and version['patch'] != '0' else version['version']
            print(f"\nTraitement de la version {version_str}...")
            
            sections = get_release_notes(version)
            if not sections:
                versions_with_changes.append({
                    'version': version_str,
                    'date': version.get('date', 'Date non disponible'),
                    'url': version.get('url', ''),
                    'download_url': version.get('download_url', ''),
                    'changes_count': 0,
                    'changes': {k: [] for k in all_changes.keys()},
                    'total_changes': 0
                })
                continue
            
            changes = extract_changes(sections)
            total_changes = sum(len(v) for v in changes.values())
            
            versions_with_changes.append({
                'version': version_str,
                'date': version.get('date', 'Date non disponible'),
                'url': version.get('url', ''),
                'download_url': version.get('download_url', ''),
                'changes_count': total_changes,
                'changes': changes,
                'total_changes': total_changes
            })
            
            for cat in all_changes:
                all_changes[cat].extend(changes.get(cat, []))
            
            time.sleep(1)
        
        for cat in all_changes:
            all_changes[cat] = list(dict.fromkeys(all_changes[cat]))
        
        analysis = analyze_changes(all_changes)
        
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

        output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'API', 'sources', 'redis-versions.json'))
        with open(output_file, 'w', encoding='utf-8') as f:
            output_versions = []
            for version_info in versions_with_changes:
                version_str = (version_info.get('version') or '').strip()
                major_version = ''
                version_parts = version_str.split('.') if version_str else []
                if len(version_parts) >= 2:
                    major_version = '.'.join(version_parts[:2])

                raw_changes: List[str] = []
                changes_by_category = version_info.get('changes')
                if isinstance(changes_by_category, dict):
                    for _, items in changes_by_category.items():
                        if isinstance(items, list):
                            raw_changes.extend(items)
                elif isinstance(changes_by_category, list):
                    raw_changes = changes_by_category

                output_versions.append({
                    "database": "Redis",
                    'major_version': major_version,
                    'patch_version': version_str,
                    'date': version_info.get('date', ''),
                    'changes': raw_changes
                })

            json.dump(output_versions, f, indent=4, ensure_ascii=False)
        
        print(f"\n✅ Rapport d'analyse des changements sauvegardé dans {output_file}")
        return report
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération du rapport: {str(e)}"
        print(error_msg)
        return {'error': error_msg}

def generate_markdown_report(report: Dict):
    """Génère un rapport au format Markdown à partir du rapport JSON."""
    if 'error' in report:
        return f"# Erreur\n\n{report['error']}"
    
    markdown = ["# Rapport de Changements Redis\n"]
    
    # Résumé
    markdown.append("## Résumé\n")
    markdown.append(f"- **Versions analysées**: {report['summary']['total_versions_analyzed']}")
    markdown.append(f"- **Total de changements**: {report['summary']['total_changes']}")
    markdown.append("\n### Par catégorie:")
    
    summary = report['global_analysis']['analysis']['summary']
    for category, data in summary.items():
        if data['count'] > 0:
            markdown.append(f"- **{category.replace('_', ' ').title()}**: {data['count']}")
    
    # Détails par version
    markdown.append("\n## Détails par version\n")
    
    for version_info in report['versions']:
        markdown.append(f"### Redis {version_info['version']}")
        markdown.append(f"- Date: {version_info.get('date', 'Date non disponible')}")
        if version_info.get('url'):
            markdown.append(f"- URL: {version_info['url']}")
        markdown.append(f"- Total changements: {version_info.get('total_changes', 0)}")
        
        changes = version_info.get('changes', {})
        for category, items in changes.items():
            if items:
                markdown.append(f"\n#### {category.replace('_', ' ').title()} ({len(items)})\n")
                for item in items[:10]:
                    content = item[:200] + ('...' if len(item) > 200 else '')
                    markdown.append(f"- {content}")
        
        markdown.append("\n---\n")
    
    # Enregistrer le rapport Markdown
    output_file = 'redis_changes_report.md'
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
    
    report = generate_change_report(max_pages=11)
    
    if 'error' in report:
        print(f"\n❌ Erreur: {report['error']}")
    else:
        # Afficher un résumé
        print("\n📊 RÉSULTATS")
        print(f"• Versions analysées: {report['summary']['total_versions_analyzed']}")
        print(f"• Total de changements: {report['summary']['total_changes']}")
        
        print("\n📈 Répartition par catégorie:")
        summary = report['global_analysis']['analysis']['summary']
        for category, data in summary.items():
            if data['count'] > 0:
                percentage = (data['count'] / report['summary']['total_changes']) * 100 if report['summary']['total_changes'] else 0
                print(f"   • {category.replace('_', ' ').title()}: {data['count']} ({percentage:.1f}%)")
        
        # Calculer et afficher le temps d'exécution
        exec_time = time.time() - start_time
        print(f"\n✅ Analyse terminée en {exec_time:.1f} secondes")
        print(f"📄 Rapport sauvegardé: redis_changes_report.json")

if __name__ == "__main__":
    main()