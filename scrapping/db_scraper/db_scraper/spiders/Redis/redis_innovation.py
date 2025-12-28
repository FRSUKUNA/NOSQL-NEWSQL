import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from typing import Dict, List, Optional

# Configuration des en-têtes pour les requêtes HTTP
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_page_content(url, page_type):
    """Récupère le contenu d'une page spécifique de la documentation Redis."""
    try:
        print(f"Récupération de la page: {url}")
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Récupérer le contenu principal de la page
        content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if not content:
            print(f"Contenu principal non trouvé pour {url}")
            return []
            
        # Extraire les sections pertinentes
        sections = []
        current_section = {'title': 'Introduction', 'content': []}
        
        for element in content.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'ul', 'ol', 'pre']):
            if element.name in ['h1', 'h2', 'h3', 'h4']:
                # Sauvegarder la section précédente
                if current_section['content']:
                    sections.append(current_section)
                # Commencer une nouvelle section
                current_section = {
                    'title': element.get_text(strip=True),
                    'content': []
                }
            else:
                # Ajouter le contenu à la section courante
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Ignorer les textes trop courts
                    current_section['content'].append(text)
        
        # Ajouter la dernière section
        if current_section['content']:
            sections.append(current_section)
            
        return sections
        
    except Exception as e:
        print(f"Erreur lors de la récupération de {url}: {str(e)}")
        return []

def extract_innovation_sections(sections, page_type):
    """Extrait les sections pertinentes en fonction du type de page."""
    innovations = {
        'vector_search': [],
        'memory_performance': [],
        'other_innovations': []
    }
    
    try:
        for section in sections:
            section_text = ' '.join(section['content'])
            section_lower = section_text.lower()
            
            # Pour la page Vector Search
            if page_type == 'vector':
                if any(keyword in section_lower for keyword in ['vector', 'embedding', 'similarity', 'semantic']):
                    innovations['vector_search'].extend([
                        f"{section['title']}: {text}"
                        for text in section['content']
                        if any(keyword in text.lower() for keyword in ['vector', 'embedding', 'similarity', 'semantic'])
                    ])
            
            # Pour la page Performance/Mémoire
            elif page_type == 'performance':
                if any(keyword in section_lower for keyword in ['memory', 'performance', 'optimization', 'speed']):
                    innovations['memory_performance'].extend([
                        f"{section['title']}: {text}"
                        for text in section['content']
                        if any(keyword in text.lower() for keyword in ['memory', 'performance', 'optimization', 'speed'])
                    ])
            
            # Autres sections intéressantes
            if 'feature' in section_lower or 'new' in section_lower or 'improvement' in section_lower:
                innovations['other_innovations'].extend([
                    f"{section['title']}: {text}"
                    for text in section['content']
                    if len(text) > 50
                ])
        
        return innovations
        
    except Exception as e:
        print(f"Erreur lors de l'extraction des sections: {str(e)}")
        return innovations

def analyze_innovations(innovations: Dict[str, List[str]]) -> Dict:
    """Analyse les innovations et génère une synthèse structurée."""
    def extract_key_points(texts: List[str], keywords: List[str]) -> List[str]:
        """Extrait les points clés pertinents des textes."""
        key_points = []
        for text in texts:
            # Simplification du texte pour l'analyse
            sentences = [s.strip() for s in text.split('.') if any(kw in s.lower() for kw in keywords)]
            key_points.extend(sentences)
        return list(set(key_points))[:5]  # Limiter à 5 points clés par catégorie
    
    vector_keywords = ['vector', 'embedding', 'similarity', 'search', 'nearest neighbor']
    memory_keywords = ['memory', 'performance', 'speed', 'optimization', 'efficiency', 'acceleration']
    
    return {
        'vector_search_innovations': {
            'description': 'Améliorations liées à la recherche vectorielle et aux embeddings',
            'key_points': extract_key_points(innovations['vector_search'], vector_keywords)
        },
        'memory_performance_innovations': {
            'description': 'Améliorations des performances et de la gestion de la mémoire',
            'key_points': extract_key_points(innovations['memory_performance'], memory_keywords)
        },
        'other_notable_features': {
            'description': 'Autres fonctionnalités notables',
            'features': list(set(innovations['other_innovations']))[:5]  # Limiter à 5 fonctionnalités
        }
    }

