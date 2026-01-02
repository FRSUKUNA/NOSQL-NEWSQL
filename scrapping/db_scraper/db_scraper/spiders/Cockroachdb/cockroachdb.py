import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time
from typing import Dict, List, Optional
import os

# Configuration
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Couleurs pour le terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color, end='\n'):
    """Affiche du texte coloré."""
    print(f"{color}{text}{Colors.ENDC}", end=end)

def extract_releases_from_h3(soup: BeautifulSoup) -> List[Dict]:
    """
    Extrait spécifiquement les informations des h3 contenant "releases"
    """
    releases_data = []
    
    print_colored("🔍 Recherche des h3 avec 'releases'...", Colors.CYAN)
    
    # Trouver tous les h3 qui contiennent "releases"
    h3_elements = soup.find_all('h3')
    
    for h3 in h3_elements:
        h3_text = h3.get_text(strip=True).lower()
        
        if 'releases' in h3_text:
            print_colored(f"✅ H3 trouvé: {h3.get_text(strip=True)}", Colors.GREEN)
            
            # Analyser le contenu après ce h3
            release_info = {
                'h3_title': h3.get_text(strip=True),
                'versions': [],
                'content': []
            }
            
            # Chercher les versions dans le h3 lui-même
            version_match = re.search(r'v(\d+\.\d+)', h3_text)
            if version_match:
                version = version_match.group(1)
                release_info['versions'].append(version)
            
            # Extraire le contenu qui suit ce h3
            next_element = h3.find_next_sibling()
            
            while next_element:
                # Arrêter si on rencontre un autre h3
                if next_element.name == 'h3':
                    break
                
                # Extraire les liens de versions
                if next_element.name == 'p':
                    links = next_element.find_all('a', href=re.compile(r'/docs/releases/v\d+\.\d+'))
                    for link in links:
                        href = link.get('href', '')
                        version_match = re.search(r'v(\d+\.\d+)', href)
                        if version_match:
                            version = version_match.group(1)
                            if version not in release_info['versions']:
                                release_info['versions'].append(version)
                
                # Extraire les listes de versions
                if next_element.name in ['ul', 'ol']:
                    list_items = next_element.find_all('li')
                    for li in list_items:
                        li_text = li.get_text(strip=True)
                        version_match = re.search(r'v(\d+\.\d+)', li_text)
                        if version_match:
                            version = version_match.group(1)
                            if version not in release_info['versions']:
                                release_info['versions'].append(version)
                        
                        # Ajouter le contenu textuel
                        if li_text and len(li_text) > 5:
                            release_info['content'].append(li_text)
                
                # Ajouter le contenu textuel des paragraphes
                if next_element.name == 'p':
                    text = next_element.get_text(strip=True)
                    if text and len(text) > 10:
                        release_info['content'].append(text)
                
                next_element = next_element.find_next_sibling()
            
            if release_info['versions'] or release_info['content']:
                releases_data.append(release_info)
    
    print_colored(f"✅ {len(releases_data)} sections 'releases' trouvées", Colors.GREEN)
    return releases_data

def extract_version_details_from_h3_sections(soup: BeautifulSoup) -> Dict:
    """
    Extrait les détails des versions depuis les sections h3
    """
    version_details = {}
    
    print_colored("🔍 Extraction détaillée des versions depuis les h3...", Colors.CYAN)
    
    # Chercher les h3 avec versions
    h3_elements = soup.find_all('h3')
    
    for h3 in h3_elements:
        h3_text = h3.get_text(strip=True)
        
        # Vérifier si le h3 contient une version
        version_match = re.search(r'v(\d+\.\d+)', h3_text)
        if version_match:
            version = version_match.group(1)
            
            print_colored(f"  📦 Analyse de v{version}...", Colors.BLUE)
            
            version_info = {
                'version': version,
                'title': h3_text,
                'downloads': [],
                'release_notes_url': None,
                'release_type': 'Unknown'
            }
            
            # Chercher l'URL des release notes
            release_notes_link = h3.find('a', href=re.compile(r'/docs/releases/v' + re.escape(version)))
            if release_notes_link:
                version_info['release_notes_url'] = "https://www.cockroachlabs.com" + release_notes_link['href']
            
            # Analyser le contenu après le h3
            next_element = h3.find_next_sibling()
            
            while next_element:
                if next_element.name == 'h3':
                    break
                
                # Extraire les liens de download
                if next_element.name == 'p':
                    links = next_element.find_all('a')
                    for link in links:
                        href = link.get('href', '')
                        text = link.get_text(strip=True)
                        
                        if 'binaries.cockroachdb.com' in href:
                            version_info['downloads'].append({
                                'type': text,
                                'url': href,
                                'architecture': extract_architecture(href)
                            })
                
                # Extraire des listes
                if next_element.name in ['ul', 'ol']:
                    list_items = next_element.find_all('li')
                    for li in list_items:
                        links = li.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            text = link.get_text(strip=True)
                            
                            if 'binaries.cockroachdb.com' in href:
                                version_info['downloads'].append({
                                    'type': text,
                                    'url': href,
                                    'architecture': extract_architecture(href)
                                })
                
                next_element = next_element.find_next_sibling()
            
            # Déterminer le type de release
            if 'testing' in h3_text.lower():
                version_info['release_type'] = 'Testing'
            elif 'production' in h3_text.lower():
                version_info['release_type'] = 'Production'
            elif 'beta' in h3_text.lower() or 'alpha' in h3_text.lower():
                version_info['release_type'] = 'Testing'
            else:
                version_info['release_type'] = 'Production'
            
            version_details[version] = version_info
    
    print_colored(f"✅ {len(version_details)} versions détaillées extraites", Colors.GREEN)
    return version_details

