
import requests
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass

# Configuration
CONFIG = {
    'alerts_url': 'https://www.mongodb.com/resources/products/alerts',
    'security_url': 'https://www.mongodb.com/security',
    'advisories_url': 'https://www.mongodb.com/support/security-advisories',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'timeout': 30,
    'alerts_file': 'mongodb_alerts.json'
}

# Mots-clés pour la classification
SECURITY_KEYWORDS = [
    'security', 'vulnerability', 'cve', 'authentication', 'authorization',
    'privilege', 'bypass', 'exploit', 'injection', 'xss', 'csrf',
    'privilege escalation', 'authentication bypass', 'authorization bypass',
    'remote code execution', 'rce', 'denial of service', 'dos'
]

PERFORMANCE_KEYWORDS = [
    'performance', 'latency', 'throughput', 'slow', 'regression',
    'degradation', 'outage', 'memory leak', 'cpu', 'disk',
    'optimization', 'improvement', 'tuning', 'scalability'
]

CRITICAL_KEYWORDS = [
    'critical', 'urgent', 'severe', 'high', 'important',
    'immediate', 'emergency', 'outage', 'downtime'
]

@dataclass
class MongoDBAlert:
    title: str
    description: str
    severity: str
    alert_type: str
    date: str
    url: Optional[str] = None
    affected_versions: List[str] = None

    def __post_init__(self):
        if self.affected_versions is None:
            self.affected_versions = []

class MongoDBAlertsScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': CONFIG['user_agent']})
        
    def scrape_alerts_page(self) -> List[Dict]:
        """Scrape la page des alertes MongoDB avec la structure exacte du site"""
        print("Scraping de la page des alertes MongoDB...")
        all_alerts = []
        
        try:
            response = self.session.get(CONFIG['alerts_url'], timeout=CONFIG['timeout'])
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parser les sections principales d'alertes
            alerts = self._parse_mongodb_alerts_structure(soup)
            all_alerts.extend(alerts)
            
            print(f"   → {len(alerts)} alertes trouvées sur la page principale")
            
        except Exception as e:
            print(f"Erreur lors du scraping principal: {e}")
        
        # Essayer les autres URLs si besoin
        if len(all_alerts) < 10:
            for url in [CONFIG['security_url'], CONFIG['advisories_url']]:
                try:
                    print(f"Tentative scraping de {url}...")
                    response = self.session.get(url, timeout=CONFIG['timeout'])
                    response.raise_for_status()
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    alerts = self._parse_general_alerts(soup)
                    all_alerts.extend(alerts)
                    print(f"   → {len(alerts)} alertes supplémentaires")
                    
                except Exception as e:
                    print(f"   Erreur: {e}")
                    continue
        
        # Déduplication
        seen_content = set()
        unique_alerts = []
        for alert in all_alerts:
            content_key = (alert['title'].lower().strip() + alert['description'].lower().strip())[:200]
            if content_key not in seen_content and len(alert['title'].strip()) > 10:
                seen_content.add(content_key)
                unique_alerts.append(alert)
        
        return unique_alerts
    
    def _parse_mongodb_alerts_structure(self, soup) -> List[Dict]:
        """Parse la structure spécifique des alertes MongoDB"""
        alerts = []
        
        # Chercher toutes les sections d'alertes (h2 avec les titres)
        sections = soup.find_all(['h2', 'h3'], string=re.compile(r'(Security|Data Integrity|Operations|General)', re.I))
        
        for section_header in sections:
            section_title = section_header.get_text(strip=True)
            print(f"   Section trouvée: {section_title}")
            
            # Parser le contenu après cette section
            current_element = section_header.next_sibling
            
            # Continuer jusqu'à la prochaine section ou fin
            while current_element:
                # Arrêter si on trouve une autre section principale
                if (current_element.name in ['h1', 'h2', 'h3'] and 
                    current_element.get_text(strip=True) != section_title and
                    re.search(r'(Security|Data Integrity|Operations|General)', current_element.get_text(), re.I)):
                    break
                
                # Parser les alertes dans cette section
                if current_element.name == 'div' or current_element.name == 'section':
                    section_alerts = self._extract_alerts_from_section(current_element, section_title)
                    alerts.extend(section_alerts)
                
                current_element = current_element.next_sibling
        
        # Fallback: chercher tous les patterns d'alertes dans le texte
        if not alerts:
            alerts = self._parse_all_alert_patterns(soup)
        
        return alerts
    
    def _extract_alerts_from_section(self, section_element, section_type: str) -> List[Dict]:
        """Extrait les alertes d'une section spécifique"""
        alerts = []
        
        # Chercher les sous-titres (h4) qui représentent des alertes individuelles
        alert_headers = section_element.find_all('h4')
        
        for header in alert_headers:
            try:
                # Titre de l'alerte
                title = header.get_text(strip=True)
                
                if len(title) < 20:  # Ignorer les titres trop courts
                    continue
                
                # Description - chercher le contenu après le h4
                description = ""
                current = header.next_sibling
                
                # Collecter le texte jusqu'au prochain h4 ou fin de section
                while current and current.name != 'h4':
                    if hasattr(current, 'get_text'):
                        text = current.get_text(strip=True)
                        if text and len(text) > 10:
                            description += text + " "
                    
                    # Arrêter si on atteint la fin de la section
                    if (current.name in ['h1', 'h2', 'h3'] and 
                        current.get_text(strip=True) != section_type):
                        break
                    
                    current = current.next_sibling
                
                description = description.strip()
                
                # Extraire les versions affectées
                versions_text = title + " " + description
                versions = self._extract_versions(versions_text)
                
                # Extraire la date
                date = self._extract_date_from_text(description)
                
                # Extraire les liens
                links = section_element.find_all('a', href=True)
                url = None
                for link in links:
                    href = link.get('href', '')
                    if 'jira.mongodb.org' in href or 'github.com' in href:
                        url = href
                        break
                
                # Classification
                alert_type = self._classify_alert(title, description, section_type)
                severity = self._determine_severity(title, description, alert_type)
                
                if len(description) > 30:  # Garder seulement les alertes avec description significative
                    alerts.append({
                        'title': title,
                        'description': description,
                        'date': date,
                        'url': url,
                        'affected_versions': versions,
                        'section_type': section_type
                    })
                
            except Exception as e:
                print(f"Erreur extraction alerte: {e}")
                continue
        
        return alerts
    
    def _parse_all_alert_patterns(self, soup) -> List[Dict]:
        """Parse tous les patterns d'alertes dans la page"""
        alerts = []
        content = soup.get_text()
        
        # Patterns pour les alertes MongoDB spécifiques
        alert_patterns = [
            # Pattern: Titre suivi de description et versions
            r'([A-Z][^.!?]*[^.!?]*\.)\s*([^.!?]*[affects|affecting][^.!?]*\.)',
            # Pattern: CVE
            r'(CVE-\d{4}-\d+)[^.!?]*([^.!?]*\.)',
            # Pattern: MongoDB Server
            r'(MongoDB Server[^.!?]*\.)\s*([^.!?]*\.)',
        ]
        
        for pattern in alert_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                title = match.group(1).strip()
                description = match.group(2).strip() if len(match.groups()) > 1 else title
                
                if len(title) > 30 and not self._is_generic_text(title):
                    alerts.append({
                        'title': title,
                        'description': description,
                        'date': self._extract_date_from_text(title + description),
                        'url': None,
                        'affected_versions': self._extract_versions(title + description),
                        'section_type': 'General'
                    })
        
        return alerts[:50]  # Limiter à 50 alertes max
    
    def _classify_alert(self, title: str, description: str, section_type: str) -> str:
        """Classifie le type d'alerte"""
        title_lower = title.lower()
        desc_lower = description.lower()
        combined = f"{title_lower} {desc_lower}"
        
        if 'security' in section_type.lower() or any(keyword in combined for keyword in SECURITY_KEYWORDS):
            return "VULNERABILITÉ"
        elif any(keyword in combined for keyword in PERFORMANCE_KEYWORDS):
            return "PERFORMANCE"
        elif 'data integrity' in section_type.lower():
            return "INTÉGRITÉ"
        else:
            return "AUTRE"
    
    def _determine_severity(self, title: str, description: str, alert_type: str) -> str:
        """Détermine la sévérité de l'alerte"""
        combined = f"{title.lower()} {description.lower()}"
        
        if any(keyword in combined for keyword in CRITICAL_KEYWORDS):
            return "CRITIQUE"
        elif alert_type == "VULNERABILITÉ":
            return "ÉLEVÉE"
        elif any(keyword in combined for keyword in ['memory', 'crash', 'corruption', 'loss']):
            return "ÉLEVÉE"
        else:
            return "MOYENNE"
    
    def _parse_general_alerts(self, soup) -> List[Dict]:
        """Parse les alertes depuis d'autres pages (sécurité, advisories)"""
        alerts = []
        
        # Utiliser la logique précédente pour les autres pages
        alert_selectors = [
            'div[class*="alert"]',
            'div[class*="security"]',
            'div[class*="vulnerability"]',
            'article[class*="alert"]',
            'section[class*="alert"]'
        ]
        
        for selector in alert_selectors:
            elements = soup.select(selector)
            for element in elements:
                alert_data = self._extract_alert_data(element)
                if alert_data and self._is_real_alert(alert_data):
                    alerts.append(alert_data)
        
        return alerts
    
    def _parse_lists_and_tables(self, soup) -> List[Dict]:
        """Parse les listes et tableaux pour trouver des alertes"""
        alerts = []
        
        # Chercher dans les listes
        for li in soup.find_all('li'):
            text = li.get_text(strip=True)
            if len(text) > 50 and any(keyword in text.lower() for keyword in ['security', 'vulnerability', 'cve', 'patch', 'update']):
                alerts.append({
                    'title': text[:100],
                    'description': text,
                    'date': self._extract_date(li),
                    'url': None,
                    'affected_versions': self._extract_versions(text)
                })
        
        # Chercher dans les tableaux
        for tr in soup.find_all('tr'):
            cells = tr.find_all(['td', 'th'])
            if len(cells) >= 2:
                row_text = ' '.join([cell.get_text(strip=True) for cell in cells])
                if len(row_text) > 50 and any(keyword in row_text.lower() for keyword in ['security', 'vulnerability', 'cve', 'patch']):
                    alerts.append({
                        'title': cells[0].get_text(strip=True),
                        'description': row_text,
                        'date': self._extract_date(tr),
                        'url': None,
                        'affected_versions': self._extract_versions(row_text)
                    })
        
        return alerts[:30]  # Limiter à 30 alertes max
    
    def _extract_alert_data(self, element) -> Optional[Dict]:
        """Extrait les données d'une alerte depuis un élément HTML"""
        try:
            # Titre
            title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or element.find('a')
            title = title_elem.get_text(strip=True) if title_elem else element.get_text(strip=True)
            
            # Nettoyer le titre
            title = re.sub(r'\s*arrow-right\s*', '', title, flags=re.IGNORECASE)
            title = title.strip()
            
            if not title or len(title) < 10:
                return None
            
            # Description détaillée - chercher dans plusieurs endroits
            description = ""
            
            # 1. Chercher un paragraphe de description
            desc_elem = element.find('p')
            if desc_elem:
                description = desc_elem.get_text(strip=True)
            
            # 2. Chercher dans une div de contenu
            if not description or len(description) < 20:
                content_elem = element.find('div', class_=re.compile(r'content|description|summary|body'))
                if content_elem:
                    description = content_elem.get_text(strip=True)
            
            # 3. Chercher tous les textes dans l'élément (sauf le titre)
            if not description or len(description) < 20:
                all_text = element.get_text(strip=True)
                # Enlever le titre du début
                if title in all_text:
                    description = all_text.replace(title, '').strip()
                else:
                    description = all_text
            
            # Nettoyer la description
            description = re.sub(r'\s*arrow-right\s*', '', description, flags=re.IGNORECASE)
            description = re.sub(r'\s+', ' ', description)
            description = description.strip()
            
            # Date - chercher dans plusieurs formats
            date = self._extract_date(element)
            
            # URL
            url_elem = element.find('a', href=True)
            url = url_elem['href'] if url_elem else None
            if url and not url.startswith('http'):
                url = f"https://www.mongodb.com{url}"
            
            # Versions affectées
            versions = self._extract_versions(title + ' ' + description)
            
            return {
                'title': title,
                'description': description,
                'date': date,
                'url': url,
                'affected_versions': versions
            }
            
        except Exception as e:
            print(f"Erreur extraction alerte: {e}")
            return None
    
    def _extract_date(self, element) -> str:
        """Extrait la date depuis un élément HTML"""
        # 1. Chercher une balise time
        time_elem = element.find('time')
        if time_elem:
            date = time_elem.get('datetime') or time_elem.get_text(strip=True)
            if date:
                return self._normalize_date(date)
        
        # 2. Chercher un span avec classe date/time
        date_elem = element.find('span', class_=re.compile(r'date|time|published'))
        if date_elem:
            date = date_elem.get_text(strip=True)
            if date:
                return self._normalize_date(date)
        
        # 3. Chercher des patterns de date dans le texte
        text = element.get_text()
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',  # MM/DD/YYYY
            r'(\d{4}-\d{2}-\d{2})',      # YYYY-MM-DD
            r'(\d{1,2}\s+\w+\s+\d{4})', # DD Month YYYY
            r'(\w+\s+\d{1,2},?\s+\d{4})' # Month DD, YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return self._normalize_date(match.group(1))
        
        # 4. Date par défaut
        return datetime.now().strftime('%Y-%m-%d')
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalise différents formats de date vers YYYY-MM-DD"""
        try:
            # Nettoyer la chaîne
            date_str = date_str.strip()
            
            # Patterns et formats correspondants
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y/%m/%d',
                '%B %d, %Y',
                '%b %d, %Y',
                '%d %B %Y',
                '%d %b %Y'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Si aucun format ne correspond, retourner la date actuelle
            return datetime.now().strftime('%Y-%m-%d')
            
        except Exception:
            return datetime.now().strftime('%Y-%m-%d')
    
    def _is_real_alert(self, alert_data: Dict) -> bool:
        """Vérifie si c'est une vraie alerte et pas un lien générique"""
        title = alert_data['title'].lower()
        description = alert_data['description'].lower()
        
        # Exclure les liens génériques
        generic_patterns = [
            r'learn more',
            r'see stories',
            r'connect with',
            r'arrow-right',
            r'contact us',
            r'get started',
            r'try now',
            r'download',
            r'sign up'
        ]
        
        for pattern in generic_patterns:
            if re.search(pattern, title):
                return False
        
        # Inclure seulement si contient des mots-clés d'alerte
        alert_keywords = SECURITY_KEYWORDS + PERFORMANCE_KEYWORDS + [
            'bug', 'fix', 'issue', 'patch', 'update', 'release',
            'critical', 'urgent', 'important', 'warning', 'advisory'
        ]
        
        combined_text = f"{title} {description}"
        return any(keyword in combined_text for keyword in alert_keywords)
    
    def _parse_alert_patterns(self, soup) -> List[Dict]:
        """Parse le contenu textuel pour des patterns d'alertes spécifiques"""
        alerts = []
        content = soup.get_text()
        
        # Nettoyer le contenu
        content = re.sub(r'\s*arrow-right\s*', ' ', content, flags=re.IGNORECASE)
        
        # Patterns plus spécifiques pour MongoDB avec extraction de date
        alert_patterns = [
            r'(?:Security\s+(?:Bulletin|Advisory|Alert))\s*[:\-]?\s*([^\n]+?)(?=\n\n|\n[A-Z]|\Z)',
            r'(?:CVE-\d{4}-\d+):\s*([^\n]+?)(?=\n\n|\n[A-Z]|\Z)',
            r'(?:MongoDB\s+(?:Security|Vulnerability|Advisory))\s*[:\-]?\s*([^\n]+?)(?=\n\n|\n[A-Z]|\Z)',
            r'(?:Critical\s+(?:Security|Update|Patch))\s*[:\-]?\s*([^\n]+?)(?=\n\n|\n[A-Z]|\Z)',
            r'(?:Version\s+(\d+\.\d+(?:\.\d+)?))\s*[:\-]?\s*([^\n]+?)(?=\n\n|\n[A-Z]|\Z)',
            # Pattern avec date: YYYY-MM-DD - Description
            r'(\d{4}-\d{2}-\d{2})\s*[:\-]?\s*([^\n]*(?:security|vulnerability|cve|patch|update)[^\n]*)(?=\n\n|\n[A-Z]|\Z)',
            # Pattern: MongoDB X.X.X - Description
            r'MongoDB\s+(\d+\.\d+(?:\.\d+)?)\s*[:\-]?\s*([^\n]*(?:security|vulnerability|cve|patch|update)[^\n]*)(?=\n\n|\n[A-Z]|\Z)'
        ]
        
        for pattern in alert_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                groups = match.groups()
                
                if len(groups) == 2:
                    if re.match(r'\d{4}-\d{2}-\d{2}', groups[0]):  # Premier groupe est une date
                        date = groups[0]
                        desc = groups[1]
                        title = f"Security Alert - {desc[:80]}"
                    elif re.match(r'\d+\.\d+(?:\.\d+)?', groups[0]):  # Premier groupe est une version
                        version = groups[0]
                        desc = groups[1]
                        title = f"MongoDB {version} - {desc[:80]}"
                        date = self._extract_date_from_text(desc)
                    else:
                        title = groups[0].strip()
                        desc = groups[1].strip()
                        date = self._extract_date_from_text(desc)
                else:
                    title = match.group(1).strip()
                    desc = title
                    date = self._extract_date_from_text(title)
                
                title = title.strip()
                desc = desc.strip()
                
                if len(title) > 30 and not self._is_generic_text(title):
                    alerts.append({
                        'title': title,
                        'description': desc,
                        'date': date,
                        'url': None,
                        'affected_versions': self._extract_versions(title + ' ' + desc)
                    })
        
        return alerts[:20]  # Limiter à 20 alertes max
    
    def _extract_date_from_text(self, text: str) -> str:
        """Extrait une date depuis un texte"""
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})',
            r'(\w+\s+\d{1,2},?\s+\d{4})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return self._normalize_date(match.group(1))
        
        return datetime.now().strftime('%Y-%m-%d')
    
    def _is_generic_text(self, text: str) -> bool:
        """Vérifie si le texte est générique"""
        generic_indicators = [
            'learn more', 'see how', 'discover', 'explore', 'find out',
            'get started', 'try now', 'contact', 'about us', 'our story'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in generic_indicators)
    
    def _find_alert_links(self, soup) -> List[Dict]:
        """Cherche les liens vers des pages d'alertes spécifiques"""
        alerts = []
        
        # Liens vers des pages de sécurité/advisories
        link_patterns = [
            r'/security/',
            r'/advisory/',
            r'/bulletin/',
            r'/alert/',
            r'/cve-',
            r'/patch/',
            r'/update/'
        ]
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            title = link.get_text(strip=True)
            
            # Nettoyer le titre
            title = re.sub(r'\s*arrow-right\s*', '', title, flags=re.IGNORECASE)
            title = title.strip()
            
            if len(title) < 10:
                continue
                
            # Vérifier si le lien correspond à un pattern d'alerte
            for pattern in link_patterns:
                if re.search(pattern, href, re.IGNORECASE):
                    if not self._is_generic_text(title):
                        alerts.append({
                            'title': title,
                            'description': title,
                            'date': datetime.now().strftime('%Y-%m-%d'),
                            'url': href if href.startswith('http') else f"https://www.mongodb.com{href}",
                            'affected_versions': self._extract_versions(title)
                        })
                    break
        
        return alerts[:20]  # Limiter à 20 alertes max
    
    def _extract_versions(self, text: str) -> List[str]:
        """Extrait les versions MongoDB depuis le texte"""
        version_patterns = [
            r'MongoDB\s+(\d+\.\d+(?:\.\d+)?)',
            r'(\d+\.\d+\.\d+)',
            r'version\s+(\d+\.\d+(?:\.\d+)?)'
        ]
        
        versions = set()
        for pattern in version_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                versions.add(match.group(1))
        
        return sorted(list(versions))
    
    def classify_alert(self, alert_data: Dict) -> MongoDBAlert:
        """Classifie une alerte (sécurité vs performance) et détermine la sévérité"""
        title = alert_data['title'].lower()
        description = alert_data['description'].lower()
        combined_text = f"{title} {description}"
        
        # Détermination du type
        is_security = any(keyword in combined_text for keyword in SECURITY_KEYWORDS)
        is_performance = any(keyword in combined_text for keyword in PERFORMANCE_KEYWORDS)
        
        if is_security:
            alert_type = "VULNERABILITÉ"
        elif is_performance:
            alert_type = "PERFORMANCE"
        else:
            alert_type = "AUTRE"
        
        # Détermination de la sévérité
        if any(keyword in combined_text for keyword in CRITICAL_KEYWORDS):
            severity = "CRITIQUE"
        elif alert_type == "VULNERABILITÉ":
            severity = "ÉLEVÉE"
        elif is_performance and any(keyword in combined_text for keyword in ['outage', 'downtime', 'critical']):
            severity = "ÉLEVÉE"
        else:
            severity = "MOYENNE"
        
        return MongoDBAlert(
            title=alert_data['title'],
            description=alert_data['description'],
            severity=severity,
            alert_type=alert_type,
            date=alert_data['date'],
            url=alert_data['url'],
            affected_versions=alert_data['affected_versions']
        )
    
    def generate_alerts_json(self, alerts: List[MongoDBAlert]) -> List[Dict]:
        """Génère le JSON des alertes"""
        return [
            {
                "technologie": "MongoDB",
                "type": alert.alert_type,
                "severite": alert.severity,
                "version": ", ".join(alert.affected_versions) if alert.affected_versions else "Non spécifiée",
                "titre": alert.title,
                "description": alert.description,
                "date": alert.date,
                "url": alert.url
            }
            for alert in alerts
        ]
    
    def run(self):
        """Exécute le scraping et génère le fichier JSON"""
        print("\n" + "="*50)
        print(f"Scraping des alertes MongoDB - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*50)
        
        # Scraping
        raw_alerts = self.scrape_alerts_page()
        
        if not raw_alerts:
            print("⚠️ Aucune alerte trouvée sur la page")
            raw_alerts = []
        
        # Classification
        classified_alerts = []
        for alert_data in raw_alerts:
            try:
                # Utiliser les nouvelles fonctions de classification
                alert_type = self._classify_alert(
                    alert_data.get('title', ''),
                    alert_data.get('description', ''),
                    alert_data.get('section_type', 'General')
                )
                severity = self._determine_severity(
                    alert_data.get('title', ''),
                    alert_data.get('description', ''),
                    alert_type
                )
                
                alert = MongoDBAlert(
                    title=alert_data['title'],
                    description=alert_data['description'],
                    severity=severity,
                    alert_type=alert_type,
                    date=alert_data['date'],
                    url=alert_data['url'],
                    affected_versions=alert_data['affected_versions']
                )
                classified_alerts.append(alert)
                print(f"✅ {alert_type} - {severity}: {alert.title[:60]}...")
            except Exception as e:
                print(f"Erreur classification: {e}")
        
        # Génération JSON
        alerts_json = self.generate_alerts_json(classified_alerts)
        
        # Sauvegarde
        with open(CONFIG['alerts_file'], 'w', encoding='utf-8') as f:
            json.dump(alerts_json, f, indent=4, ensure_ascii=False)
        
        print(f"\n📊 {len(alerts_json)} alertes sauvegardées dans {CONFIG['alerts_file']}")
        
        # Résumé
        summary = {}
        for alert in classified_alerts:
            key = f"{alert.alert_type} - {alert.severity}"
            summary[key] = summary.get(key, 0) + 1
        
        if summary:
            print("\n📈 Résumé des alertes:")
            for key, count in sorted(summary.items()):
                print(f"   • {key}: {count}")

if __name__ == "__main__":
    scraper = MongoDBAlertsScraper()
    scraper.run()
