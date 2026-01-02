#!/usr/bin/env python3
"""
Script pour ajouter des alertes (vulnérabilités critiques, performance majeure)
directement dans chaque fichier JSON du dossier output.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import re

class AlertsAdder:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.backup_dir = Path("output_backup_alerts")
        
        # Mots-clés pour les vulnérabilités critiques
        self.vulnerability_keywords = [
            'security', 'vulnerability', 'cve', 'exploit', 'attack', 'breach',
            'authentication', 'authorization', 'privilege escalation', 'injection',
            'xss', 'csrf', 'sql injection', 'remote code execution', 'rce',
            'buffer overflow', 'memory corruption', 'dos', 'denial of service',
            'cryptographic', 'encryption', 'tls', 'ssl', 'certificate',
            'credential', 'password', 'token', 'jwt', 'oauth', 'saml',
            'firewall', 'malware', 'virus', 'trojan', 'backdoor', 'rootkit'
        ]
        
        # Mots-clés pour les changements de performance majeure
        self.performance_keywords = [
            'performance', 'optimization', 'improve', 'speed', 'fast', 'slow',
            'latency', 'throughput', 'benchmark', 'scalability', 'memory',
            'cpu', 'disk', 'network', 'cache', 'index', 'query', 'execution',
            'concurrency', 'parallel', 'async', 'batch', 'pool', 'connection',
            'compression', 'serialization', 'deserialization', 'marshaling',
            'garbage collection', 'gc', 'heap', 'stack', 'allocation', 'leak',
            'bottleneck', 'hotspot', 'critical path', 'resource', 'utilization'
        ]
        
        # Mots-clés pour les changements critiques/majeurs
        self.critical_keywords = [
            'critical', 'major', 'breaking', 'incompatible', 'deprecation',
            'removal', 'discontinued', 'obsolete', 'legacy', 'migration',
            'upgrade', 'downgrade', 'compatibility', 'stability', 'reliability',
            'crash', 'hang', 'deadlock', 'timeout', 'failure', 'error',
            'exception', 'panic', 'abort', 'terminate', 'shutdown', 'restart'
        ]
    
    def is_vulnerability_related(self, text: str) -> bool:
        """Vérifie si le texte contient des mots-clés de vulnérabilité"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.vulnerability_keywords)
    
    def is_performance_related(self, text: str) -> bool:
        """Vérifie si le texte contient des mots-clés de performance"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.performance_keywords)
    
    def is_critical_change(self, text: str) -> bool:
        """Vérifie si le texte contient des mots-clés de changement critique"""
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in self.critical_keywords)
    
    def assess_alert_level(self, text: str) -> str:
        """Évalue le niveau d'alerte basé sur le contenu"""
        text_lower = text.lower()
        
        # Critique : vulnérabilités de sécurité ou crashes
        if any(word in text_lower for word in ['cve', 'exploit', 'rce', 'remote code execution', 'privilege escalation', 'crash', 'security']):
            return 'critical'
        
        # Élevé : changements de performance majeurs ou breaking changes
        elif any(word in text_lower for word in ['breaking', 'incompatible', 'major performance', 'critical performance', 'deprecation']):
            return 'high'
        
        # Moyen : améliorations de performance ou changements importants
        elif any(word in text_lower for word in ['performance', 'optimization', 'improve', 'major', 'significant']):
            return 'medium'
        
        # Bas : changements mineurs
        elif self.is_vulnerability_related(text) or self.is_performance_related(text) or self.is_critical_change(text):
            return 'low'
        
        return None
    
    def extract_alerts_from_changes(self, changes: List[str]) -> List[Dict]:
        """Extrait les alertes de la liste des changements"""
        alerts = []
        for change in changes:
            alert_level = self.assess_alert_level(change)
            if alert_level:
                alert_type = []
                if self.is_vulnerability_related(change):
                    alert_type.append('vulnerability')
                if self.is_performance_related(change):
                    alert_type.append('performance')
                if self.is_critical_change(change):
                    alert_type.append('critical_change')
                
                alerts.append({
                    "description": change,
                    "level": alert_level,
                    "type": alert_type,
                })
        return alerts
    
    def extract_alerts_from_ai_analysis(self, ai_analysis: Dict) -> List[Dict]:
        """Extrait les alertes de l'analyse IA"""
        alerts = []
        if 'details' in ai_analysis:
            for detail in ai_analysis['details']:
                alert_level = self.assess_alert_level(detail['description'])
                if alert_level:
                    alert_type = []
                    if self.is_vulnerability_related(detail['description']):
                        alert_type.append('vulnerability')
                    if self.is_performance_related(detail['description']):
                        alert_type.append('performance')
                    if self.is_critical_change(detail['description']):
                        alert_type.append('critical_change')
                    
                    alerts.append({
                        "description": detail['description'],
                        "level": alert_level,
                        "type": alert_type,
                        "category": detail.get('category', 'unknown'),
                    })
        return alerts
    
    def process_version_data(self, version_data: Dict) -> Dict:
        """Traite les données d'une version pour ajouter les alertes"""
        modified_data = version_data.copy()
        
        # Extraire les alertes
        alerts = []
        
        # Depuis les changements
        if 'changes' in version_data:
            alerts.extend(self.extract_alerts_from_changes(version_data['changes']))
        
        # Depuis l'analyse IA
        if 'ai_analysis' in version_data:
            alerts.extend(self.extract_alerts_from_ai_analysis(version_data['ai_analysis']))
        
        # Trier les alertes par niveau d'importance
        level_priority = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: level_priority.get(x['level'], 4))
        
        # Ajouter la section alerts
        modified_data['alerts'] = {
            "total_count": len(alerts),
            "critical_count": len([a for a in alerts if a['level'] == 'critical']),
            "high_count": len([a for a in alerts if a['level'] == 'high']),
            "medium_count": len([a for a in alerts if a['level'] == 'medium']),
            "low_count": len([a for a in alerts if a['level'] == 'low']),
            "alerts": alerts,
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
                    
                    alert_count = modified_version['alerts']['total_count']
                    critical_count = modified_version['alerts']['critical_count']
                    high_count = modified_version['alerts']['high_count']
                    
                    if alert_count > 0:
                        version_name = version_data.get('patch_version', version_data.get('major_version', 'unknown'))
                        print(f"  {version_name}: {alert_count} alertes")
                        if critical_count > 0:
                            print(f"    ⚠️  {critical_count} critique(s)")
                        if high_count > 0:
                            print(f"    🔥 {high_count} élevée(s)")
            
            # Sauvegarder les modifications
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                print(f"✅ Fichier modifié: {file_path.name}")
                return True
            else:
                print(f"ℹ️  Aucune alerte trouvée: {file_path.name}")
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
        
        print(f"🚨 Traitement de {len(json_files)} fichiers JSON pour détection d'alertes...")
        print("=" * 70)
        
        # Créer une sauvegarde
        self.backup_output_directory()
        
        total_files_modified = 0
        total_alerts = 0
        total_critical = 0
        total_high = 0
        
        for file_path in json_files:
            print(f"\n📁 Traitement de: {file_path.name}")
            if self.process_json_file(file_path):
                total_files_modified += 1
                
                # Compter les alertes dans ce fichier
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    for version_data in data:
                        if 'alerts' in version_data:
                            total_alerts += version_data['alerts']['total_count']
                            total_critical += version_data['alerts']['critical_count']
                            total_high += version_data['alerts']['high_count']
                except:
                    pass
        
        print("\n" + "=" * 70)
        print("🚨 RÉSUMÉ DES ALERTES")
        print("=" * 70)
        print(f"Fichiers traités: {len(json_files)}")
        print(f"Fichiers avec alertes: {total_files_modified}")
        print(f"Total alertes détectées: {total_alerts}")
        print(f"⚠️  Alertes critiques: {total_critical}")
        print(f"🔥 Alertes élevées: {total_high}")
        print(f"Sauvegarde disponible dans: {self.backup_dir}")
        
        if total_critical > 0:
            print(f"\n⚠️  ATTENTION: {total_critical} alerte(s) critique(s) détectée(s)!")
        if total_high > 0:
            print(f"🔥 {total_high} alerte(s) élevée(s) requièrent une attention particulière!")
        
        if total_files_modified > 0:
            print("\n✅ Tous les fichiers ont été mis à jour avec les alertes!")
        else:
            print("\nℹ️  Aucune alerte détectée dans les fichiers.")

def main():
    """Fonction principale"""
    print("🚨 Ajout des alertes (vulnérabilités, performance, changements critiques)")
    print("Ce script va modifier directement les fichiers dans le dossier 'output'")
    print("🔍 Détection automatique des alertes par niveau: critical, high, medium, low")
    print("=" * 70)
    
    # Demander confirmation
    response = input("\nVoulez-vous continuer? (y/N): ").strip().lower()
    if response not in ['y', 'yes', 'oui', 'o']:
        print("Opération annulée.")
        return
    
    adder = AlertsAdder()
    adder.process_all_files()

if __name__ == "__main__":
    main()
