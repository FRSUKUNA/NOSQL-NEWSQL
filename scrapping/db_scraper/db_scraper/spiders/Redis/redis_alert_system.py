import requests
import json
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from dataclasses import dataclass
import time

# Configuration
CONFIG = {
    'redis_versions_url': 'https://github.com/redis/redis/tags',
    'cve_api_url': 'https://services.nvd.nist.gov/rest/json/cves/1.0',
    'versions_file': 'redis_versions.json',
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'email_sender': os.getenv('GMAIL_EMAIL', 'votre_email@gmail.com'),
    'email_password': os.getenv('GMAIL_APP_PASSWORD', 'votre_mot_de_passe_app'),
    'email_recipients': ['destinataire@example.com'],
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

@dataclass
class RedisVersion:
    version: str
    date: str
    is_stable: bool = False
    changes: List[str] = None
    vulnerabilities: List[Dict] = None

    def __post_init__(self):
        if self.changes is None:
            self.changes = []
        if self.vulnerabilities is None:
            self.vulnerabilities = []

class RedisMonitor:
    def __init__(self):
        self.headers = {'User-Agent': CONFIG['user_agent']}
        self.versions_file = CONFIG['versions_file']
        
    def get_redis_versions(self) -> List[Dict]:
        """Récupère les versions de Redis depuis GitHub"""
        print("Récupération des versions de Redis...")
        try:
            response = requests.get(CONFIG['redis_versions_url'], headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            versions = []
            
            for tag in soup.select('a.Link--primary'):
                version_text = tag.text.strip()
                if version_text.startswith('v') and version_text[1].isdigit():
                    version = version_text[1:]  # Enlève le 'v' du début
                    date_tag = tag.find_next('relative-time')
                    date = date_tag['datetime'] if date_tag else 'Date inconnue'
                    
                    versions.append({
                        'version': version,
                        'date': date,
                        'is_stable': 'alpha' not in version.lower() and 'beta' not in version.lower()
                    })
            
            return versions
            
        except Exception as e:
            print(f"Erreur lors de la récupération des versions: {e}")
            return []

    def get_redis_official_info(self, version: str) -> Dict:
        """Récupère les informations officielles d'une version depuis redis.io"""
        try:
            url = f"https://redis.io/docs/latest/operate/oss_and_stack/release-notes/release-{version}/"
            print(f"Récupération des informations officielles pour Redis {version}...")
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 404:
                url = "https://redis.io/docs/latest/operate/oss_and_stack/release-notes/"
                response = requests.get(url, headers=self.headers, timeout=30)
            
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            info = {
                'version': version,
                'release_notes': [],
                'important_changes': [],
                'download_url': f"https://download.redis.io/releases/redis-{version}.tar.gz"
            }
            
            content = soup.find('article') or soup.find('main') or soup.find('div', class_='content')
            if content:
                for h2 in content.find_all(['h2', 'h3']):
                    section = {
                        'title': h2.get_text(strip=True),
                        'content': []
                    }
                    
                    next_node = h2.next_sibling
                    while next_node and next_node.name not in ['h2', 'h3']:
                        if next_node.name == 'p':
                            section['content'].append(next_node.get_text(strip=True))
                        next_node = next_node.next_sibling
                    
                    info['release_notes'].append(section)
                    
                    if any(keyword in section['title'].lower() for keyword in 
                          ['important', 'security', 'breaking change', 'new feature']):
                        info['important_changes'].extend(section['content'])
            
            return info
            
        except Exception as e:
            print(f"Erreur lors de la récupération des informations officielles: {e}")
            return None

    def check_security_vulnerabilities(self, version: str) -> List[Dict]:
        """Vérifie les vulnérabilités pour une version spécifique"""
        try:
            response = requests.get(
                f"{CONFIG['cve_api_url']}?keyword=redis {version}",
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('result', {}).get('CVE_Items', [])
        except Exception as e:
            print(f"Erreur lors de la vérification des vulnérabilités: {e}")
            return []

    def analyze_version_changes(self, current_versions: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Analyse les changements entre les versions"""
        alerts = []
        new_versions = []
        
        try:
            if os.path.exists(self.versions_file):
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    previous_data = json.load(f)
                    previous_versions = {v['version']: v for v in previous_data.get('versions', [])}
            else:
                previous_versions = {}

            for version in current_versions:
                version_info = version.copy()
                
                if version['version'] not in previous_versions:
                    official_info = self.get_redis_official_info(version['version'])
                    if official_info:
                        version_info.update(official_info)
                        alerts.append(f"🆕 Nouvelle version détectée: Redis {version['version']} (Date: {version['date']})")
                        
                        if version_info.get('important_changes'):
                            alerts.append("📌 Changements importants :")
                            alerts.extend([f"   • {change}" for change in version_info['important_changes'][:3]])
                        
                    new_versions.append(version_info)
                    
                    vulns = self.check_security_vulnerabilities(version['version'])
                    if vulns:
                        alerts.append(f"⚠️ {len(vulns)} vulnérabilité(s) trouvée(s) pour la version {version['version']}")

            for version in current_versions:
                if version['version'] in previous_versions:
                    prev_major = int(previous_versions[version['version']]['version'].split('.')[0])
                    curr_major = int(version['version'].split('.')[0])
                    
                    if curr_major > prev_major:
                        alerts.append(f"🚨 Mise à jour majeure disponible: Redis {version['version']}")
                        alerts.append(f"   🔗 Notes de version: https://redis.io/docs/latest/operate/oss_and_stack/release-notes/release-{version['version']}/")

        except Exception as e:
            print(f"Erreur lors de l'analyse des versions: {e}")

        return new_versions, alerts

    def send_alert(self, subject: str, content: str, is_critical: bool = False) -> bool:
        """Envoie une alerte par email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = CONFIG['email_sender']
            msg['To'] = ', '.join(CONFIG['email_recipients'])
            msg['Subject'] = f"{'🚨 URGENT - ' if is_critical else 'ℹ️ '}{subject}"
            
            # Style minimal pour le contenu
            bg_color = '#ffebee' if is_critical else '#e3f2fd'
            html_template = """
            <html>
                <body>
                    <h2>Redis Monitoring Alert</h2>
                    <div style="background-color: {bg_color}; padding: 15px; border-radius: 5px; font-family: Arial, sans-serif;">
                        {content}
                    </div>
                    <p style="color: #666; font-size: 0.9em; margin-top: 20px;">
                        Ceci est une notification automatique du système de surveillance Redis.
                    </p>
                </body>
            </html>
            """
            html_content = html_template.format(bg_color=bg_color, content=content.replace('\n', '<br>'))
            
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(CONFIG['smtp_server'], CONFIG['smtp_port']) as server:
                server.starttls()
                server.login(CONFIG['email_sender'], CONFIG['email_password'])
                server.send_message(msg)
                
            print("Alerte envoyée avec succès")
            return True
            
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {e}")
            return False

    def save_versions(self, versions: List[Dict]) -> None:
        """Sauvegarde les versions dans un fichier JSON"""
        try:
            data = {
                'last_checked': datetime.utcnow().isoformat(),
                'versions': versions
            }
            
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des versions: {e}")

    def run(self):
        """Exécute la surveillance"""
        print("\n" + "="*50)
        print(f"Vérification des mises à jour Redis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        try:
            current_versions = self.get_redis_versions()
            if not current_versions:
                print("Aucune version trouvée. Vérifiez votre connexion Internet.")
                return

            new_versions, alerts = self.analyze_version_changes(current_versions)
            
            if alerts:
                print("\n🔔 Alertes détectées :")
                for alert in alerts:
                    print(f"- {alert}")
                
                subject = f"Redis - {len(alerts)} alerte(s) de sécurité/mise à jour"
                content = "\n".join(alerts)
                self.send_alert(subject, content, any('🚨' in alert for alert in alerts))
            else:
                print("\n✅ Aucune alerte critique détectée.")
            
            self.save_versions(current_versions)
            print(f"\n✅ {len(current_versions)} versions enregistrées dans {self.versions_file}")
            
        except Exception as e:
            error_msg = f"Erreur critique dans le système de surveillance: {str(e)}"
            print(error_msg)
            self.send_alert("Erreur dans le système de surveillance Redis", error_msg, is_critical=True)

if __name__ == "__main__":
    if not all([CONFIG['email_sender'], CONFIG['email_password']]):
        print("ERREUR: Veuillez configurer les variables d'environnement GMAIL_EMAIL et GMAIL_APP_PASSWORD")
        print("Ou modifiez-les directement dans le fichier CONFIG")
        exit(1)

    monitor = RedisMonitor()
    monitor.run()