def generate_innovation_report() -> Dict:
    """Génère un rapport complet sur les innovations de Redis."""
    print("Début de l'analyse des pages de documentation Redis...")
    
    # URLs des pages à analyser
    pages = [
        {
            'url': 'https://redis.io/docs/latest/develop/ai/search-and-query/vectors/',
            'type': 'vector',
            'title': 'Redis Vector Search'
        },
        {
            'url': 'https://redis.io/docs/latest/operate/rs/databases/memory-performance/',
            'type': 'performance',
            'title': 'Redis Memory Performance'
        }
    ]
    
    try:
        # Préparer la structure pour les innovations
        all_innovations = {
            'vector_search': [],
            'memory_performance': [],
            'other_innovations': []
        }
        
        # Analyser chaque page
        for page in pages:
            print(f"\nAnalyse de la page: {page['title']}")
            
            # Récupérer le contenu de la page
            sections = get_page_content(page['url'], page['type'])
            
            if not sections:
                print(f"Aucune section trouvée pour {page['title']}")
                continue
            
            # Extraire les innovations de la page
            innovations = extract_innovation_sections(sections, page['type'])
            
            # Fusionner avec les résultats existants
            for key in all_innovations:
                all_innovations[key].extend(innovations[key])
        
        # Nettoyer les doublons
        for key in all_innovations:
            all_innovations[key] = list(set(all_innovations[key]))
        
        # Analyser les innovations trouvées
        analysis = analyze_innovations(all_innovations)
        
        # Création du rapport final
        report = {
            'report_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'pages_analyzed': [{'title': p['title'], 'url': p['url']} for p in pages],
            'analysis': analysis
        }
        
        # Sauvegarde du rapport
        output_file = 'redis_innovations_report.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4, ensure_ascii=False)
        
        print(f"\n✅ Rapport d'analyse des innovations sauvegardé dans {output_file}")
        return report
        
    except Exception as e:
        error_msg = f"Erreur lors de la génération du rapport: {str(e)}"
        print(error_msg)
        return {'error': error_msg}

def main():
    # Générer le rapport d'innovations
    report = generate_innovation_report()
    
    # Afficher un résumé dans la console
    if 'analysis' in report and 'error' not in report:
        print("\n=== SYNTHÈSE DES INNOVATIONS REDIS ===")
        
        # Afficher les pages analysées
        if 'pages_analyzed' in report and report['pages_analyzed']:
            print("\n📄 PAGES ANALYSÉES :")
            for i, page in enumerate(report['pages_analyzed'], 1):
                print(f"  {i}. {page['title']}")
                print(f"     {page['url']}")
        
        # Afficher les innovations Vector Search
        vector_points = report['analysis']['vector_search_innovations'].get('key_points', [])
        if vector_points:
            print("\n🔍 VECTOR SEARCH :")
            for i, point in enumerate(vector_points[:10], 1):  # Limiter à 10 points max
                print(f"  {i}. {point}")
        
        # Afficher les innovations Mémoire/Performance
        perf_points = report['analysis']['memory_performance_innovations'].get('key_points', [])
        if perf_points:
            print("\n⚡ MÉMOIRE & PERFORMANCE :")
            for i, point in enumerate(perf_points[:10], 1):  # Limiter à 10 points max
                print(f"  {i}. {point}")
        
        # Afficher d'autres fonctionnalités notables
        other_features = report['analysis']['other_notable_features'].get('features', [])
        if other_features:
            print("\n✨ AUTRES FONCTIONNALITÉS :")
            for i, feature in enumerate(other_features[:5], 1):  # Limiter à 5 fonctionnalités
                print(f"  {i}. {feature[:150]}..." if len(feature) > 150 else f"  {i}. {feature}")
        
        print("\n✅ Analyse terminée avec succès !")
    
    elif 'error' in report:
        print(f"\n❌ Erreur: {report['error']}")

if __name__ == "__main__":
    main()