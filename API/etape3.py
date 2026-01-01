import json
from transformers import pipeline
from typing import List, Dict
import os

class ChangelogClassifier:
    def __init__(self):
        """Initialise le classificateur zero-shot"""
        print("🤖 Chargement du modèle de classification...")
        self.classifier = pipeline(
            "zero-shot-classification",
            model="valhalla/distilbart-mnli-12-1"
        )
        
        # Définir les catégories cibles
        self.categories = [
            "performance optimization",
            "bug fix",
            "security improvement",
            "new feature"
        ]
        
        # Seuil de confiance minimum pour la classification
        self.confidence_threshold = 0.4
        print("✅ Modèle chargé avec succès!\n")
        
    def classify_change(self, description: str) -> Dict:
        """
        Classifie une description de changement
        
        Args:
            description: La description du changement à classifier
            
        Returns:
            Dict contenant la catégorie et le score de confiance
        """
        # Exécuter la classification
        result = self.classifier(
            description,
            candidate_labels=self.categories,
            multi_label=False
        )
        
        # Récupérer la meilleure prédiction
        best_label = result['labels'][0]
        best_score = result['scores'][0]
        
        # Mapper vers les catégories finales
        category_mapping = {
            "performance optimization": "performance",
            "bug fix": "bug_fix",
            "security improvement": "security",
            "new feature": "new_feature"
        }
        
        # Si le score est trop faible, c'est hors sujet
        if best_score < self.confidence_threshold:
            return {
                "category": "hors_sujet",
                "confidence": best_score,
                "original_prediction": best_label
            }
        
        return {
            "category": category_mapping.get(best_label, "other"),
            "confidence": best_score,
            "original_prediction": best_label
        }
    
    def process_version(self, version_data: Dict, db_name: str, version: str) -> Dict:
        """
        Traite une version spécifique d'une base de données
        
        Args:
            version_data: Données d'une version
            db_name: Nom de la base de données
            version: Numéro de version
            
        Returns:
            Version mise à jour avec les nouvelles classifications
        """
        if 'ai_analysis' not in version_data or 'details' not in version_data['ai_analysis']:
            print(f"  ⚠️  Structure ai_analysis manquante pour {db_name} {version}")
            return version_data
        
        details = version_data['ai_analysis']['details']
        summary = version_data['ai_analysis']['summary']
        
        reclassified_count = 0
        other_count = sum(1 for item in details if item.get('category') == 'other')
        
        if other_count == 0:
            print(f"  ℹ️  Aucun élément 'other' à reclassifier")
            return version_data
        
        print(f"  🔍 Reclassification de {other_count} éléments 'other'...")
        
        # Parcourir tous les changements
        for item in details:
            # Ne reclassifier que les éléments marqués 'other'
            if item.get('category') == 'other':
                description = item.get('description', '')
                
                # Effectuer la classification
                result = self.classify_change(description)
                
                # Mise à jour de la catégorie
                old_category = item['category']
                new_category = result['category']
                
                item['category'] = new_category
                item['ai_confidence'] = result['confidence']
                item['ai_prediction'] = result['original_prediction']
                
                # Mettre à jour le résumé
                if old_category in summary:
                    summary[old_category] -= 1
                
                if new_category not in summary:
                    summary[new_category] = 0
                summary[new_category] += 1
                
                reclassified_count += 1
        
        # Recalculer le type dominant
        if summary:
            version_data['ai_analysis']['dominant_type'] = max(
                summary.items(), 
                key=lambda x: x[1]
            )[0]
        
        print(f"  ✅ {reclassified_count} éléments reclassifiés")
        print(f"  📊 Résumé: {summary}")
        
        return version_data
    
    def process_json_file(self, json_data: List[Dict]) -> List[Dict]:
        """
        Traite un fichier JSON contenant plusieurs versions de bases de données
        
        Args:
            json_data: Liste de versions de bases de données
            
        Returns:
            Liste mise à jour avec les nouvelles classifications
        """
        if not isinstance(json_data, list):
            print("  ⚠️  Format JSON inattendu (attendu: liste de versions)")
            return json_data
        
        total_versions = len(json_data)
        print(f"📦 {total_versions} version(s) trouvée(s) dans ce fichier\n")
        
        # Traiter chaque version
        for i, version_data in enumerate(json_data, 1):
            db_name = version_data.get('database', 'Unknown')
            version = version_data.get('patch_version', version_data.get('major_version', 'Unknown'))
            
            print(f"  [{i}/{total_versions}] 🗃️  {db_name} v{version}")
            
            json_data[i-1] = self.process_version(version_data, db_name, version)
            print()
        
        return json_data
    
    def process_file(self, input_path: str, output_path: str):
        """
        Traite un fichier JSON complet
        
        Args:
            input_path: Chemin du fichier JSON d'entrée
            output_path: Chemin du fichier JSON de sortie
        """
        # Charger le fichier JSON
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Traiter les données
        updated_data = self.process_json_file(data)
        
        # Sauvegarder le résultat
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(updated_data, f, indent=2, ensure_ascii=False)
        
        return updated_data


def process_directory(input_dir: str = "output", output_dir: str = "outputfinal"):
    """
    Traite tous les fichiers JSON d'un dossier
    
    Args:
        input_dir: Dossier contenant les fichiers JSON d'entrée
        output_dir: Dossier où sauvegarder les résultats
    """
    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Vérifier que le dossier d'entrée existe
    if not os.path.exists(input_dir):
        print(f"❌ Le dossier '{input_dir}' n'existe pas!")
        return
    
    # Lister tous les fichiers JSON
    json_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]
    
    if not json_files:
        print(f"❌ Aucun fichier JSON trouvé dans '{input_dir}'")
        return
    
    print(f"{'='*70}")
    print(f"🚀 DÉMARRAGE DU CLASSIFICATEUR MULTI-DATABASE")
    print(f"{'='*70}")
    print(f"📁 Dossier d'entrée: {input_dir}")
    print(f"📤 Dossier de sortie: {output_dir}")
    print(f"📄 Fichiers à traiter: {len(json_files)}\n")
    
    # Créer le classificateur (une seule fois pour tous les fichiers)
    classifier = ChangelogClassifier()
    
    # Statistiques globales
    total_files = len(json_files)
    successful = 0
    failed = 0
    total_versions_processed = 0
    
    # Traiter chaque fichier
    for i, filename in enumerate(json_files, 1):
        print(f"\n{'='*70}")
        print(f"📂 [{i}/{total_files}] Fichier: {filename}")
        print(f"{'='*70}")
        
        input_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)
        
        try:
            classifier.process_file(input_path, output_path)
            successful += 1
            print(f"💾 Sauvegardé dans: {output_path}")
        except Exception as e:
            print(f"❌ Erreur: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    # Résumé final
    print(f"\n{'='*70}")
    print(f"✅ TRAITEMENT TERMINÉ")
    print(f"{'='*70}")
    print(f"✔️  Fichiers traités avec succès: {successful}/{total_files}")
    if failed > 0:
        print(f"❌ Fichiers en erreur: {failed}/{total_files}")
    print(f"📁 Tous les résultats sont dans: {output_dir}/")
    print(f"{'='*70}")


def main():
    """Point d'entrée principal"""
    # Traiter tous les fichiers du dossier output vers outputfinal
    process_directory(input_dir="output", output_dir="outputfinal")


if __name__ == "__main__":
    main()