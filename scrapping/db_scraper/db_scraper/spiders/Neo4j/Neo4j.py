import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional
import re
import os

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_neo4j_release_notes() -> List[Dict]:
    """Récupère toutes les notes de version depuis le changelog GitHub Neo4j."""
    try:
        # URL du changelog GitHub Neo4j
        url = "https://github.com/neo4j/neo4j/wiki/Neo4j-2025-changelog/"
        print(f"Récupération des notes de version depuis {url}...")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Récupérer le contenu principal de la page wiki GitHub
        content = soup.find('div', class_='markdown-body') or soup.find('article') or soup.find('main')
        if not content:
            print("Contenu principal non trouvé")
            return []
        
        all_versions = []
        current_version = None
        current_changes = []
        
        # Pattern pour détecter les versions
        version_pattern = re.compile(r'(\d{4})\.(\d{2})\.(\d+)')
        
        # Parcourir tous les éléments
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'pre', 'div']):
            element_text = element.get_text(strip=True)
            
            # Vérifier si c'est une ligne de version
            version_match = version_pattern.match(element_text)
            if version_match:
                # Sauvegarder la version précédente si elle existe
                if current_version and current_changes:
                    all_versions.append(current_version)
                
                major = f"{version_match.group(1)}.{version_match.group(2)}"
                patch = version_match.group(3)
                print(f"Version trouvée: {major}.{patch}")
                
                # Créer la nouvelle version
                current_version = {
                    'major_version': major,
                    'patch_version': patch,
                    'date': "Date non disponible",
                    'changes': []
                }
                current_changes = []
            
            # Vérifier si c'est un changement
            elif current_version and element_text and len(element_text) > 10:
                # Nettoyer la ligne de changement
                if element_text.startswith(('* ', '- ', '• ')):
                    change = element_text[2:].strip() if element_text.startswith(('* ', '- ')) else element_text[1:].strip()
                else:
                    change = element_text
                
                # Vérifier si le changement contient des mots-clés significatifs
                if any(keyword in change.lower() for keyword in ['fix', 'add', 'improve', 'update', 'remove', 'change', 'support', 'new', 'optimize', 'enhance', 'enable']):
                    current_changes.append(change)
                    current_version['changes'] = current_changes.copy()
            
            # Traiter les listes spécialement
            elif current_version and element.name in ['ul', 'ol']:
                for li in element.find_all('li'):
                    li_text = li.get_text(strip=True)
                    if li_text and len(li_text) > 10:
                        # Nettoyer le texte
                        if li_text.startswith(('* ', '- ', '• ')):
                            change = li_text[2:].strip() if li_text.startswith(('* ', '- ')) else li_text[1:].strip()
                        else:
                            change = li_text
                        
                        # Vérifier si le changement contient des mots-clés significatifs
                        if any(keyword in change.lower() for keyword in ['fix', 'add', 'improve', 'update', 'remove', 'change', 'support', 'new', 'optimize', 'enhance', 'enable']):
                            current_changes.append(change)
                            current_version['changes'] = current_changes.copy()
        
        # Ajouter la dernière version
        if current_version and current_changes:
            all_versions.append(current_version)
        
        # Si aucune version trouvée avec le pattern principal, essayer une approche plus large
        if not all_versions:
            print("Recherche alternative des versions...")
            all_text = content.get_text()
            
            # Chercher toutes les mentions de versions dans tout le texte
            version_matches = version_pattern.findall(all_text)
            unique_versions = list(set(version_matches))
            unique_versions.sort(reverse=True)
            
            for version_tuple in unique_versions[:20]:
                major = f"{version_tuple[0]}.{version_tuple[1]}"
                patch = version_tuple[2]
                print(f"Version trouvée (alternative): {major}.{patch}")
                
                # Chercher les changements associés à cette version
                version_changes = []
                version_str = f"{major}.{patch}"
                lines = all_text.split('\n')
                
                for i, line in enumerate(lines):
                    if version_str in line:
                        # Ajouter les lignes suivantes
                        for j in range(i, min(len(lines), i + 10)):
                            context_line = lines[j].strip()
                            if context_line and len(context_line) > 10:
                                # Nettoyer la ligne
                                if context_line.startswith(('* ', '- ', '• ')):
                                    change = context_line[2:].strip() if context_line.startswith(('* ', '- ')) else context_line[1:].strip()
                                else:
                                    change = context_line
                                
                                # Vérifier si c'est un changement significatif
                                if any(keyword in change.lower() for keyword in ['fix', 'add', 'improve', 'update', 'remove', 'change', 'support', 'new', 'optimize', 'enhance', 'enable']):
                                    version_changes.append(change)
                
                all_versions.append({
                    'major_version': major,
                    'patch_version': patch,
                    'date': "Date non disponible",
                    'changes': version_changes
                })
        
        # Tenter d'extraire des dates des changements si disponibles
        for version in all_versions:
            dates_found = []
            for change in version['changes']:
                # Chercher des patterns de date
                date_patterns = [
                    r'(\d{4}-\d{2}-\d{2})',
                    r'(\d{1,2}/\d{1,2}/\d{4})',
                    r'(\w+ \d{1,2}, \d{4})',
                    r'(\w+ \d{4})'
                ]
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, change)
                    dates_found.extend(matches)
            
            if dates_found:
                version['date'] = dates_found[0]
        
        print(f"Total de versions trouvées: {len(all_versions)}")
        return all_versions
        
    except Exception as e:
        print(f"Erreur lors de la récupération des notes de version: {e}")
        return []

