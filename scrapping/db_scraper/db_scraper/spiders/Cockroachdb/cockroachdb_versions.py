import requests
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime
import time
from typing import Dict, List, Optional
from collections import OrderedDict
import os  # <--- AJOUT IMPORTANT pour gérer les dossiers

# Configuration
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Couleurs pour le terminal (ANSI codes)
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

def extract_minor_releases_from_main_page(soup: BeautifulSoup) -> List[Dict]:
    """Extrait toutes les versions trimestrielles."""
    minor_releases = []
    seen_versions = set()
    
    print_colored("🔍 Extraction des versions trimestrielles depuis la page principale...", Colors.CYAN)
    
    version_links = soup.find_all('a', href=re.compile(r'/docs/releases/v\d+\.\d+'))
    
    for link in version_links:
        href = link.get('href', '')
        version_match = re.search(r'/docs/releases/v(\d+)\.(\d+)', href)
        
        if version_match:
            major = version_match.group(1)
            minor = version_match.group(2)
            version_key = f"{major}.{minor}"
            
            if int(major) >= 19 and version_key not in seen_versions:
                seen_versions.add(version_key)
                minor_releases.append({
                    'major_version': major,
                    'minor_version': minor,
                    'full_version': version_key,
                    'url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}"
                })
    
    headings = soup.find_all(['h2', 'h3'])
    for heading in headings:
        heading_text = heading.get_text(strip=True)
        version_match = re.search(r'v(\d+)\.(\d+)', heading_text)
        
        if version_match:
            major = version_match.group(1)
            minor = version_match.group(2)
            version_key = f"{major}.{minor}"
            
            if int(major) >= 19 and version_key not in seen_versions:
                seen_versions.add(version_key)
                minor_releases.append({
                    'major_version': major,
                    'minor_version': minor,
                    'full_version': version_key,
                    'url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}"
                })
    
    minor_releases.sort(
        key=lambda x: [int(n) for n in x['full_version'].split('.')],
        reverse=True
    )
    
    print_colored(f"✅ {len(minor_releases)} versions trimestrielles trouvées\n", Colors.GREEN)
    return minor_releases


