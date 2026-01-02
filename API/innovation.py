#!/usr/bin/env python3
"""
Script pour générer des synthèses automatiques sur les innovations
(vector search, memory acceleration, etc.) basées sur les changements.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import re

class InnovationSummaryGenerator:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.backup_dir = Path("output_backup_innovations")
        
        # Catégories d'innovations avec mots-clés
        self.innovation_categories = {
            "vector_search": {
                "keywords": [
                    'vector', 'embedding', 'similarity', 'nearest neighbor', 'ann', 'approximate nearest',
                    'vector search', 'vector index', 'vector similarity', 'embedding search',
                    'faiss', 'hnsw', 'lsh', 'ivf', 'pq', 'product quantization',
                    'semantic search', 'vector database', 'vector storage', 'vector operations',
                    'dot product', 'cosine similarity', 'euclidean distance', 'manhattan distance',
                    'vector indexing', 'vector query', 'vector filter', 'vector aggregation',
                    'vector index type', 'vector distance', 'vector function', 'vector operator',
                    'vector storage engine', 'vector compression', 'vector encoding', 'vector decoding',
                    'vector normalization', 'vector quantization', 'vector clustering', 'vector partitioning'
                ],
                "description": "Recherche vectorielle et similarité sémantique",
                "examples": ["Vector indexing", "Embedding similarity search", "ANN algorithms"]
            },
            "memory_acceleration": {
                "keywords": [
                    'memory', 'cache', 'acceleration', 'ram', 'buffer', 'pool', 'allocation',
                    'memory optimization', 'memory management', 'memory pool', 'memory cache',
                    'in-memory', 'memory-mapped', 'mmap', 'shared memory', 'memory mapping',
                    'garbage collection', 'gc', 'heap', 'stack', 'memory leak', 'memory footprint',
                    'memory compression', 'memory deduplication', 'memory prefetching',
                    'tlb', 'translation lookaside buffer', 'memory hierarchy', 'memory bandwidth',
                    'memory allocator', 'memory arena', 'memory region', 'memory segment',
                    'memory controller', 'memory channel', 'memory bank', 'memory tier',
                    'memory tiering', 'memory hotness', 'memory cooling', 'memory eviction',
                    'memory reclamation', 'memory recycling', 'memory pooling', 'memory caching',
                    'fast memory', 'slow memory', 'persistent memory', 'non-volatile memory'
                ],
                "description": "Accélération mémoire et optimisation cache",
                "examples": ["Memory pool optimization", "Cache acceleration", "Memory-mapped files"]
            },
            "ai_ml_integration": {
                "keywords": [
                    'ai', 'ml', 'machine learning', 'artificial intelligence', 'neural network',
                    'deep learning', 'model', 'inference', 'training', 'prediction',
                    'tensorflow', 'pytorch', 'onnx', 'model serving', 'ml pipeline',
                    'feature store', 'model registry', 'automl', 'mlops', 'model deployment',
                    'gpu', 'cuda', 'tensor', 'vectorization', 'batch processing', 'distributed training'
                ],
                "description": "Intégration IA/ML et machine learning",
                "examples": ["ML model integration", "AI-powered features", "Neural network inference"]
            },
            "distributed_computing": {
                "keywords": [
                    'distributed', 'cluster', 'shard', 'partition', 'replica', 'consensus',
                    'raft', 'paxos', 'gossip', 'leader election', 'load balancing',
                    'horizontal scaling', 'vertical scaling', 'elastic scaling', 'auto-scaling',
                    'microservices', 'service mesh', 'kubernetes', 'docker', 'container',
                    'parallel processing', 'concurrent', 'async', 'event-driven', 'stream processing'
                ],
                "description": "Calcul distribué et scalabilité",
                "examples": ["Distributed consensus", "Horizontal scaling", "Load balancing"]
            },
            "quantum_computing": {
                "keywords": [
                    'quantum', 'qubit', 'quantum computing', 'quantum algorithm', 'quantum circuit',
                    'quantum gate', 'quantum entanglement', 'quantum superposition',
                    'quantum annealing', 'quantum cryptography', 'quantum key distribution',
                    'quantum simulation', 'quantum optimization', 'quantum machine learning'
                ],
                "description": "Informatique quantique",
                "examples": ["Quantum algorithms", "Qubit operations", "Quantum cryptography"]
            },
            "blockchain_web3": {
                "keywords": [
                    'blockchain', 'web3', 'smart contract', 'decentralized', 'dapp', 'cryptocurrency',
                    'nft', 'token', 'wallet', 'consensus', 'proof of work', 'proof of stake',
                    'defi', 'dao', 'smart contract', 'ethereum', 'solidity', 'smart contract execution',
                    'distributed ledger', 'crypto', 'mining', 'staking', 'validation'
                ],
                "description": "Blockchain et technologies Web3",
                "examples": ["Smart contracts", "DeFi protocols", "NFT storage"]
            },
            "edge_computing": {
                "keywords": [
                    'edge', 'edge computing', 'iot', 'internet of things', 'edge device',
                    'fog computing', 'edge analytics', 'edge ai', 'edge inference',
                    'real-time processing', 'low latency', 'edge gateway', 'edge node',
                    'embedded systems', 'microcontroller', 'sensor', 'actuator', 'edge ml'
                ],
                "description": "Edge computing et IoT",
                "examples": ["Edge AI inference", "IoT data processing", "Real-time analytics"]
            },
            "security_privacy": {
                "keywords": [
                    'security', 'privacy', 'encryption', 'decryption', 'cryptography', 'zero-knowledge',
                    'homomorphic encryption', 'differential privacy', 'secure multi-party computation',
                    'privacy-preserving', 'anonymous', 'pseudonymous', 'confidential',
                    'access control', 'authentication', 'authorization', 'biometric', 'multi-factor',
                    'zero-trust', 'security by design', 'privacy by design'
                ],
                "description": "Sécurité avancée et protection de la vie privée",
                "examples": ["Zero-knowledge proofs", "Homomorphic encryption", "Privacy-preserving ML"]
            }
        }
    
    def detect_innovations(self, text: str) -> List[str]:
        """Détecte les catégories d'innovations dans un texte"""
        detected = []
        text_lower = text.lower()
        
        for category, config in self.innovation_categories.items():
            # Compter le nombre de mots-clés trouvés pour cette catégorie
            keyword_matches = 0
            matched_keywords = []
            
            for keyword in config["keywords"]:
                if keyword in text_lower:
                    keyword_matches += 1
                    matched_keywords.append(keyword)
            
            # Ajouter la catégorie seulement si on trouve au moins 2 mots-clés
            # ou 1 mot-clé très spécifique (plus de 3 caractères)
            if keyword_matches >= 2 or (keyword_matches >= 1 and any(len(kw) > 3 for kw in matched_keywords)):
                detected.append(category)
        
        return detected
    
    def extract_innovations_from_changes(self, changes: List[str]) -> List[Dict]:
        """Extrait les innovations des changements"""
        innovations = []
        for change in changes:
            detected_categories = self.detect_innovations(change)
            if detected_categories:
                innovations.append({
                    "description": change,
                    "categories": detected_categories,
                    "source": "changes"
                })
        return innovations
    
    def extract_innovations_from_ai_analysis(self, ai_analysis: Dict) -> List[Dict]:
        """Extrait les innovations de l'analyse IA"""
        innovations = []
        if 'details' in ai_analysis:
            for detail in ai_analysis['details']:
                detected_categories = self.detect_innovations(detail['description'])
                if detected_categories:
                    # Ne garder que les catégories détectées, pas les catégories "unknown"
                    original_category = detail.get('category', '')
                    if original_category.lower() != 'unknown':
                        category = original_category
                    else:
                        # Utiliser la première catégorie détectée comme catégorie principale
                        category = detected_categories[0]
                    
                    innovations.append({
                        "description": detail['description'],
                        "categories": detected_categories,
                        "category": category,
                        "source": "ai_analysis"
                    })
        return innovations
    
    def generate_innovation_summary(self, innovations: List[Dict]) -> Dict:
        """Génère une synthèse des innovations"""
        # Compter par catégorie
        category_counts = {}
        category_details = {}
        
        for innovation in innovations:
            for category in innovation['categories']:
                if category not in category_counts:
                    category_counts[category] = 0
                    category_details[category] = []
                
                category_counts[category] += 1
                
                # N'ajouter que les catégories valides (pas "unknown")
                innovation_category = innovation.get('category', '')
                if innovation_category.lower() != 'unknown':
                    category_details[category].append({
                        "description": innovation['description'],
                        "source": innovation['source'],
                        "category": innovation_category
                    })
                else:
                    # Si la catégorie est "unknown", utiliser la catégorie détectée
                    category_details[category].append({
                        "description": innovation['description'],
                        "source": innovation['source'],
                        "category": category
                    })
        
        # Générer la synthèse
        summary = {
            "total_innovations": len(innovations),
            "categories_detected": list(category_counts.keys()),
            "category_counts": category_counts,
            "category_details": category_details,
            "innovation_trends": self.analyze_trends(innovations),
            "top_innovations": self.get_top_innovations(innovations),
            "generation_date": datetime.now().isoformat()
        }
        
        return summary
    
    def analyze_trends(self, innovations: List[Dict]) -> Dict:
        """Analyse les tendances d'innovation"""
        trends = {}
        
        # Tendances par catégorie
        category_frequency = {}
        for innovation in innovations:
            for category in innovation['categories']:
                if category not in category_frequency:
                    category_frequency[category] = 0
                category_frequency[category] += 1
        
        # Identifier les tendances émergentes
        total_innovations = len(innovations)
        emerging_trends = []
        established_trends = []
        
        for category, count in category_frequency.items():
            percentage = (count / total_innovations) * 100
            if percentage > 20:  # Plus de 20% = tendance établie
                established_trends.append({
                    "category": category,
                    "count": count,
                    "percentage": round(percentage, 2)
                })
            elif percentage > 5:  # 5-20% = tendance émergente
                emerging_trends.append({
                    "category": category,
                    "count": count,
                    "percentage": round(percentage, 2)
                })
        
        return {
            "established_trends": established_trends,
            "emerging_trends": emerging_trends,
            "category_frequency": category_frequency
        }
    
    def get_top_innovations(self, innovations: List[Dict]) -> List[Dict]:
        """Extrait les innovations les plus importantes"""
        # Trier par nombre de catégories (innovations multi-domaines)
        sorted_innovations = sorted(
            innovations, 
            key=lambda x: len(x['categories']), 
            reverse=True
        )
        
        # Prendre les 10 meilleures
        return sorted_innovations[:10]
    
    def process_version_data(self, version_data: Dict) -> Dict:
        """Traite les données d'une version pour ajouter les innovations"""
        modified_data = version_data.copy()
        
        # Extraire les innovations
        innovations = []
        
        # Depuis les changements
        if 'changes' in version_data:
            innovations.extend(self.extract_innovations_from_changes(version_data['changes']))
        
        # Depuis l'analyse IA
        if 'ai_analysis' in version_data:
            innovations.extend(self.extract_innovations_from_ai_analysis(version_data['ai_analysis']))
        
        # Générer la synthèse
        innovation_summary = self.generate_innovation_summary(innovations)
        
        # Ajouter la section innovation_summary
        modified_data['innovation_summary'] = innovation_summary
        
        return modified_data
    
    def backup_output_directory(self):
        """Crée une sauvegarde du dossier output"""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        shutil.copytree(self.output_dir, self.backup_dir)
        print(f"Sauvegarde créée dans: {self.backup_dir}")
    
    def process_json_file(self, file_path: Path) -> bool:
        """Traite un fichier JSON individuel"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, list):
                print(f"Le fichier {file_path.name} ne contient pas une liste")
                return False
            
            modified = False
            for i, version_data in enumerate(data):
                if 'database' not in version_data:
                    continue
                
                # Traiter les données de la version
                modified_version = self.process_version_data(version_data)
                
                # Vérifier si des modifications ont été apportées
                if modified_version != version_data:
                    data[i] = modified_version
                    modified = True
                    
                    innovation_count = modified_version['innovation_summary']['total_innovations']
                    categories_count = len(modified_version['innovation_summary']['categories_detected'])
                    
                    if innovation_count > 0:
                        version_name = version_data.get('patch_version', version_data.get('major_version', 'unknown'))
                        print(f"  {version_name}: {innovation_count} innovations dans {categories_count} catégories")
                        
                        # Afficher les catégories principales
                        top_categories = sorted(
                            modified_version['innovation_summary']['category_counts'].items(),
                            key=lambda x: x[1],
                            reverse=True
                        )[:3]
                        
                        for cat, count in top_categories:
                            print(f"    🚀 {cat}: {count}")
            
            # Sauvegarder les modifications
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Fichier modifié: {file_path.name}")
                return True
            else:
                print(f"ℹ️  Aucune innovation détectée: {file_path.name}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement du fichier {file_path}: {e}")
            return False
    
    def generate_global_summary(self):
        """Génère une synthèse globale de toutes les innovations"""
        print("\n🌍 GÉNÉRATION DE LA SYNTHÈSE GLOBALE...")
        
        all_innovations = []
        database_summaries = {}
        
        # Parcourir tous les fichiers
        for file_path in self.output_dir.glob("*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                db_name = None
                for version_data in data:
                    if 'database' in version_data:
                        db_name = version_data['database']
                        break
                
                if db_name and 'innovation_summary' in version_data:
                    summary = version_data['innovation_summary']
                    database_summaries[db_name] = summary
                    all_innovations.extend(summary['category_details'].get('all', []))
                    
            except Exception as e:
                print(f"Erreur lors de la lecture de {file_path}: {e}")
        
        # Générer la synthèse globale
        global_summary = {
            "generation_date": datetime.now().isoformat(),
            "total_databases": len(database_summaries),
            "database_summaries": database_summaries,
            "global_trends": self.analyze_global_trends(database_summaries),
            "innovation_matrix": self.create_innovation_matrix(database_summaries)
        }
        
        # Sauvegarder la synthèse globale
        with open("global_innovation_summary.json", "w", encoding="utf-8") as f:
            json.dump(global_summary, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Synthèse globale sauvegardée dans: global_innovation_summary.json")
        
        # Afficher un résumé
        self.print_global_summary(global_summary)
    
    def analyze_global_trends(self, database_summaries: Dict) -> Dict:
        """Analyse les tendances globales"""
        global_category_counts = {}
        
        for db_name, summary in database_summaries.items():
            for category, count in summary['category_counts'].items():
                if category not in global_category_counts:
                    global_category_counts[category] = {"total": 0, "databases": []}
                
                global_category_counts[category]["total"] += count
                global_category_counts[category]["databases"].append(db_name)
        
        return global_category_counts
    
    def create_innovation_matrix(self, database_summaries: Dict) -> Dict:
        """Crée une matrice d'innovations par base de données"""
        matrix = {}
        
        for db_name, summary in database_summaries.items():
            matrix[db_name] = summary['category_counts']
        
        return matrix
    
    def print_global_summary(self, global_summary: Dict):
        """Affiche la synthèse globale"""
        print("\n" + "=" * 80)
        print("🌍 SYNTHÈSE GLOBALE DES INNOVATIONS")
        print("=" * 80)
        
        print(f"\n📊 Statistiques générales:")
        print(f"  Bases de données analysées: {global_summary['total_databases']}")
        
        print(f"\n🚀 Tendances globales:")
        trends = global_summary['global_trends']
        sorted_trends = sorted(trends.items(), key=lambda x: x[1]['total'], reverse=True)
        
        for category, data in sorted_trends[:10]:
            print(f"  {category}: {data['total']} innovations dans {len(data['databases'])} bases de données")
    
    def test_innovation_detection(self):
        """Teste la détection d'innovations"""
        print("\n🧪 TEST DE DÉTECTION D'INNOVATIONS")
        print("=" * 50)
        
        test_cases = [
            {
                "text": "Add vector index support for similarity search using HNSW algorithm",
                "expected_categories": ["vector_search"]
            },
            {
                "text": "Optimize memory pool allocation and reduce memory footprint",
                "expected_categories": ["memory_acceleration"]
            },
            {
                "text": "Implement garbage collection optimization and memory caching",
                "expected_categories": ["memory_acceleration"]
            },
            {
                "text": "Add embedding similarity search with cosine distance",
                "expected_categories": ["vector_search"]
            },
            {
                "text": "Fix minor bug in user interface",
                "expected_categories": []
            },
            {
                "text": "Memory-mapped file implementation for faster data access",
                "expected_categories": ["memory_acceleration"]
            }
        ]
        
        for i, test_case in enumerate(test_cases, 1):
            detected = self.detect_innovations(test_case["text"])
            expected = test_case["expected_categories"]
            
            print(f"\nTest {i}: {test_case['text'][:50]}...")
            print(f"  Attendu: {expected}")
            print(f"  Détecté: {detected}")
            
            # Vérifier si les catégories attendues sont détectées
            success = all(cat in detected for cat in expected)
            # Vérifier si aucune catégorie non désirée n'est détectée
            extra_categories = set(detected) - set(expected)
            
            if success and not extra_categories:
                print("  ✅ Succès")
            else:
                print("  ❌ Échec")
                if extra_categories:
                    print(f"    Catégories supplémentaires: {extra_categories}")
    
    def process_all_files(self):
        """Traite tous les fichiers JSON du dossier output"""
        if not self.output_dir.exists():
            print(f"Le dossier {self.output_dir} n'existe pas.")
            return
        
        json_files = list(self.output_dir.glob("*.json"))
        if not json_files:
            print("Aucun fichier JSON trouvé dans le dossier output.")
            return
        
        print(f"🚀 Traitement de {len(json_files)} fichiers JSON pour détection d'innovations...")
        print("=" * 80)
        
        # Créer une sauvegarde
        self.backup_output_directory()
        
        total_files_modified = 0
        total_innovations = 0
        
        for file_path in json_files:
            print(f"\n📁 Traitement de: {file_path.name}")
            if self.process_json_file(file_path):
                total_files_modified += 1
                
                # Compter les innovations dans ce fichier
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for version_data in data:
                        if 'innovation_summary' in version_data:
                            total_innovations += version_data['innovation_summary']['total_innovations']
                except:
                    pass
        
        print("\n" + "=" * 80)
        print("🚀 RÉSUMÉ DES INNOVATIONS")
        print("=" * 80)
        print(f"Fichiers traités: {len(json_files)}")
        print(f"Fichiers avec innovations: {total_files_modified}")
        print(f"Total innovations détectées: {total_innovations}")
        print(f"Sauvegarde disponible dans: {self.backup_dir}")
        
        if total_files_modified > 0:
            print("\n✅ Tous les fichiers ont été mis à jour avec les synthèses d'innovations!")
            # Générer la synthèse globale
            self.generate_global_summary()
        else:
            print("\nℹ️  Aucune innovation détectée dans les fichiers.")

def main():
    """Fonction principale"""
    print("🚀 Génération de synthèses automatiques sur les innovations")
    print("Ce script va modifier directement les fichiers dans le dossier 'output'")
    print("🔍 Détection automatique des innovations: vector search, memory acceleration, AI/ML, etc.")
    print("=" * 80)
    
    # Demander si l'utilisateur veut tester d'abord
    test_response = input("\nVoulez-vous tester la détection d'innovations d'abord? (y/N): ").strip().lower()
    if test_response in ['y', 'yes', 'oui', 'o']:
        generator = InnovationSummaryGenerator()
        generator.test_innovation_detection()
        
        # Demander confirmation pour continuer
        continue_response = input("\nVoulez-vous continuer avec le traitement des fichiers? (y/N): ").strip().lower()
        if continue_response not in ['y', 'yes', 'oui', 'o']:
            print("Opération annulée.")
            return
    
    # Demander confirmation pour le traitement principal
    response = input("\nVoulez-vous continuer avec le traitement des fichiers? (y/N): ").strip().lower()
    if response not in ['y', 'yes', 'oui', 'o']:
        print("Opération annulée.")
        return
    
    generator = InnovationSummaryGenerator()
    generator.process_all_files()

if __name__ == "__main__":
    main()
