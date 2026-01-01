from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import json
import re
import time

def safe_find_element(parent, by, value, max_retries=3):
    """Trouve un élément avec gestion des erreurs et des réessais"""
    for attempt in range(max_retries):
        try:
            if parent is None:
                return None
            element = parent.find_element(by, value)
            if element:
                return element
        except Exception as e:
            if "stale element" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"  - Erreur lors de la recherche de l'élément: {str(e)[:100]}...")
            return None
    return None

def safe_find_elements(parent, by, value, max_retries=3):
    """Trouve des éléments avec gestion des erreurs et des réessais"""
    for attempt in range(max_retries):
        try:
            if parent is None:
                return []
            elements = parent.find_elements(by, value)
            if elements:
                return elements
            return []
        except Exception as e:
            if "stale element" in str(e).lower() and attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"  - Erreur lors de la recherche d'éléments: {str(e)[:100]}...")
            return []
    return []

def get_stable_element(driver, by, value, max_retries=3):
    """Récupère un élément de manière stable avec des réessais"""
    for attempt in range(max_retries):
        try:
            element = driver.find_element(by, value)
            # Vérifier que l'élément est toujours valide
            element.is_displayed()
            return element
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            time.sleep(1)
    return None

def process_patch_item(item, driver, major_version):
    """Traite un élément de patch individuel"""
    try:
        version_text = item.text.strip()
        if not version_text:
            return None

        # Récupérer le lien si disponible
        link = ''
        link_elem = safe_find_element(item, By.TAG_NAME, 'a')
        if link_elem:
            link = link_elem.get_attribute('href') or ''

        # Structure de données pour le patch
        version_data = {
            'version': '',
            'date': '',
            'link': link,
            'changes': {
                'improvements': [],
                'bug_fixes': []
            }
        }

        # Extraire le numéro de version et la date
        match = re.match(r"(\d+\.\d+\.\d+)(?:\s*:\s*(\d{4}-\d{2}-\d{2}))?", version_text)
        if match:
            version_number = match.group(1)
            version_data['version'] = version_number
            if match.group(2):
                version_data['date'] = match.group(2).strip()

            # Extraire les changements si un lien est disponible
            if link and 'tidb' in link:
                print(f"\nExtraction des changements pour {version_number}...")
                changes = extract_changes(driver, link, f"{major_version} - {version_number}")
                version_data['changes'] = changes
            else:
                print(f"\nAucun lien valide pour {version_number}")

        else:
            version_data['version'] = version_text

        return version_data

    except Exception as e:
        print(f"Erreur lors du traitement d'un patch: {str(e)[:200]}...")
        return None