def extract_all_patches_from_version_page(version_url: str, version_key: str) -> List[Dict]:
    """
    Extrait TOUS les patches avec détection intelligente LTS.
    """
    patches = []
    seen_patches = set()
    
    try:
        print(f"  🔎 Scanning page de v{version_key}...", end=" ")
        response = requests.get(version_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Déterminer si cette version est LTS
        page_text = soup.get_text()
        is_lts_release = 'LTS' in page_text or 'Long Term Support' in page_text
        
        # Extraire depuis les tableaux
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    version_cell = cells[0]
                    version_cell_full_text = version_cell.get_text(strip=True)
                    date_cell = cells[1].get_text(strip=True)
                    
                    # Vérifier marqueur LTS explicite
                    is_lts_explicit = '(LTS)' in version_cell_full_text or ' LTS ' in version_cell_full_text
                    
                    # Extraire la version
                    version_clean = version_cell_full_text.replace('(LTS)', '').replace('LTS', '').strip()
                    
                    patch_full = None
                    match = re.search(r'v?(\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?)', version_clean)
                    if match:
                        patch_full = match.group(1)
                    
                    if patch_full and patch_full.startswith(version_key):
                        if patch_full not in seen_patches:
                            seen_patches.add(patch_full)
                            
                            # Extraire le numéro de patch
                            patch_num_match = re.search(r'\.(\d+)(?:-|$)', patch_full)
                            patch_number = patch_num_match.group(1) if patch_num_match else '0'
                            
                            # LOGIQUE LTS CORRECTE
                            is_testing = any(x in patch_full for x in ['-alpha', '-beta', '-rc'])
                            # Une version est GA si elle se termine par .0 ET n'a pas de suffixe de test
                            is_ga_version = patch_full.split('.')[-1] == '0' and not is_testing
                            # Un patch LTS = appartient à release LTS + production + pas GA
                            is_lts_patch = (is_lts_release and not is_testing and not is_ga_version) or is_lts_explicit
                            
                            # Déterminer le type
                            if '-alpha' in patch_full:
                                patch_type = 'Testing (Alpha)'
                            elif '-beta' in patch_full:
                                patch_type = 'Testing (Beta)'
                            elif '-rc' in patch_full:
                                patch_type = 'Testing (RC)'
                            elif is_lts_patch:
                                patch_type = 'Production (LTS)'
                            elif is_ga_version:
                                patch_type = 'GA (General Availability)'
                            else:
                                patch_type = 'Production'
                            
                            # Nettoyer la date
                            date_clean = date_cell.strip()
                            if not re.search(r'\d{4}', date_clean):
                                date_clean = 'Date non disponible'
                            
                            patches.append({
                                'version': patch_full,
                                'patch_number': patch_number,
                                'type': patch_type,
                                'date': date_clean,
                                'is_lts': is_lts_patch
                            })
        
        # Stratégie 2: titres
        headings = soup.find_all(['h2', 'h3', 'h4'])
        for heading in headings:
            heading_text = heading.get_text(strip=True)
            
            patch_match = re.search(r'v?(\d+\.\d+\.\d+(?:-(?:alpha|beta|rc)\.\d+)?)', heading_text)
            if patch_match:
                patch_full = patch_match.group(1)
                
                if patch_full.startswith(version_key) and patch_full not in seen_patches:
                    seen_patches.add(patch_full)
                    
                    date = 'Date non disponible'
                    next_elem = heading.find_next(['p', 'div', 'span'])
                    if next_elem:
                        for pattern in [r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})', r'(\d{4}-\d{2}-\d{2})']:
                            date_match = re.search(pattern, next_elem.get_text())
                            if date_match:
                                date = date_match.group(1)
                                break
                    
                    patch_num_match = re.search(r'\.(\d+)(?:-|$)', patch_full)
                    patch_number = patch_num_match.group(1) if patch_num_match else '0'
                    
                    is_testing = any(x in patch_full for x in ['-alpha', '-beta', '-rc'])
                    is_ga_version = patch_full.split('.')[-1] == '0' and not is_testing
                    is_lts_patch = is_lts_release and not is_testing and not is_ga_version
                    
                    if '-alpha' in patch_full:
                        patch_type = 'Testing (Alpha)'
                    elif '-beta' in patch_full:
                        patch_type = 'Testing (Beta)'
                    elif '-rc' in patch_full:
                        patch_type = 'Testing (RC)'
                    elif is_lts_patch:
                        patch_type = 'Production (LTS)'
                    elif is_ga_version:
                        patch_type = 'GA (General Availability)'
                    else:
                        patch_type = 'Production'
                    
                    patches.append({
                        'version': patch_full,
                        'patch_number': patch_number,
                        'type': patch_type,
                        'date': date,
                        'is_lts': is_lts_patch
                    })
        
        # Trier
        def sort_key(p):
            try:
                return int(p['patch_number'])
            except:
                return 0
        
        patches.sort(key=sort_key, reverse=True)
        
        lts_count = sum(1 for p in patches if p.get('is_lts', False))
        
        print_colored(f"✅ {len(patches)} patches trouvés", Colors.GREEN, end="")
        if lts_count > 0:
            print_colored(f" ({lts_count} LTS)", Colors.YELLOW)
        else:
            print()
        
        return patches
        
    except Exception as e:
        print_colored(f"❌ Erreur: {e}", Colors.RED)
        return []


