from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import json
import time

# ===================== CONFIGURATION CHROME =====================
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
wait = WebDriverWait(driver, 10)

# ===================== URL PRINCIPALE =====================
url = "https://www.cockroachlabs.com/docs/releases"
driver.get(url)

result = []

# ===================== CHERCHER LES H4 avec "releases" =====================
h4_elements = driver.find_elements(By.TAG_NAME, "h4")
for h4 in h4_elements:
    if "releases" in h4.text.lower():
        try:
            # attendre que le tableau suivant le h4 soit chargé
            table = wait.until(EC.presence_of_element_located(
                (By.XPATH, ".//following-sibling::table[1]")
            ))
            tbody = table.find_element(By.TAG_NAME, "tbody")
            # récupérer tous les liens dans le tbody
            links = tbody.find_elements(By.XPATH, ".//td/a")
            
            for a_tag in links:
                version_link = a_tag.get_attribute("href")
                version_text = a_tag.text.strip()
                
                # ===================== ACCÉDER À LA PAGE DE VERSION =====================
                driver.get(version_link)
                time.sleep(1)  # attendre le rendu JS

                changes = []
                try:
                    # trouver le h3 "Changelog"
                    h3_elements = driver.find_elements(By.TAG_NAME, "h3")
                    for h3 in h3_elements:
                        if "changelog" in h3.text.lower():
                            # récupérer tous les éléments suivants jusqu'au prochain h2 version
                            following_elements = h3.find_elements(By.XPATH, "following-sibling::*")
                            for el in following_elements:
                                if el.tag_name == "h2" and any(c.isdigit() for c in el.text):
                                    break
                                text = el.text.strip()
                                if text:
                                    changes.append(text)
                            break
                except:
                    pass

                result.append({
                    "version": version_text,
                    "patch": version_text,  # si tu veux, tu peux extraire juste le numéro de patch
                    "changes": changes
                })
        except TimeoutException:
            print("Tableau non trouvé après", h4.text)
        break  # si tu veux juste le premier h4 releases

# ===================== AFFICHER LE JSON =====================
print(json.dumps(result, indent=2, ensure_ascii=False))
driver.quit()
