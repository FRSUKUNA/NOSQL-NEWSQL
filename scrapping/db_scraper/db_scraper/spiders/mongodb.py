from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import re
import time

# ===================== CONFIGURATION CHROME =====================
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

try:
    # ===================== PAGE PRINCIPALE DES RELEASE NOTES =====================
    MAIN_URL = "https://www.mongodb.com/docs/manual/release-notes/"
    driver.get(MAIN_URL)
    time.sleep(2)  # laisser le JS charger les liens

    # ===================== RÉCUPÉRER TOUS LES HREFS VIA JS =====================
    hrefs = driver.execute_script("""
        let links = document.querySelectorAll('a');
        let urls = [];
        links.forEach(a => urls.push(a.href));
        return urls;
    """)

    # ===================== FILTRER LES PAGES DE VERSIONS MAJEURES =====================
    major_links = set()
    for href in hrefs:
        if href and re.search(r"/docs/manual/release-notes/\d+\.\d+/$", href):
            major_links.add(href)

    print(f"{len(major_links)} pages de versions majeures détectées.")

    all_versions = []

    # ===================== SCRAPER CHAQUE PAGE DE VERSION =====================
    for url in sorted(major_links):  # tri pour ordre croissant
        driver.get(url)
        try:
            patch_header = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(text(),'Patch Releases')]")
                )
            )
            parent_section = patch_header.find_element(By.XPATH, "./parent::*")
            text_content = parent_section.text.split("\n")
            pattern = re.compile(r"(\d+\.\d+\.\d+)\s*-\s*(.+)")
            for line in text_content:
                match = pattern.match(line.strip())
                if match:
                    all_versions.append({
                        "version": match.group(1),
                        "date": match.group(2),
                        "major_page": url
                    })
        except:
            print(f"Aucun patch release trouvé sur {url}")
            continue

    # ===================== SAUVEGARDER DANS JSON =====================
    with open("mongodb_all_versions.json", "w", encoding="utf-8") as f:
        json.dump(all_versions, f, ensure_ascii=False, indent=4)

    print(f"{len(all_versions)} versions totales récupérées et sauvegardées dans mongodb_all_versions.json")

finally:
    driver.quit()
