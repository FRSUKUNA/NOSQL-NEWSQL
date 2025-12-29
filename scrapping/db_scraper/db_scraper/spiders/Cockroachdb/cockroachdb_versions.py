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

def extract_key_changes(soup: BeautifulSoup, version: str) -> List[str]:
    """Extrait les changements clés (key changes) d'une version."""
    key_changes = []
    
    try:
        # Chercher les sections de highlights ou key features
        keywords = ['highlights', 'key features', 'key changes', 'what\'s new', 'major changes', 'notable changes']
        
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_text = heading.get_text(strip=True).lower()
            
            if any(keyword in heading_text for keyword in keywords):
                # Récupérer les éléments de liste suivants
                next_element = heading.find_next_sibling()
                
                while next_element and len(key_changes) < 10:
                    if next_element.name in ['ul', 'ol']:
                        for li in next_element.find_all('li', recursive=False):
                            text = li.get_text(strip=True)
                            if len(text) > 20 and len(text) < 300:
                                key_changes.append(text)
                                if len(key_changes) >= 10:
                                    break
                        break
                    elif next_element.name == 'p':
                        text = next_element.get_text(strip=True)
                        if len(text) > 30 and len(text) < 300:
                            key_changes.append(text)
                    
                    next_element = next_element.find_next_sibling()
                    if next_element and next_element.name in ['h1', 'h2', 'h3', 'h4']:
                        break
                
                if key_changes:
                    break
        
        # Si pas trouvé, chercher les premiers paragraphes informatifs
        if not key_changes:
            paragraphs = soup.find_all('p')
            for para in paragraphs[:15]:
                text = para.get_text(strip=True)
                if len(text) > 50 and len(text) < 300:
                    # Filtrer les paragraphes qui semblent être des changements
                    if any(word in text.lower() for word in ['new', 'added', 'improved', 'fixed', 'support', 'feature', 'performance', 'security']):
                        key_changes.append(text)
                        if len(key_changes) >= 8:
                            break
        
        print(f"  ✓ {len(key_changes)} key changes extraits pour v{version}")
        
    except Exception as e:
        print(f"  ⚠ Erreur extraction key changes v{version}: {e}")
    
    return key_changes[:10]  # Maximum 10 key changes


def extract_version_features(soup: BeautifulSoup, version: str) -> List[str]:
    """Extrait les fonctionnalités spécifiques introduites dans cette version."""
    features = []
    
    try:
        # Chercher les sections de features
        keywords = ['new features', 'features', 'capabilities', 'enhancements', 'additions']
        
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_text = heading.get_text(strip=True).lower()
            
            if any(keyword in heading_text for keyword in keywords) and 'feature' in heading_text:
                # Récupérer les éléments de liste suivants
                next_element = heading.find_next_sibling()
                
                while next_element and len(features) < 8:
                    if next_element.name in ['ul', 'ol']:
                        for li in next_element.find_all('li', recursive=False):
                            text = li.get_text(strip=True)
                            # Extraire juste le nom de la feature (première phrase ou jusqu'à :)
                            if ':' in text:
                                feature_name = text.split(':')[0].strip()
                            else:
                                feature_name = text.split('.')[0].strip()
                            
                            if len(feature_name) > 10 and len(feature_name) < 150:
                                features.append(feature_name)
                                if len(features) >= 8:
                                    break
                        break
                    
                    next_element = next_element.find_next_sibling()
                    if next_element and next_element.name in ['h1', 'h2', 'h3']:
                        break
                
                if features:
                    break
        
        # Si pas trouvé, extraire des innovations SQL ou techniques
        if not features:
            all_text = soup.get_text()
            patterns = [
                r'(?:new|added|introduced)\s+([A-Z][A-Za-z\s]{10,80})',
                r'(?:support for|supports)\s+([A-Za-z\s]{10,80})',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, all_text)
                for match in matches[:5]:
                    clean_match = match.strip()
                    if len(clean_match) > 10:
                        features.append(clean_match)
                        if len(features) >= 6:
                            break
                if features:
                    break
        
        print(f"  ✓ {len(features)} features extraites pour v{version}")
        
    except Exception as e:
        print(f"  ⚠ Erreur extraction features v{version}: {e}")
    
    return features[:8]  # Maximum 8 features