def extract_changes(driver, url, version_info):
    """Extrait les améliorations et corrections de bugs depuis une URL de version"""
    print(f"\nTraitement de la version {version_info}...")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"  - Tentative {attempt + 1}/{max_retries}")
            # IMPORTANT: ne pas quitter la page principale (release-notes), sinon les éléments deviennent stale.
            # On ouvre le lien du patch dans un nouvel onglet, on scrape, puis on revient.
            main_handle = driver.current_window_handle
            existing_handles = set(driver.window_handles)
            driver.execute_script("window.open(arguments[0], '_blank');", url)

            WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(existing_handles))
            new_handles = [h for h in driver.window_handles if h not in existing_handles]
            if not new_handles:
                raise RuntimeError("Impossible d'ouvrir un nouvel onglet pour scraper le patch")
            patch_handle = new_handles[-1]
            driver.switch_to.window(patch_handle)

            changes = {
                'improvements': [],
                'bug_fixes': []
            }
            
            # Attendre que la page se charge
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h2"))
                )
                time.sleep(2)  # Attente supplémentaire pour le chargement
            except TimeoutException:
                print(f"  - Timeout lors du chargement de la page {url}")
                # Toujours fermer l'onglet patch et revenir sur l'onglet principal
                try:
                    driver.close()
                finally:
                    driver.switch_to.window(main_handle)

                if attempt == max_retries - 1:
                    return changes
                continue
            
            # Trouver tous les h2 avec gestion des éléments obsolètes
            h2_elements = safe_find_elements(driver, By.TAG_NAME, "h2")
        
            for i in range(len(h2_elements)):
                try:
                    # Re-récupérer l'élément à chaque itération pour éviter les problèmes de stale elements
                    current_h2s = safe_find_elements(driver, By.TAG_NAME, "h2")
                    if not current_h2s or i >= len(current_h2s):
                        continue
                        
                    h2 = current_h2s[i]
                    section_type = None
                    text = h2.text.lower()
                    
                    # Déterminer le type de section (plus flexible sur la correspondance)
                    if 'improvement' in text or 'new feature' in text:
                        section_type = 'improvements'
                    elif ('bug' in text and 'fix' in text) or 'bugfix' in text:
                        section_type = 'bug_fixes'
                    
                    if section_type:
                        print(f"  - Extraction des {section_type}...")
                        
                        # Trouver le prochain ul après le h2
                        try:
                            # Essayer de trouver le prochain ul frère
                            next_ul = h2.find_element(By.XPATH, "following-sibling::ul[1]")
                            if next_ul:
                                items = safe_find_elements(next_ul, By.TAG_NAME, "li")
                                for item in items:
                                    changes[section_type].append(item.text.strip())
                                print(f"    - {len(items)} éléments trouvés")
                                continue  # Passer à la section suivante si on a trouvé des éléments
                        except Exception as e:
                            print(f"    - Erreur avec le premier ul: {str(e)[:100]}...")
                        
                        # Si on arrive ici, essayer une méthode alternative pour trouver le ul
                        try:
                            xpath = f"//h2[contains(., '{h2.text[:30]}')]/following::ul[1]"
                            next_ul = driver.find_element(By.XPATH, xpath)
                            if next_ul:
                                items = safe_find_elements(next_ul, By.TAG_NAME, "li")
                                for item in items:
                                    changes[section_type].append(item.text.strip())
                                print(f"    - {len(items)} éléments trouvés (méthode alternative)")
                        except Exception as e:
                            print(f"    - Aucun élément trouvé pour la section {section_type}: {str(e)[:100]}...")
                            
                except Exception as e:
                    print(f"    - Erreur lors du traitement d'une section: {str(e)[:100]}...")
                    continue
        
            # Si on a trouvé des changements, on peut sortir de la boucle de tentatives
            if any(changes.values()):
                try:
                    driver.close()
                finally:
                    driver.switch_to.window(main_handle)
                return changes

            # Si aucun changement n'a été trouvé, on ferme l'onglet quand même et on réessaie si besoin
            try:
                driver.close()
            finally:
                driver.switch_to.window(main_handle)
                
        except Exception as e:
            print(f"  - Erreur lors de l'extraction des changements (tentative {attempt + 1}): {str(e)[:200]}...")
            # Sécurité: si on a ouvert un onglet patch, le fermer et revenir sur l'onglet principal
            try:
                if len(driver.window_handles) > 1 and driver.current_window_handle != driver.window_handles[0]:
                    driver.close()
            except Exception:
                pass
            try:
                driver.switch_to.window(driver.window_handles[0])
            except Exception:
                pass

            if attempt == max_retries - 1:
                print("  - Nombre maximum de tentatives atteint, passage à la version suivante...")
                return {'improvements': [], 'bug_fixes': []}
            time.sleep(2)  # Attendre avant de réessayer
    
    return {'improvements': [], 'bug_fixes': []}

# ===================== CONFIGURATION CHROME =====================
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-notifications")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--ignore-certificate-errors")
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--allow-running-insecure-content")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Désactiver le chargement des images pour accélérer le scraping
prefs = {
    'profile.managed_default_content_settings.images': 2,
    'profile.managed_default_content_settings.javascript': 1,
    'profile.managed_default_content_settings.stylesheets': 1,
    'profile.managed_default_content_settings.cookies': 1,
    'profile.managed_default_content_settings.plugins': 1,
    'profile.managed_default_content_settings.popups': 2,
    'profile.managed_default_content_settings.geolocation': 2,
    'profile.managed_default_content_settings.media_stream': 2,
}
chrome_options.add_experimental_option('prefs', prefs)
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

