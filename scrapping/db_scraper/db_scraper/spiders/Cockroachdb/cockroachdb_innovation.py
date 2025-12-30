import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import re
import time
import os

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def extract_bug_fixes_operational_changes(soup: BeautifulSoup) -> dict:
    """
    Extrait UNIQUEMENT les paragraphes qui commencent par:
    - "Fixed a bug..."
    - "Updated TTL job..."
    - "Previously..."
    - Autres patterns similaires
    """
    results = {
        'bug_fixes': [],
        'operational_changes': []
    }
    
    try:
        # Trouver toutes les sections Bug Fixes et Operational Changes
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5'])
        
        for heading in headings:
            heading_text = heading.get_text(strip=True).lower()
            
            # Section Bug Fixes
            if any(pattern in heading_text for pattern in ['bug fix', 'bug fixes', 'bugs fixed']):
                content = extract_paragraphs_after_heading(heading)
                results['bug_fixes'].extend(content)
            
            # Section Operational Changes
            elif any(pattern in heading_text for pattern in ['operational change', 'operational changes']):
                content = extract_paragraphs_after_heading(heading)
                results['operational_changes'].extend(content)
    
    except Exception as e:
        print(f"⚠️  Erreur extraction: {e}")
    
    return results


def extract_paragraphs_after_heading(heading) -> list:
    """
    Extrait TOUS les paragraphes après un titre jusqu'au prochain titre.
    Récupère uniquement le contenu brut, jamais les titres.
    """
    paragraphs = []
    current = heading.find_next_sibling()
    
    while current:
        # Arrêter si nouveau titre
        if current.name and current.name.startswith('h'):
            break
        
        # Extraire paragraphes
        if current.name == 'p':
            text = current.get_text(strip=True)
            if len(text) > 30:
                # Nettoyer
                text = re.sub(r'\s*#\d+\s*$', '', text)
                text = re.sub(r'\[#\d+\]', '', text)
                text = re.sub(r'\s+', ' ', text).strip()
                if text:
                    paragraphs.append(text)
        
        # Extraire listes
        elif current.name in ['ul', 'ol']:
            for li in current.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if len(text) > 30:
                    text = re.sub(r'\s*#\d+\s*$', '', text)
                    text = re.sub(r'\[#\d+\]', '', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        paragraphs.append(text)
        
        # Extraire divs avec contenu
        elif current.name == 'div':
            for p in current.find_all('p'):
                text = p.get_text(strip=True)
                if len(text) > 30:
                    text = re.sub(r'\s*#\d+\s*$', '', text)
                    text = re.sub(r'\[#\d+\]', '', text)
                    text = re.sub(r'\s+', ' ', text).strip()
                    if text:
                        paragraphs.append(text)
            
            for ul in current.find_all(['ul', 'ol']):
                for li in ul.find_all('li', recursive=False):
                    text = li.get_text(strip=True)
                    if len(text) > 30:
                        text = re.sub(r'\s*#\d+\s*$', '', text)
                        text = re.sub(r'\[#\d+\]', '', text)
                        text = re.sub(r'\s+', ' ', text).strip()
                        if text:
                            paragraphs.append(text)
        
        current = current.find_next_sibling()
    
    return paragraphs


def get_version_data(version: str) -> dict:
    """Récupère les données pour une version spécifique."""
    try:
        url = f"https://www.cockroachlabs.com/docs/releases/v{version}"
        print(f"\n{'='*80}")
        print(f"📦 VERSION v{version}")
        print(f"{'='*80}")
        print(f"🔗 URL: {url}")
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 404:
            print(f"⚠️  Page non trouvée")
            return None
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        content = soup.find('article') or soup.find('main') or soup.find('div', class_='markdown-body')
        
        if not content:
            print(f"⚠️  Contenu non trouvé")
            return None
        
        # Extraire bug fixes et operational changes
        data = extract_bug_fixes_operational_changes(content)
        
        print(f"\n✅ Résultats:")
        print(f"   • Bug Fixes: {len(data['bug_fixes'])}")
        print(f"   • Operational Changes: {len(data['operational_changes'])}")
        
        # Afficher TOUS les bug fixes
        if data['bug_fixes']:
            print(f"\n{'─'*80}")
            print(f"🐛 BUG FIXES (Total: {len(data['bug_fixes'])})")
            print(f"{'─'*80}")
            for idx, fix in enumerate(data['bug_fixes'], 1):
                print(f"\n[{idx}] {fix}")
        
        # Afficher TOUS les operational changes
        if data['operational_changes']:
            print(f"\n{'─'*80}")
            print(f"⚙️  OPERATIONAL CHANGES (Total: {len(data['operational_changes'])})")
            print(f"{'─'*80}")
            for idx, change in enumerate(data['operational_changes'], 1):
                print(f"\n[{idx}] {change}")
        
        if not data['bug_fixes'] and not data['operational_changes']:
            print(f"\n⚠️  Aucun Bug Fix ou Operational Change trouvé")
        
        return {
            'version': version,
            'url': url,
            'bug_fixes': data['bug_fixes'],
            'operational_changes': data['operational_changes'],
            'total_bug_fixes': len(data['bug_fixes']),
            'total_operational_changes': len(data['operational_changes'])
        }
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None


def main():
    """Fonction principale."""
    print("\n" + "="*80)
    print("🚀 EXTRACTION DES BUG FIXES ET OPERATIONAL CHANGES - COCKROACHDB")
    print("="*80)
    
    target_dir = r"D:\Projet VT\Cockroachdb"
    input_file = os.path.join(target_dir, 'cockroachdb_versions.json')
    
    # Charger les versions
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            versions_data = json.load(f)
            
            versions_list = []
            if 'versions_hierarchy' in versions_data:
                print("📂 Chargement des versions depuis la hiérarchie...")
                hierarchy = versions_data['versions_hierarchy']
                for major in hierarchy.values():
                    for minor in major.get('minor_releases', {}).values():
                        versions_list.append(minor)
            elif 'versions' in versions_data:
                versions_list = versions_data['versions']
            
            versions = versions_list
    
    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {input_file}")
        print("📋 Exécutez d'abord cockroachdb_versions.py")
        return
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return
    
    if not versions:
        print("❌ Aucune version disponible")
        return
    
    # Trier les versions
    try:
        versions.sort(
            key=lambda x: [int(n) for n in x.get('full_version', '0.0').split('.') if n.isdigit()],
            reverse=True
        )
    except:
        pass
    
    print(f"\n📊 {len(versions)} versions à analyser")
    
    # Collecter les données
    all_data = []
    
    for idx, version_info in enumerate(versions, 1):
        version = version_info.get('full_version', version_info.get('version', 'Unknown'))
        
        print(f"\n[{idx}/{len(versions)}]", end=" ")
        
        data = get_version_data(version)
        
        if data:
            data['date'] = version_info.get('date', 'Date non disponible')
            data['release_type'] = version_info.get('release_type', 'N/A')
            all_data.append(data)
        
        time.sleep(1.5)  # Respecter le serveur
    
    # Sauvegarder le rapport
    output_file = os.path.join(target_dir, 'bug_fixes_operational_changes_report.json')
    
    report = {
        'database': 'CockroachDB',
        'report_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
        'total_versions': len(all_data),
        'total_bug_fixes': sum(v['total_bug_fixes'] for v in all_data),
        'total_operational_changes': sum(v['total_operational_changes'] for v in all_data),
        'versions': all_data
    }
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"✅ RAPPORT SAUVEGARDÉ")
        print(f"{'='*80}")
        print(f"📁 Fichier: {output_file}")
        print(f"\n📊 STATISTIQUES GLOBALES:")
        print(f"   • Versions analysées: {report['total_versions']}")
        print(f"   • Total Bug Fixes: {report['total_bug_fixes']}")
        print(f"   • Total Operational Changes: {report['total_operational_changes']}")
    
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
    
    # Afficher résumé par version
    print(f"\n{'='*80}")
    print("📋 RÉSUMÉ PAR VERSION")
    print(f"{'='*80}")
    
    for data in all_data:
        badge = "🟢" if 'LTS' in data.get('release_type', '') else "🔵"
        print(f"\n{badge} v{data['version']} - {data.get('release_type', 'N/A')} - {data.get('date', 'N/A')}")
        print(f"   • Bug Fixes: {data['total_bug_fixes']}")
        print(f"   • Operational Changes: {data['total_operational_changes']}")
    
    print(f"\n{'='*80}")
    print("✅ EXTRACTION TERMINÉE")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
