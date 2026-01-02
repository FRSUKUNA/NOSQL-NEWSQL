#!/usr/bin/env python3
"""
Script pour ajouter les fonctionnalités ACID/CONSISTENCY
directement dans chaque fichier JSON du dossier output.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

class AcidConsistencyAdder:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.backup_dir = Path("output_backup")
        
        self.acid_keywords = [
            'acid', 'consistency', 'atomic', 'isolation', 'durability',
            'transaction', 'commit', 'rollback', 'lock', 'concurrency',
            'serializable', 'repeatable_read', 'read_committed', 'read_uncommitted',
            'write_ahead_log', 'wal', 'mvcc', 'optimistic_locking',
            'pessimistic_locking', 'deadlock', 'two_phase_commit', '2pc',
            'causal_consistency', 'eventual_consistency', 'strong_consistency',
            'linearizability', 'serializability', 'isolation_level',
            'atomicity', 'consistency_check', 'data_integrity', 'foreign_key',
            'referential_integrity', 'constraint', 'unique_constraint',
            'not_null', 'check_constraint', 'domain_integrity'
        ]
    
    def is_acid_related(self, text: str) -> bool:
        """Vérifie si le texte contient des mots-clés ACID/CONSISTENCY"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.acid_keywords)
    
    def extract_acid_features_from_changes(self, changes: List[str]) -> List[Dict]:
        """Extrait les fonctionnalités ACID de la liste des changements"""
        acid_features = []
        for change in changes:
            if self.is_acid_related(change):
                acid_features.append({
                    "description": change,
                    "source": "changes"
                })
        return acid_features
    
    def extract_acid_features_from_ai_analysis(self, ai_analysis: Dict) -> List[Dict]:
        """Extrait les fonctionnalités ACID de l'analyse IA"""
        acid_features = []
        if 'details' in ai_analysis:
            for detail in ai_analysis['details']:
                if self.is_acid_related(detail['description']):
                    acid_features.append({
                        "description": detail['description'],
                        "category": detail.get('category', 'unknown'),
                        "source": "ai_analysis"
                    })
        return acid_features
    
    def process_version_data(self, version_data: Dict) -> Dict:
        """Traite les données d'une version pour ajouter les fonctionnalités ACID"""
        modified_data = version_data.copy()
        
        # Extraire les fonctionnalités ACID
        acid_features = []
        
        # Depuis les changements
        if 'changes' in version_data:
            acid_features.extend(self.extract_acid_features_from_changes(version_data['changes']))
        
        # Depuis l'analyse IA
        if 'ai_analysis' in version_data:
            acid_features.extend(self.extract_acid_features_from_ai_analysis(version_data['ai_analysis']))
        
        # Ajouter la section acid_consistency_features
        modified_data['acid_consistency_features'] = {
            "total_count": len(acid_features),
            "features": acid_features,
            "extraction_date": datetime.now().isoformat()
        }
        
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
                    
                    acid_count = modified_version['acid_consistency_features']['total_count']
                    if acid_count > 0:
                        print(f"  {version_data.get('patch_version', version_data.get('major_version', 'unknown'))}: {acid_count} fonctionnalités ACID")
            
            # Sauvegarder les modifications
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Fichier modifié: {file_path.name}")
                return True
            else:
                print(f"ℹ️  Aucune modification nécessaire: {file_path.name}")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors du traitement du fichier {file_path}: {e}")
            return False
    
    def process_all_files(self):
        """Traite tous les fichiers JSON du dossier output"""
        if not self.output_dir.exists():
            print(f"Le dossier {self.output_dir} n'existe pas.")
            return
        
        json_files = list(self.output_dir.glob("*.json"))
        if not json_files:
            print("Aucun fichier JSON trouvé dans le dossier output.")
            return
        
        print(f"Traitement de {len(json_files)} fichiers JSON...")
        print("=" * 60)
        
        # Créer une sauvegarde
        self.backup_output_directory()
        
        total_files_modified = 0
        total_acid_features = 0
        
        for file_path in json_files:
            print(f"\n📁 Traitement de: {file_path.name}")
            if self.process_json_file(file_path):
                total_files_modified += 1
                
                # Compter les fonctionnalités ACID dans ce fichier
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for version_data in data:
                        if 'acid_consistency_features' in version_data:
                            total_acid_features += version_data['acid_consistency_features']['total_count']
                except:
                    pass
        
        print("\n" + "=" * 60)
        print("RÉSUMÉ DU TRAITEMENT")
        print("=" * 60)
        print(f"Fichiers traités: {len(json_files)}")
        print(f"Fichiers modifiés: {total_files_modified}")
        print(f"Total fonctionnalités ACID ajoutées: {total_acid_features}")
        print(f"Sauvegarde disponible dans: {self.backup_dir}")
        
        if total_files_modified > 0:
            print("\n✅ Tous les fichiers ont été mis à jour avec les fonctionnalités ACID/CONSISTENCY!")
        else:
            print("\nℹ️  Aucune modification n'était nécessaire.")

def main():
    """Fonction principale"""
    print("🔧 Ajout des fonctionnalités ACID/CONSISTENCY dans les fichiers JSON")
    print("Ce script va modifier directement les fichiers dans le dossier 'output'")
    print("=" * 70)
    
    # Demander confirmation
    response = input("\nVoulez-vous continuer? (y/N): ").strip().lower()
    if response not in ['y', 'yes', 'oui', 'o']:
        print("Opération annulée.")
        return
    
    adder = AcidConsistencyAdder()
    adder.process_all_files()

if __name__ == "__main__":
    main()
