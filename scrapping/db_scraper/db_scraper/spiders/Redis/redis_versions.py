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

def get_acid_properties() -> Dict[str, str]:
    """Récupère les propriétés ACID/consistency de Redis depuis la documentation officielle."""
    print("Récupération des propriétés ACID/consistency de Redis...")
    
    url = "https://redis.io/glossary/acid-transactions/"
    acid_properties = {
        'atomicity': '',
        'consistency': '',
        'isolation': '',
        'durability': ''
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Trouver les sections ACID dans la page
        for h3 in soup.find_all('h3'):
            text = h3.get_text().lower()
            if 'atomicity' in text:
                acid_properties['atomicity'] = h3.find_next('p').get_text(strip=True)
            elif 'consistency' in text:
                acid_properties['consistency'] = h3.find_next('p').get_text(strip=True)
            elif 'isolation' in text:
                acid_properties['isolation'] = h3.find_next('p').get_text(strip=True)
            elif 'durability' in text:
                acid_properties['durability'] = h3.find_next('p').get_text(strip=True)
        
        print("Propriétés ACID récupérées avec succès")
        
    except Exception as e:
        print(f"Erreur lors de la récupération des propriétés ACID: {str(e)}")
    
    return acid_properties

def get_redis_versions() -> List[dict]:
    print("Récupération des versions de Redis...")
    
    versions: List[dict] = []
    
    # 1) Tentative via API GitHub Releases (paginée)
    try:
        per_page = 100
        page = 1
        print("Tentative via l'API GitHub Releases (avec pagination)...")
        while True:
            api_url = f"https://api.github.com/repos/redis/redis/releases?per_page={per_page}&page={page}"
            resp = requests.get(api_url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break

            for rel in data:
                # Ignorer les préversions et brouillons
                if rel.get('draft') or rel.get('prerelease'):
                    continue
                tag = rel.get('tag_name', '').lstrip('v')
                if not tag:
                    continue

                parts = tag.split('.')
                if not all(p.isdigit() for p in parts):
                    continue

                date_str = rel.get('published_at') or rel.get('created_at')
                if date_str:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                else:
                    formatted_date = "Date non disponible"

                versions.append({
                    'version': parts[0],
                    'patch': '.'.join(parts[1:]) if len(parts) > 1 else '0',
                    'date': formatted_date,
                    'url': f"https://github.com/redis/redis/releases/tag/v{tag}",
                    'download_url': f"https://download.redis.io/releases/redis-{tag}.tar.gz"
                })
                print(f"Trouvé: {tag} - {formatted_date}")

            page += 1
            time.sleep(0.5)

        if versions:
            return versions
    except Exception as e:
        print(f"API GitHub indisponible, bascule vers scraping HTML: {e}")

    # 2) Fallback: scraping HTML des pages Releases
    try:
        base_url = "https://github.com/redis/redis/releases"
        page = 1
        while True:
            url = f"{base_url}?page={page}"
            print(f"Récupération de la page {page} (fallback HTML)...")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Cartes de release (structure moderne GitHub)
            cards = soup.select('div[data-test-selector="release-card"]')
            if not cards:
                # Essayer des sélecteurs alternatifs
                cards = soup.select('div.release-entry, div.Box')

            if not cards:
                break

            for card in cards:
                try:
                    link = card.select_one('a[href*="/redis/redis/releases/tag/"]')
                    if not link:
                        # chercher globalement si non trouvé dans la carte
                        link = soup.select_one('a[href*="/redis/redis/releases/tag/"]')
                    if not link:
                        continue
                    tag_text = (link.text or '').strip().lstrip('v')
                    if not tag_text:
                        # parfois le texte n'est pas le tag: le tag est dans l'URL
                        href = link.get('href', '')
                        m = re.search(r'/releases/tag/v(\d+(?:\.\d+){1,2})', href)
                        if m:
                            tag_text = m.group(1)
                    parts = tag_text.split('.') if tag_text else []
                    if not parts or not all(p.isdigit() for p in parts):
                        continue

                    # date
                    time_el = card.select_one('relative-time, time-ago, time')
                    if time_el and time_el.has_attr('datetime'):
                        d = time_el['datetime']
                        date_obj = datetime.strptime(d, '%Y-%m-%dT%H:%M:%SZ')
                        formatted_date = date_obj.strftime('%Y-%m-%d')
                    else:
                        formatted_date = "Date non disponible"

                    versions.append({
                        'version': parts[0],
                        'patch': '.'.join(parts[1:]) if len(parts) > 1 else '0',
                        'date': formatted_date,
                        'url': f"https://github.com/redis/redis/releases/tag/v{tag_text}",
                        'download_url': f"https://download.redis.io/releases/redis-{tag_text}.tar.gz"
                    })
                    print(f"Trouvé: {tag_text} - {formatted_date}")
                except Exception as e:
                    print(f"Erreur lors du parsing d'une carte release: {e}")
                    continue

            # pagination
            next_link = soup.select_one('a.next_page, a[rel="next"]')
            if not next_link or 'disabled' in (next_link.get('class') or []):
                break
            page += 1
            time.sleep(1)
    except Exception as e:
        print(f"Erreur lors du fallback HTML: {e}")

    return versions
    
def main():
    # Récupérer les propriétés ACID/consistency
    acid_properties = get_acid_properties()
    
    # Récupérer les versions
    versions = get_redis_versions()
    
    if not versions:
        print("Aucune version trouvée.")
        return
    
    # Trier par version complète (ex: 7.4.1 > 7.4.0 > 7.3.9)
    def parse_version(vd: dict) -> List[int]:
        full = f"{vd['version']}.{vd['patch']}" if vd.get('patch') else vd['version']
        return [int(p) for p in full.split('.')]
    versions.sort(key=parse_version, reverse=True)
    
    # Préparer les données à sauvegarder
    output_data = {
        'acid_properties': acid_properties,
        'versions': versions,
        'last_updated': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    }
    
    # Sauvegarder dans un fichier JSON
    output_file = 'redis_versions.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    
    print(f"\n{len(versions)} versions trouvées et sauvegardées dans {output_file}")
    print("\nPropriétés ACID/consistency récupérées:")
    for prop, value in acid_properties.items():
        print(f"- {prop.capitalize()}: {value[:100]}..." if len(value) > 100 else f"- {prop.capitalize()}: {value}")
    
    print("\nAperçu des versions :")
    for i, ver in enumerate(versions[:5], 1):
        print(f"{i}. Version: {ver['version']}.{ver['patch']} (Maj: {ver['version']}, Patch: {ver['patch']}) - {ver['date']}")
    if len(versions) > 5:
        print(f"... et {len(versions) - 5} versions supplémentaires")

if __name__ == "__main__":
    main()