def get_minor_release_metadata(soup: BeautifulSoup, version_key: str) -> Dict:
    """Extrait les métadonnées."""
    metadata = {
        'date': 'Date non disponible',
        'release_type': 'Regular',
        'key_changes': [],
        'features': []
    }
    
    page_text = soup.get_text()
    
    for pattern in [r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4})', r'(\d{4}-\d{2}-\d{2})']:
        dates = re.findall(pattern, page_text)
        if dates:
            metadata['date'] = dates[0]
            break
    
    if 'LTS' in page_text or 'Long Term Support' in page_text:
        metadata['release_type'] = 'LTS (Long Term Support)'
    elif 'Innovation' in page_text or 'innovation release' in page_text.lower():
        metadata['release_type'] = 'Innovation Release'
    elif 'Regular' in page_text or 'regular release' in page_text.lower():
        metadata['release_type'] = 'Regular Release'
    
    metadata['features'] = extract_version_features(soup, version_key)
    metadata['key_changes'] = extract_key_changes(soup, version_key)
    
    return metadata


def extract_key_changes(soup: BeautifulSoup, version: str) -> List[str]:
    """Extrait les changements clés."""
    key_changes = []
    keywords = ['highlights', 'key features', 'key changes', "what's new"]
    
    try:
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_text = heading.get_text(strip=True).lower()
            
            if any(kw in heading_text for kw in keywords):
                next_elem = heading.find_next_sibling()
                
                while next_elem and len(key_changes) < 10:
                    if next_elem.name in ['ul', 'ol']:
                        for li in next_elem.find_all('li', recursive=False):
                            text = li.get_text(strip=True)
                            if 20 < len(text) < 400:
                                key_changes.append(text)
                        break
                    next_elem = next_elem.find_next_sibling()
                    if next_elem and next_elem.name in ['h1', 'h2', 'h3']:
                        break
                if key_changes:
                    break
    except:
        pass
    
    return key_changes[:10]


def extract_version_features(soup: BeautifulSoup, version: str) -> List[str]:
    """Extrait les fonctionnalités."""
    features = []
    keywords = ['new features', 'features', 'feature highlights']
    
    try:
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_text = heading.get_text(strip=True).lower()
            
            if any(kw in heading_text for kw in keywords):
                next_elem = heading.find_next_sibling()
                
                while next_elem and len(features) < 10:
                    if next_elem.name in ['ul', 'ol']:
                        for li in next_elem.find_all('li', recursive=False):
                            text = li.get_text(strip=True)
                            feature_name = text.split(':')[0].strip() if ':' in text else text.split('.')[0].strip()
                            if 10 < len(feature_name) < 200:
                                features.append(feature_name)
                        break
                    next_elem = next_elem.find_next_sibling()
                    if next_elem and next_elem.name in ['h1', 'h2', 'h3']:
                        break
                if features:
                    break
    except:
        pass
    
    return features[:10]