def extract_architecture(url: str) -> str:
    """Extrait l'architecture depuis l'URL"""
    if 'amd64' in url:
        return 'amd64'
    elif 'arm64' in url:
        return 'arm64'
    elif 'darwin' in url:
        return 'macOS'
    elif 'linux' in url:
        return 'Linux'
    else:
        return 'Unknown'

def extract_recent_releases_from_content(soup: BeautifulSoup) -> List[Dict]:
    """
    Extrait les releases récentes depuis le contenu de la page
    """
    recent_releases = []
    
    print_colored("🔍 Extraction des releases récentes...", Colors.CYAN)
    
    # Chercher la section "Recent releases"
    all_h3 = soup.find_all('h3')
    
    for h3 in all_h3:
        if 'recent releases' in h3.get_text(strip=True).lower():
            print_colored("✅ Section 'Recent releases' trouvée", Colors.GREEN)
            
            # Analyser le contenu après ce h3
            next_element = h3.find_next_sibling()
            
            while next_element:
                if next_element.name == 'h3':
                    break
                
                # Extraire les versions depuis les paragraphes
                if next_element.name == 'p':
                    text = next_element.get_text(strip=True)
                    version_matches = re.findall(r'v(\d+\.\d+)', text)
                    
                    for version in version_matches:
                        # Vérifier si c'est un lien
                        link = next_element.find('a', href=re.compile(r'v' + re.escape(version)))
                        url = "https://www.cockroachlabs.com" + link['href'] if link else None
                        
                        recent_releases.append({
                            'version': version,
                            'url': url,
                            'status': 'Current' if url else 'Unsupported'
                        })
                
                # Extraire depuis les listes
                if next_element.name in ['ul', 'ol']:
                    list_items = next_element.find_all('li')
                    for li in list_items:
                        li_text = li.get_text(strip=True)
                        version_match = re.search(r'v(\d+\.\d+)', li_text)
                        
                        if version_match:
                            version = version_match.group(1)
                            link = li.find('a')
                            url = "https://www.cockroachlabs.com" + link['href'] if link else None
                            
                            # Déterminer le statut
                            status = 'Current'
                            if 'unsupported' in li_text.lower():
                                status = 'Unsupported'
                            
                            recent_releases.append({
                                'version': version,
                                'url': url,
                                'status': status
                            })
                
                next_element = next_element.find_next_sibling()
            
            break
    
    print_colored(f"✅ {len(recent_releases)} releases récentes trouvées", Colors.GREEN)
    return recent_releases

def main():
    start_time = time.time()
    
    print("="*80)
    print_colored("🚀 SCRAPER COCKROACHDB - FOCUS H3 'RELEASES'", Colors.BOLD + Colors.CYAN)
    print("="*80)
    print()
    
    try:
        print_colored("📡 Connexion à la page des releases CockroachDB...", Colors.CYAN)
        response = requests.get("https://www.cockroachlabs.com/docs/releases/", headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extraire les données depuis les h3
        h3_releases = extract_releases_from_h3(soup)
        version_details = extract_version_details_from_h3_sections(soup)
        recent_releases = extract_recent_releases_from_content(soup)
        
        # Combiner toutes les données
        output_data = {
            'database_info': {
                'name': 'CockroachDB',
                'type': 'Distributed SQL Database',
                'url': 'https://www.cockroachlabs.com/docs/releases',
                'scraping_method': 'H3 with releases focus'
            },
            'h3_releases_sections': h3_releases,
            'version_details': version_details,
            'recent_releases': recent_releases,
            'statistics': {
                'total_h3_sections': len(h3_releases),
                'total_versions_detailed': len(version_details),
                'total_recent_releases': len(recent_releases)
            },
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        # Sauvegarder les résultats
        target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'API', 'sources'))
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        
        output_file = os.path.join(target_dir, 'cockroachdb-versions.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*80)
        print_colored(f"✅ SCRAPPING TERMINÉ EN {elapsed:.1f}s", Colors.BOLD + Colors.GREEN)
        print("="*80)
        print(f"\n📦 Données sauvegardées dans: {output_file}")
        
        print(f"\n📈 STATISTIQUES:")
        print(f"   🔍 Sections H3 'releases'    : {len(h3_releases)}")
        print(f"   📦 Versions détaillées        : {len(version_details)}")
        print(f"   🕐 Releases récentes          : {len(recent_releases)}")
        
        # Afficher un aperçu des résultats
        print(f"\n📋 APPERÇU DES RÉSULTATS:")
        
        if h3_releases:
            print(f"\n🔍 Sections H3 trouvées:")
            for i, section in enumerate(h3_releases[:3], 1):
                print(f"   {i}. {section['h3_title']}")
                print(f"      Versions: {', '.join(section['versions'])}")
        
        if recent_releases:
            print(f"\n🕐 Releases récentes:")
            for i, release in enumerate(recent_releases[:5], 1):
                status_icon = "✅" if release['status'] == 'Current' else "❌"
                print(f"   {i}. {status_icon} v{release['version']} ({release['status']})")
        
        if version_details:
            print(f"\n📦 Versions détaillées:")
            for version, details in list(version_details.items())[:3]:
                print(f"   • v{version} - {details['release_type']} ({len(details['downloads'])} downloads)")
        
    except Exception as e:
        print_colored(f"\n❌ ERREUR CRITIQUE: {e}", Colors.RED)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