def get_acid_properties() -> Dict[str, str]:
    """Récupère les propriétés ACID complètes de CockroachDB depuis plusieurs sources."""
    print("Récupération des propriétés ACID de CockroachDB...")
    
    acid_properties = {
        'atomicity': '',
        'consistency': '',
        'isolation': '',
        'durability': '',
        'distributed_sql': '',
        'high_availability': ''
    }
    
    # Essayer plusieurs URLs pour obtenir des informations complètes
    urls = [
        "https://www.cockroachlabs.com/docs/stable/architecture/transaction-layer",
        "https://www.cockroachlabs.com/docs/stable/demo-serializable"
    ]
    
    for url in urls:
        try:
            print(f"  Tentative: {url}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            content = soup.find('article') or soup.find('main') or soup.find('div', class_='content') or soup
            
            # Chercher les sections avec des titres spécifiques (h2, h3, h4)
            page_headers = content.find_all(['h1', 'h2', 'h3', 'h4'])
            
            for header in page_headers:
                header_text = header.get_text(strip=True).lower()
                
                # Trouver le contenu suivant le header
                next_content = []
                sibling = header.find_next_sibling()
                
                # Collecter les paragraphes après le header
                while sibling and sibling.name not in ['h1', 'h2', 'h3', 'h4']:
                    if sibling.name in ['p', 'div']:
                        text = sibling.get_text(strip=True)
                        if len(text) > 30:
                            next_content.append(text)
                    sibling = sibling.find_next_sibling()
                    if len(next_content) >= 3:  # Limiter à 3 paragraphes
                        break
                
                combined_text = ' '.join(next_content)
                
                # Chercher Atomicity
                if not acid_properties['atomicity'] and 'atomic' in header_text:
                    if combined_text and len(combined_text) > 50:
                        acid_properties['atomicity'] = combined_text[:600]
                        print(f"  ✓ Atomicity trouvée (section: {header_text[:50]})")
                
                # Chercher Consistency
                if not acid_properties['consistency'] and 'consistency' in header_text:
                    if combined_text and len(combined_text) > 50:
                        acid_properties['consistency'] = combined_text[:600]
                        print(f"  ✓ Consistency trouvée (section: {header_text[:50]})")
                
                # Chercher Isolation
                if not acid_properties['isolation'] and 'isolation' in header_text:
                    if combined_text and len(combined_text) > 50:
                        acid_properties['isolation'] = combined_text[:600]
                        print(f"  ✓ Isolation trouvée (section: {header_text[:50]})")
                
                # Chercher Durability
                if not acid_properties['durability'] and 'durability' in header_text:
                    if combined_text and len(combined_text) > 50:
                        acid_properties['durability'] = combined_text[:600]
                        print(f"  ✓ Durability trouvée (section: {header_text[:50]})")
            
            # Si les headers ne fonctionnent pas, chercher dans les paragraphes avec contexte
            if not all([acid_properties[k] for k in ['atomicity', 'consistency', 'isolation', 'durability']]):
                paragraphs = content.find_all('p')
                
                for i, para in enumerate(paragraphs):
                    text = para.get_text(strip=True)
                    text_lower = text.lower()
                    
                    # Atomicity - chercher des phrases spécifiques
                    if not acid_properties['atomicity']:
                        if 'atomic' in text_lower and any(kw in text_lower for kw in ['all or nothing', 'commit', 'rollback', 'abort']):
                            if len(text) > 80 and 'transaction' in text_lower:
                                acid_properties['atomicity'] = text[:600]
                                print(f"  ✓ Atomicity trouvée (paragraphe)")
                    
                    # Consistency - chercher des phrases spécifiques
                    if not acid_properties['consistency']:
                        if 'consistency' in text_lower and any(kw in text_lower for kw in ['constraint', 'valid state', 'integrity', 'rules']):
                            if len(text) > 80 and text_lower.count('consistency') == 1:
                                acid_properties['consistency'] = text[:600]
                                print(f"  ✓ Consistency trouvée (paragraphe)")
                    
                    # Isolation - chercher des phrases spécifiques
                    if not acid_properties['isolation']:
                        if 'isolation' in text_lower and any(kw in text_lower for kw in ['serializable', 'concurrent', 'level', 'snapshot']):
                            if len(text) > 80 and text_lower.count('isolation') <= 2:
                                acid_properties['isolation'] = text[:600]
                                print(f"  ✓ Isolation trouvée (paragraphe)")
                    
                    # Durability - chercher des phrases spécifiques
                    if not acid_properties['durability']:
                        if 'durability' in text_lower and any(kw in text_lower for kw in ['persist', 'disk', 'storage', 'crash', 'survive']):
                            if len(text) > 80:
                                acid_properties['durability'] = text[:600]
                                print(f"  ✓ Durability trouvée (paragraphe)")
            
            # Si toutes les propriétés sont trouvées, arrêter
            if all([acid_properties[k] for k in ['atomicity', 'consistency', 'isolation', 'durability']]):
                break
                
            time.sleep(1)  # Respecter le serveur
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Ignorer silencieusement les pages non trouvées
                continue
            else:
                print(f"  ⚠ Erreur HTTP {e.response.status_code} avec {url}")
                continue
        except Exception as e:
            print(f"  ⚠ Erreur avec {url}: {e}")
            continue
    
    # Valeurs par défaut améliorées si non trouvées
    if not acid_properties['atomicity']:
        acid_properties['atomicity'] = "CockroachDB garantit l'atomicité des transactions : toutes les opérations d'une transaction sont exécutées complètement ou pas du tout (all-or-nothing). Si une transaction échoue à n'importe quel moment, toutes les modifications sont annulées via un rollback automatique, garantissant qu'aucune modification partielle n'est jamais visible dans la base de données. Cette propriété est fondamentale pour maintenir l'intégrité des données dans des opérations complexes impliquant plusieurs modifications."
        print("  ℹ Atomicity: Utilisation de la valeur par défaut")
    
    if not acid_properties['consistency']:
        acid_properties['consistency'] = "CockroachDB maintient la cohérence en s'assurant que toutes les transactions respectent les contraintes définies dans le schéma de la base de données (clés primaires, clés étrangères, contraintes CHECK, contraintes UNIQUE, etc.). La base de données passe toujours d'un état valide à un autre état valide. Les transactions qui violeraient ces contraintes sont automatiquement rejetées, préservant ainsi l'intégrité référentielle et logique des données à tout moment."
        print("  ℹ Consistency: Utilisation de la valeur par défaut")
    
    if not acid_properties['isolation']:
        acid_properties['isolation'] = "CockroachDB utilise le niveau d'isolation SERIALIZABLE par défaut, le plus strict du standard SQL (également compatible avec READ COMMITTED). Cela signifie que les transactions concurrentes s'exécutent comme si elles étaient exécutées en série, éliminant toutes les anomalies de lecture : dirty reads (lectures sales), non-repeatable reads (lectures non répétables), et phantom reads (lectures fantômes). CockroachDB utilise un mécanisme de contrôle de concurrence optimiste basé sur des timestamps pour gérer l'isolation."
        print("  ℹ Isolation: Utilisation de la valeur par défaut")
    
    if not acid_properties['durability']:
        acid_properties['durability'] = "CockroachDB garantit la durabilité en répliquant automatiquement les données sur plusieurs nœuds (par défaut 3 réplicas). Une fois qu'une transaction est validée (committed), les données sont persistées de manière durable et survivront aux pannes de nœuds ou aux crashes système."
    
    # Informations spécifiques à CockroachDB
    acid_properties['distributed_sql'] = "CockroachDB est une base de données SQL distribuée qui supporte le standard SQL avec des transactions ACID complètes sur un cluster distribué géographiquement. Elle combine les avantages du SQL relationnel avec la scalabilité horizontale des systèmes NoSQL."
    
    acid_properties['high_availability'] = "CockroachDB offre une haute disponibilité (99.99%+) grâce à la réplication automatique, le consensus Raft pour la cohérence, et la tolérance aux pannes sans point unique de défaillance (SPOF). Le système peut survivre à la perte de nœuds tout en continuant à servir les requêtes."
    
    print("✓ Propriétés ACID complètes récupérées")
    return acid_properties

def get_cockroachdb_versions() -> List[dict]:
    """Récupère les versions de CockroachDB depuis la page officielle des releases."""
    print("Récupération des versions de CockroachDB...")
    
    url = "https://www.cockroachlabs.com/docs/releases/"
    
    versions = []
    
    try:
        print(f"Connexion à {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Chercher tous les liens vers les pages de versions
        version_links = soup.find_all('a', href=re.compile(r'/docs/releases/v\d+\.\d+'))
        
        seen_versions = set()
        
        for link in version_links:
            href = link.get('href', '')
            version_match = re.search(r'v(\d+)\.(\d+)', href)
            
            if version_match:
                major = version_match.group(1)
                minor = version_match.group(2)
                version_key = f"{major}.{minor}"
                
                if version_key not in seen_versions:
                    seen_versions.add(version_key)
                    
                    # Extraire des informations supplémentaires du texte du lien
                    link_text = link.get_text(strip=True)
                    
                    # Déterminer le type de release
                    release_type = "Regular"
                    if any(keyword in link_text.lower() for keyword in ['innovation', 'optional']):
                        release_type = "Innovation"
                    
                    versions.append({
                        'version': major,
                        'patch': minor,
                        'full_version': version_key,
                        'date': 'Date à récupérer',
                        'release_type': release_type,
                        'url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}",
                        'download_url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}#downloads"
                    })
                    
                    print(f"Trouvé: v{version_key} ({release_type})")
        
        # Si peu de versions trouvées, essayer une approche alternative
        if len(versions) < 5:
            print("Recherche alternative des versions...")
            
            # Chercher dans le texte de la page
            content = soup.get_text()
            version_pattern = re.compile(r'v?(\d+)\.(\d+)\.(\d+)')
            found_versions = version_pattern.findall(content)
            
            for major, minor, patch in found_versions:
                version_key = f"{major}.{minor}"
                if version_key not in seen_versions:
                    seen_versions.add(version_key)
                    
                    versions.append({
                        'version': major,
                        'patch': minor,
                        'full_version': version_key,
                        'date': 'Date non disponible',
                        'release_type': 'Regular',
                        'url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}",
                        'download_url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}#downloads"
                    })
                    
                    print(f"Trouvé (alternative): v{version_key}")
                    
                    if len(versions) >= 20:  # Limiter à 20 versions
                        break
        
        # Récupérer les dates complètes et métadonnées pour chaque version
        print("\nRécupération des dates complètes et métadonnées...")
        for version_info in versions[:10]:  # Limiter à 10 pour éviter trop de requêtes
            try:
                time.sleep(1)  # Respecter le serveur
                version_url = version_info['url']
                version_response = requests.get(version_url, headers=headers, timeout=30)
                version_response.raise_for_status()
                
                version_soup = BeautifulSoup(version_response.text, 'html.parser')
                page_text = version_soup.get_text()
                
                # Chercher les dates complètes (format: Month Day, Year)
                date_patterns = [
                    r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})',
                    r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4})',
                    r'(\d{4}-\d{2}-\d{2})'
                ]
                
                date_found = None
                for pattern in date_patterns:
                    dates = re.findall(pattern, page_text)
                    if dates:
                        date_found = dates[0] if isinstance(dates[0], str) else dates[0][0]
                        break
                
                if date_found:
                    version_info['date'] = date_found
                    print(f"  ✓ v{version_info['full_version']}: {date_found}")
                else:
                    print(f"  ⚠ v{version_info['full_version']}: Date non trouvée")
                
                # Extraire le type de release (LTS, Innovation, etc.)
                if 'LTS' in page_text or 'Long Term Support' in page_text:
                    version_info['release_type'] = 'LTS (Long Term Support)'
                elif 'Innovation Release' in page_text:
                    version_info['release_type'] = 'Innovation Release'
                elif 'Testing Release' in page_text:
                    version_info['release_type'] = 'Testing Release'
                
                # Extraire les notes importantes
                version_info['notes'] = []
                if 'required' in page_text.lower():
                    version_info['notes'].append('Required upgrade')
                if 'optional' in page_text.lower():
                    version_info['notes'].append('Optional upgrade')
                if 'security' in page_text.lower():
                    version_info['notes'].append('Contains security fixes')
                
                # Extraire les key changes (changements clés)
                version_info['key_changes'] = extract_key_changes(version_soup, version_info['full_version'])
                
                # Extraire les features spécifiques à cette version
                version_info['features'] = extract_version_features(version_soup, version_info['full_version'])
                
            except Exception as e:
                print(f"  ⚠ Erreur v{version_info['full_version']}: {e}")
                version_info['notes'] = []
                version_info['key_changes'] = []
                version_info['features'] = []
                    
    except Exception as e:
        print(f"Erreur lors de la récupération des versions: {str(e)}")
    
    return versions