try:
    MAIN_URL = "https://docs.pingcap.com/tidb/stable/release-notes"
    driver.get(MAIN_URL)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/div/div/main/div/div[1]/div[1]/div[1]/div"))
    )
    time.sleep(1)

    container = driver.find_element(By.XPATH, "/html/body/div[1]/div[1]/div/div/main/div/div[1]/div[1]/div[1]/div")
    h2_elements = container.find_elements(By.TAG_NAME, "h2")
    # Liste stable (strings) pour éviter les stale element reference lors de l'itération
    major_versions = [h.text.strip() for h in h2_elements if h.text and h.text.strip()]

    result = []

    for major_version in major_versions:
        try:
            print(f"\nTraitement de la version {major_version}...")
            patches = []

            # Re-trouver le h2 à partir de son texte (évite les références obsolètes)
            h2 = safe_find_element(container, By.XPATH, f".//h2[normalize-space()='{major_version}']")
            if not h2:
                h2 = safe_find_element(container, By.XPATH, f".//h2[contains(normalize-space(.), '{major_version}')]")
            if not h2:
                print(f"  - Impossible de retrouver le h2 pour la version {major_version}")
                continue

            # Trouver le prochain élément après le h2 (en relatif)
            next_element = safe_find_element(h2, By.XPATH, "./following-sibling::*[1]")
            
            # Parcourir les éléments suivants jusqu'au prochain h2
            while next_element and next_element.tag_name != 'h2':
                if next_element.tag_name == 'ul':
                    # Récupérer tous les éléments li dans l'ul
                    patch_items = safe_find_elements(next_element, By.TAG_NAME, "li")

                    # Boucle anti-stale: re-récupérer le li par index à chaque itération
                    for i in range(len(patch_items)):
                        current_items = safe_find_elements(next_element, By.TAG_NAME, "li")
                        if i >= len(current_items):
                            break
                        item = current_items[i]
                        patch = process_patch_item(item, driver, major_version)
                        if patch:
                            patches.append(patch)
                
                # Passer à l'élément suivant
                try:
                    next_element = next_element.find_element(By.XPATH, "./following-sibling::*[1]")
                except (NoSuchElementException, StaleElementReferenceException):
                    break

            if patches:
                result.append({
                    'major_version': major_version,
                    'patches': patches
                })
                print(f"  - {major_version}: {len(patches)} patches traités avec succès")
            else:
                print(f"  - Aucun patch trouvé pour la version {major_version}")
                
        except Exception as e:
            print(f"Erreur lors du traitement de la version {major_version if 'major_version' in locals() else 'inconnue'}: {str(e)[:200]}...")
            continue


    # ===================== SAUVEGARDE =====================
    # Enregistrer les résultats dans un fichier JSON avec le format demandé
    with open("..\\..\\..\\..\\..\\API\\sources\\tidb-versions.json", 'w', encoding='utf-8') as f:
        output = []
        for major in result:
            major_version = major.get('major_version', '')
            for patch in major.get('patches', []) or []:
                # Aplatir les changements
                changes = patch.get('changes', {})
                flat_changes = []
                if isinstance(changes, dict):
                    improvements = changes.get('improvements', [])
                    bug_fixes = changes.get('bug_fixes', [])
                    if isinstance(improvements, list):
                        flat_changes.extend(improvements)
                    if isinstance(bug_fixes, list):
                        flat_changes.extend(bug_fixes)
                elif isinstance(changes, list):
                    flat_changes = changes

                # Créer l'entrée au format demandé
                output.append({
                    "database": "Tidb",
                    "major_version": major_version,
                    "patch_version": patch.get('version', ''),
                    "date": patch.get('date', ''),
                    "changes": flat_changes
                })

        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print("Scraping terminé avec succès!")
    print(f"{len(result)} versions majeures trouvées.")
    for version in result:
        print(f"\n{version['major_version']} ({len(version['patches'])} patches):")
        for patch in version['patches']:
            print(f"- {patch['version']}")

except Exception as e:
    print(f"Une erreur s'est produite : {str(e)}")
    raise e

finally:
    driver.quit()