def generate_simplified_report() -> List[Dict]:
    """Génère un rapport au format simplifié demandé."""
    print("Début de l'analyse des changements Neo4j...")
    
    # Récupérer toutes les versions depuis le changelog
    all_versions = get_neo4j_release_notes()
    
    if not all_versions:
        print("Aucune version trouvée dans le changelog.")
        return []
    
    # Trier les versions par numéro de version (du plus récent au plus ancien)
    all_versions.sort(
        key=lambda x: [int(n) for n in (x['major_version'] + '.' + x['patch_version']).split('.')], 
        reverse=True
    )
    
    # Créer le format simplifié
    simplified_versions = []
    
    for version_info in all_versions:
        simplified_entry = {
            "database": "Neo4j",
            "major_version": version_info['major_version'],
            "patch_version": version_info['patch_version'],
            "date": version_info['date'],
            "changes": version_info['changes']
        }
        
        simplified_versions.append(simplified_entry)
        
        print(f"\nVersion {version_info['major_version']}.{version_info['patch_version']}:")
        print(f"  Date: {version_info['date']}")
        print(f"  Changements: {len(version_info['changes'])}")
    
    # Sauvegarder le rapport au format demandé
    output_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', 'API', 'sources', 'neo4j-versions.json'))
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(simplified_versions, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Rapport sauvegardé dans {output_file}")
    print(f"📊 Versions analysées: {len(simplified_versions)}")
    print(f"📝 Total de changements: {sum(len(v['changes']) for v in simplified_versions)}")

    return simplified_versions

def main():
    """Fonction principale pour exécuter l'analyse des changements."""
    print("=== Analyse des Changements Neo4j - Format Simplifié ===\n")

    # Générer le rapport simplifié
    report = generate_simplified_report()

    if not report:
        print("❌ Erreur: Aucune donnée disponible")
        return

    # Afficher un aperçu des premières versions
    print("\n=== Aperçu des 3 Premières Versions ===")
    for i, version_info in enumerate(report[:3], 1):
        print(f"\n{i}. Neo4j {version_info['major_version']}.{version_info['patch_version']} ({version_info['date']})")
        print(f"   Nombre de changements: {len(version_info['changes'])}")
        
        # Afficher les 3 premiers changements
        for j, change in enumerate(version_info['changes'][:3], 1):
            print(f"   {j}. {change[:100]}{'...' if len(change) > 100 else ''}")
        
        if len(version_info['changes']) > 3:
            print(f"   ... et {len(version_info['changes']) - 3} autres changements")

    print("\n✨ Analyse terminée avec succès!")

if __name__ == "__main__":
    main()