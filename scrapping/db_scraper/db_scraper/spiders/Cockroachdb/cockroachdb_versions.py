import requests
from bs4 import BeautifulSoup, NavigableString
import re
import json
import time
from typing import Dict, List
import os

# --- Configuration ---
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# --- Couleurs pour le terminal ---
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
    print(f"{color}{text}{Colors.ENDC}", end=end)

# --- Fonctions d'extraction ---

def extract_minor_releases_from_main_page(soup: BeautifulSoup) -> List[Dict]:
    """Extrait les versions et s'assure que v26.1 est présente."""
    minor_releases = []
    seen_versions = set()
    
    print_colored("🔍 Extraction des versions majeures...", Colors.CYAN)
    
    # 1. Extraction dynamique standard
    version_links = soup.find_all('a', href=re.compile(r'/docs/releases/v\d+\.\d+'))
    
    for link in version_links:
        href = link.get('href', '')
        version_match = re.search(r'/docs/releases/v(\d+)\.(\d+)/?$', href)
        
        if version_match:
            major = version_match.group(1)
            minor = version_match.group(2)
            version_key = f"{major}.{minor}"
            
            if int(major) >= 19 and version_key not in seen_versions:
                seen_versions.add(version_key)
                minor_releases.append({
                    'major_version': version_key,
                    'url': f"https://www.cockroachlabs.com/docs/releases/v{version_key}"
                })

    # 2. AJOUT FORCÉ DE LA v26.1 (Si non trouvée dynamiquement)
    if "26.1" not in seen_versions:
        print_colored("➕ Ajout manuel de v26.1 (prioritaire)", Colors.YELLOW)
        minor_releases.append({
            'major_version': '26.1',
            'url': 'https://www.cockroachlabs.com/docs/releases/v26.1'
        })
        seen_versions.add("26.1")

    # 3. Tri décroissant
    minor_releases.sort(
        key=lambda x: [int(n) for n in x['major_version'].split('.')],
        reverse=True
    )
    
    # 4. LIMITATION AUX 7 DERNIÈRES VERSIONS
    top_releases = minor_releases[:7]
    
    print_colored(f"✅ Liste finale des {len(top_releases)} versions à scanner :", Colors.GREEN)
    for r in top_releases:
        print(f"   - v{r['major_version']}")
    print()
    
    return top_releases


def extract_patch_changelog(soup: BeautifulSoup, patch_version: str) -> List[str]:
    """
    Extrait le contenu entre le titre de la version et le suivant.
    """
    changes = []
    
    # Regex mise à jour pour accepter les suffixes (ex: -beta.1)
    # \b assure qu'on matche "26.1.0-beta.1" mais pas "26.1.0-beta.10" si on cherche le 1
    target_version_regex = re.compile(rf"v?{re.escape(patch_version)}\b", re.IGNORECASE)
    
    # Regex d'arrêt : Doit aussi reconnaître les versions avec beta/alpha pour s'arrêter correctement
    any_version_header_regex = re.compile(r'v?\d+\.\d+\.\d+(?:-[a-zA-Z0-9\.]+)?\b')

    # 1. Trouver le header de début
    start_header = None
    for header in soup.find_all(['h1', 'h2', 'h3', 'h4']):
        header_text = header.get_text(strip=True)
        if target_version_regex.search(header_text):
            if "archive" not in header_text.lower():
                start_header = header
                break

    if not start_header:
        return []

    # 2. Scan linéaire
    current_element = start_header.next_element

    while current_element:
        if isinstance(current_element, NavigableString):
            current_element = current_element.next_element
            continue

        # Condition d'arrêt
        if current_element.name in ['h1', 'h2', 'h3', 'h4']:
            header_text = current_element.get_text(strip=True)
            if any_version_header_regex.search(header_text):
                # Si ce n'est pas le titre de départ
                if header_text != start_header.get_text(strip=True):
                    break

        # Extraction des listes
        if current_element.name == 'li':
            if current_element.parent and current_element.parent.name in ['ul', 'ol']:
                text = current_element.get_text(strip=True)
                if text and len(text) > 10:
                     cleaned_text = re.sub(r'\s+', ' ', text).strip()
                     if cleaned_text not in changes:
                         changes.append(cleaned_text)

        current_element = current_element.next_element

    return changes