def build_version_hierarchy(minor_releases: List[Dict]) -> Dict:
    """Construit la hiérarchie complète."""
    versions_hierarchy = OrderedDict()
    
    print_colored("\n🏗️  Construction de la hiérarchie complète...", Colors.BOLD)
    print(f"📋 {len(minor_releases)} versions à traiter\n")
    
    for i, minor_release in enumerate(minor_releases, 1):
        version_key = minor_release['full_version']
        major = minor_release['major_version']
        minor = minor_release['minor_version']
        version_url = minor_release['url']
        
        print_colored(f"[{i}/{len(minor_releases)}] 📦 v{version_key}", Colors.CYAN)
        
        if major not in versions_hierarchy:
            versions_hierarchy[major] = {
                'major_version': major,
                'name': f'v{major}',
                'year': 2000 + int(major),
                'minor_releases': OrderedDict()
            }
        
        try:
            response = requests.get(version_url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            metadata = get_minor_release_metadata(soup, version_key)
            patches = extract_all_patches_from_version_page(version_url, version_key)
            
            versions_hierarchy[major]['minor_releases'][version_key] = {
                'full_version': version_key,
                'minor_version': minor,
                'url': version_url,
                'date': metadata['date'],
                'release_type': metadata['release_type'],
                'key_changes': metadata['key_changes'],
                'features': metadata['features'],
                'patches': patches,
                'total_patches': len(patches)
            }
            
            lts_count = sum(1 for p in patches if p.get('is_lts', False))
            
            print(f"  ✅ Métadonnées: {metadata['date']} - {metadata['release_type']}")
            print(f"  ✅ {len(metadata['key_changes'])} changements • {len(metadata['features'])} features")
            print(f"  ✅ {len(patches)} patches au total", end="")
            if lts_count > 0:
                print_colored(f" ({lts_count} LTS)", Colors.GREEN)
            else:
                print()
            print()
            
            time.sleep(1.5)
            
        except Exception as e:
            print_colored(f"  ❌ Erreur: {e}\n", Colors.RED)
    
    return versions_hierarchy


def print_statistics_summary(versions_hierarchy: Dict):
    """Affiche les statistiques."""
    print_colored("\n" + "="*80, Colors.BOLD)
    print_colored("📊 RÉSUMÉ STATISTIQUES PAR TYPE DE RELEASE", Colors.BOLD)
    print("="*80)
    
    stats = {
        'LTS': 0,
        'Innovation': 0,
        'Regular': 0,
        'Total Patches': 0,
        'LTS Patches': 0,
        'Production Patches': 0,
        'Testing Patches': 0
    }
    
    for major_data in versions_hierarchy.values():
        for minor_data in major_data['minor_releases'].values():
            release_type = minor_data['release_type']
            
            if 'LTS' in release_type:
                stats['LTS'] += 1
            elif 'Innovation' in release_type:
                stats['Innovation'] += 1
            else:
                stats['Regular'] += 1
            
            for patch in minor_data['patches']:
                stats['Total Patches'] += 1
                
                if patch.get('is_lts', False):
                    stats['LTS Patches'] += 1
                
                if 'Production' in patch['type']:
                    stats['Production Patches'] += 1
                elif 'Testing' in patch['type']:
                    stats['Testing Patches'] += 1
    
    print(f"\n🎯 Types de Releases:")
    print(f"   🟢 LTS (Long Term Support)  : {stats['LTS']}")
    print(f"   🟣 Innovation Release        : {stats['Innovation']}")
    print(f"   🔵 Regular Release           : {stats['Regular']}")
    
    print(f"\n🔧 Distribution des Patches:")
    print(f"   📦 Total patches             : {stats['Total Patches']}")
    print_colored(f"   🟢 Patches LTS               : {stats['LTS Patches']}", Colors.GREEN)
    print(f"   ✅ Patches Production        : {stats['Production Patches']}")
    print(f"   🧪 Patches Testing           : {stats['Testing Patches']}")
    print()


def print_full_hierarchy(versions_hierarchy: Dict):
    """Affiche la hiérarchie."""
    print("\n" + "="*80)
    print_colored("📊 HIÉRARCHIE COMPLÈTE DES VERSIONS COCKROACHDB", Colors.BOLD + Colors.CYAN)
    print("="*80)
    
    sorted_majors = sorted(versions_hierarchy.keys(), key=lambda x: int(x), reverse=True)
    
    for major in sorted_majors:
        major_data = versions_hierarchy[major]
        minor_releases = major_data['minor_releases']
        
        total_patches = sum(m['total_patches'] for m in minor_releases.values())
        
        print(f"\n{'█'*80}")
        print_colored(f"🎯 VERSION MAJEURE v{major} (Année {major_data['year']})", Colors.BOLD)
        print(f"   {len(minor_releases)} releases • {total_patches} patches au total")
        print(f"{'█'*80}")
        
        sorted_minors = sorted(
            minor_releases.keys(),
            key=lambda x: [int(n) for n in x.split('.')],
            reverse=True
        )
        
        for minor_key in sorted_minors:
            minor_data = minor_releases[minor_key]
            
            badge = "🟢 LTS" if 'LTS' in minor_data['release_type'] else "🔵 REG"
            if 'Innovation' in minor_data['release_type']:
                badge = "🟣 INN"
            
            print(f"\n  {badge} ┌─ v{minor_key} - {minor_data['release_type']}")
            print(f"      │  📅 Date: {minor_data['date']}")
            print(f"      │  🔧 Total patches: {minor_data['total_patches']}")
            
            if minor_data['features']:
                print(f"      │  ✨ Nouvelles fonctionnalités:")
                for feat in minor_data['features'][:5]:
                    print(f"      │     • {feat[:75]}...")
            
            print(f"      │")
            print(f"      │  📋 LISTE COMPLÈTE DES PATCHES:")
            print(f"      │")
            
            for idx, patch in enumerate(minor_data['patches'], 1):
                if patch.get('is_lts', False):
                    type_icon = "🟢"
                    type_display = f"{patch['type']:25s} 🏅"
                elif patch['type'] == 'Production':
                    type_icon = "🟢"
                    type_display = f"{patch['type']:25s}  "
                elif 'Alpha' in patch['type']:
                    type_icon = "🟡"
                    type_display = f"{patch['type']:25s}  "
                elif 'Beta' in patch['type']:
                    type_icon = "🟠"
                    type_display = f"{patch['type']:25s}  "
                elif 'RC' in patch['type']:
                    type_icon = "🔵"
                    type_display = f"{patch['type']:25s}  "
                else:
                    type_icon = "⚪"
                    type_display = f"{patch['type']:25s}  "
                
                print(f"      │  {type_icon} [{idx:2d}] v{patch['version']:20s} | {type_display} | {patch['date']}")
            
            print(f"      └{'─'*75}")
    
    print("\n" + "="*80)


def main():
    start_time = time.time()
    
    print("="*80)
    print_colored("🚀 RÉCUPÉRATION COMPLÈTE DES VERSIONS COCKROACHDB", Colors.BOLD + Colors.CYAN)
    print("="*80)
    print()
    
    try:
        print_colored("📡 Connexion à la page principale des releases...", Colors.CYAN)
        response = requests.get("https://www.cockroachlabs.com/docs/releases/", headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        minor_releases = extract_minor_releases_from_main_page(soup)
        
        if not minor_releases:
            print_colored("\n❌ Aucune version trouvée.", Colors.RED)
            return
        
        versions_hierarchy = build_version_hierarchy(minor_releases)
        
        total_major = len(versions_hierarchy)
        total_minor = sum(len(v['minor_releases']) for v in versions_hierarchy.values())
        total_patches = sum(
            minor['total_patches']
            for major in versions_hierarchy.values()
            for minor in major['minor_releases'].values()
        )
        
        sorted_majors = sorted(versions_hierarchy.keys(), key=lambda x: int(x), reverse=True)
        
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
            'versions_hierarchy': versions_hierarchy,
            'statistics': {
                'total_major_versions': total_major,
                'total_minor_releases': total_minor,
                'total_patches': total_patches,
                'major_versions_list': sorted_majors
            },
            'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        # --- MODIFICATION POUR FORCER LE CHEMIN ---
        target_dir = r"D:\Projet VT\Cockroachdb"
        
        # Créer le dossier s'il n'existe pas
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir)
                print(f"📁 Dossier créé : {target_dir}")
            except Exception as e:
                print_colored(f"⚠️ Impossible de créer le dossier, sauvegarde locale. Erreur: {e}", Colors.YELLOW)
                target_dir = "."

        output_file = os.path.join(target_dir, 'cockroachdb_versions.json')
        # ------------------------------------------

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=4, ensure_ascii=False)
        
        elapsed = time.time() - start_time
        
        print("\n" + "="*80)
        print_colored(f"✅ RÉCUPÉRATION TERMINÉE EN {elapsed:.1f}s", Colors.BOLD + Colors.GREEN)
        print("="*80)
        print(f"\n📦 Données sauvegardées dans: {output_file}")
        print(f"\n📈 STATISTIQUES GLOBALES:")
        print(f"   🎯 Versions majeures         : {total_major}")
        print(f"   📦 Releases trimestrielles   : {total_minor}")
        print(f"   🔧 Patches individuels       : {total_patches}")
        
        print_statistics_summary(versions_hierarchy)
        print_full_hierarchy(versions_hierarchy)
        
    except Exception as e:
        print_colored(f"\n❌ ERREUR CRITIQUE: {e}", Colors.RED)
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
    