def get_github_releases() -> List[dict]:
    """Récupère les releases depuis GitHub (méthode alternative)."""
    print("\nRécupération des versions depuis GitHub...")
    
    url = "https://api.github.com/repos/cockroachdb/cockroach/releases"
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        releases = response.json()
        github_versions = []
        
        for release in releases[:20]:  # Limiter à 20
            tag_name = release.get('tag_name', '')
            version_match = re.search(r'v(\d+)\.(\d+)\.(\d+)', tag_name)
            
            if version_match:
                major, minor, patch = version_match.groups()
                
                github_versions.append({
                    'version': major,
                    'patch': minor,
                    'full_version': f"{major}.{minor}.{patch}",
                    'date': release.get('published_at', '').split('T')[0],
                    'release_type': 'Production' if not release.get('prerelease') else 'Testing',
                    'url': release.get('html_url', ''),
                    'download_url': release.get('html_url', ''),
                    'key_changes': [],
                    'features': []
                })
                
                print(f"Trouvé sur GitHub: v{major}.{minor}.{patch} - {release.get('published_at', '').split('T')[0]}")
        
        return github_versions
        
    except Exception as e:
        print(f"Erreur lors de la récupération depuis GitHub: {e}")
        return []
    
def main():
    # Récupérer les propriétés ACID
    acid_properties = get_acid_properties()
    
    # Récupérer les versions depuis le site officiel
    versions = get_cockroachdb_versions()
    
    # Si peu de versions, essayer GitHub
    if len(versions) < 5:
        print("\nTentative de récupération depuis GitHub...")
        github_versions = get_github_releases()
        if github_versions:
            versions.extend(github_versions)
    
    if not versions:
        print("Aucune version trouvée.")
        return
    
    # Trier les versions par numéro (du plus récent au plus ancien)
    versions.sort(key=lambda x: [int(n) for n in x['full_version'].split('.')], reverse=True)
    
    # Retirer les doublons
    unique_versions = []
    seen = set()
    for v in versions:
        key = v['full_version']
        if key not in seen:
            seen.add(key)
            unique_versions.append(v)
    
    # Préparer les données à sauvegarder
    output_data = {
        'database_info': {
            'name': 'CockroachDB',
            'type': 'Distributed SQL',
            'features': [
                'SQL Standard',
                'Distribution globale',
                'Haute disponibilité',
                'Transactions ACID',
                'Scalabilité horizontale'
            ]
        },
        'acid_properties': acid_properties,
        'versions': unique_versions,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    
    # Sauvegarder dans un fichier JSON
    output_file = 'cockroachdb_versions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"{len(unique_versions)} versions trouvées et sauvegardées dans {output_file}")
    print(f"{'='*60}")
    
    print("\n🔒 Propriétés ACID/Caractéristiques:")
    for prop, value in acid_properties.items():
        prop_name = prop.replace('_', ' ').title()
        if len(value) > 150:
            print(f"  • {prop_name}:")
            print(f"    {value[:150]}...")
        else:
            print(f"  • {prop_name}: {value}")
    
    print("\n📦 Aperçu des versions (5 plus récentes):")
    for i, ver in enumerate(unique_versions[:5], 1):
        release_badge = "🟢" if 'LTS' in ver.get('release_type', '') else ("🔵" if 'Innovation' in ver.get('release_type', '') else "🟡")
        notes_str = f" | {', '.join(ver.get('notes', []))}" if ver.get('notes') else ""
        print(f"  {i}. {release_badge} v{ver['full_version']} ({ver.get('release_type', 'N/A')}) - {ver['date']}{notes_str}")
        
        # Afficher les key changes
        key_changes = ver.get('key_changes', [])
        if key_changes:
            print(f"     🔑 Key Changes ({len(key_changes)}):")
            for change in key_changes[:3]:
                print(f"        - {change[:80]}..." if len(change) > 80 else f"        - {change}")
        
        # Afficher les features
        features = ver.get('features', [])
        if features:
            print(f"     ✨ New Features ({len(features)}):")
            for feature in features[:3]:
                print(f"        - {feature[:80]}..." if len(feature) > 80 else f"        - {feature}")
    
    if len(unique_versions) > 5:
        print(f"  ... et {len(unique_versions) - 5} versions supplémentaires")

if __name__ == "__main__":
    main()
    