def extract_patches_with_changelog(version_url: str, major_version: str) -> List[Dict]:
    """Extrait tous les patches, y compris Alpha/Beta."""
    patches = []
    seen_patches = set()
    
    try:
        print(f"  🔎 Scanning {version_url}...", end=" ", flush=True)
        response = requests.get(version_url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            print_colored(" (404 Page non trouvée)", Colors.YELLOW, end="\n")
            return []
            
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        headings = soup.find_all(['h2', 'h3', 'h4'])
        
        for heading in headings:
            heading_text = heading.get_text(strip=True)
            
            # --- MODIFICATION MAJEURE ICI ---
            # Regex modifiée pour capturer : v26.1.0, v26.1.0-beta.1, v26.1.0-alpha.2
            # Structure : Chiffres + Optionnel (Tiret + Alphanumérique/Points)
            patch_match = re.search(r'v?(\d+\.\d+\.\d+(?:-[a-zA-Z0-9\.]+)?)\b', heading_text)
            
            if patch_match:
                patch_version = patch_match.group(1)
                
                # Vérification que ça appartient bien à la version majeure (ex: 26.1)
                if patch_version.startswith(major_version + ".") and patch_version not in seen_patches:
                    seen_patches.add(patch_version)
                    
                    # Date approximative
                    date = 'Date non disponible'
                    next_elem = heading.find_next(['p', 'div', 'span', 'em'])
                    if next_elem:
                        next_text = next_elem.get_text()
                        date_match = re.search(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,\s+\d{4})', next_text, re.IGNORECASE)
                        if date_match:
                            date = date_match.group(1).strip()

                    # Extraction du contenu
                    print(f"\n    -> Patch {patch_version}...", end="")
                    changes = extract_patch_changelog(soup, patch_version)
                    print(f" ({len(changes)} changements)", end="")
                    
                    patches.append({
                        'database': 'CockroachDB',
                        'major_version': major_version,
                        'patch_version': patch_version,
                        'date': date,
                        'changes': changes
                    })
        
        print()
        
        # Fonction de tri robuste pour gérer les "beta" et "alpha" sans planter
        def safe_sort_key(p):
            v_str = p['patch_version']
            # On essaie de splitter proprement pour le tri
            # Astuce: "beta" > "alpha" en string, donc le reverse sort mettra bien Beta avant Alpha
            return v_str
            
        # Tri alphabétique inverse (v26.1.0 > v26.1.0-beta > v26.1.0-alpha)
        # Ce n'est pas un tri sémantique parfait, mais suffisant pour grouper beta avant alpha
        patches.sort(key=lambda p: p['patch_version'], reverse=True)
        
        return patches
        
    except Exception as e:
        print_colored(f"  ❌ Erreur: {e}", Colors.RED)
        return []

# --- Main ---

def main():
    start_time = time.time()
    
    print("="*80)
    print_colored("🚀 SCRAPING COCKROACHDB (INCLUT ALPHA/BETA)", Colors.BOLD + Colors.CYAN)
    print("="*80)
    print()
    
    try:
        response = requests.get("https://www.cockroachlabs.com/docs/releases/", headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        target_releases = extract_minor_releases_from_main_page(soup)
        
        all_patches_result = []
        
        for i, release in enumerate(target_releases, 1):
            print_colored(f"[{i}/{len(target_releases)}] Branche v{release['major_version']}", Colors.CYAN)
            
            patches = extract_patches_with_changelog(release['url'], release['major_version'])
            
            if patches:
                all_patches_result.extend(patches)
            
            time.sleep(1)
            print("-" * 40)

        # Sauvegarde
        target_dir = r"c:\Users\Dell\VT\API\sources"
        if not os.path.exists(target_dir):
            try:
                os.makedirs(target_dir, exist_ok=True)
            except:
                target_dir = "."

        output_file = os.path.join(target_dir, 'cockroachdb-versions.json')

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_patches_result, f, indent=4, ensure_ascii=False)
        
        print("\n" + "="*80)
        print_colored(f"✅ TERMINÉ ! {len(all_patches_result)} patches sauvegardés.", Colors.BOLD + Colors.GREEN)
        print(f"📂 Fichier : {output_file}")
        
    except Exception as e:
        print_colored(f"\n❌ ERREUR GLOBALE: {e}", Colors.RED)

if __name__ == "__main__":
    main()
    