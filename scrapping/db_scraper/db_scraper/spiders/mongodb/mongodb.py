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
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=chrome_options
)

# ===================== PARSE CHANGELOG (VERSION CORRECTE) =====================
def parse_changelog_page(driver, major_version):
    """
    Scrape UNE SEULE FOIS le changelog X.Y
    Filtre STRICTEMENT les patchs de la version majeure courante
    """
    url = f"https://www.mongodb.com/docs/manual/release-notes/{major_version}-changelog/"
    print(f"   ↳ Chargement changelog {major_version}")
    driver.get(url)

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "h2"))
    )

    changelog = {}

    h2_elements = driver.find_elements(By.TAG_NAME, "h2")

    for h2 in h2_elements:
        title = h2.text.strip()

        # ✅ FILTRAGE STRICT PAR VERSION MAJEURE
        # ex: "7.0.25 Changelog"
        match = re.match(
            rf"^{major_version}\.(\d+)\s+Changelog",
            title
        )
        if not match:
            continue

        patch_version = f"{major_version}.{match.group(1)}"
        changes = []

        try:
            sibling = h2.find_element(By.XPATH, "following-sibling::*")
        except:
            changelog[patch_version] = []
            continue

        while sibling.tag_name == "section":
            # stop si on arrive à un autre patch
            if sibling.find_elements(By.TAG_NAME, "h2"):
                break

            for li in sibling.find_elements(By.TAG_NAME, "li"):
                txt = li.text.strip()
                if txt:
                    changes.append(txt)

            try:
                sibling = sibling.find_element(By.XPATH, "following-sibling::*")
            except:
                break

        changelog[patch_version] = changes

    return changelog

try:
    # ===================== PAGE PRINCIPALE =====================
    MAIN_URL = "https://www.mongodb.com/docs/manual/release-notes/"
    driver.get(MAIN_URL)
    time.sleep(2)

    # ===================== RÉCUPÉRER TOUS LES LIENS =====================
    hrefs = driver.execute_script("""
        return Array.from(document.querySelectorAll('a')).map(a => a.href);
    """)

    # ===================== FILTRER LES VERSIONS MAJEURES =====================
    major_links = sorted({
        href for href in hrefs
        if href and re.search(r"/docs/manual/release-notes/\d+\.\d+/$", href)
    })

    print(f"🔎 {len(major_links)} versions majeures détectées")

    result = []

    # ===================== SCRAPING GLOBAL =====================
    for url in major_links:
        driver.get(url)
        time.sleep(1)

        major_version = re.search(
            r"/release-notes/(\d+\.\d+)/", url
        ).group(1)

        print(f"\n📦 Version majeure {major_version}")

        # ---------- PATCH RELEASES ----------
        try:
            patch_header = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h2[contains(text(),'Patch Releases')]")
                )
            )

            section = patch_header.find_element(By.XPATH, "./parent::*")
            lines = section.text.split("\n")

        except:
            print("   ⚠️ Aucun patch trouvé")
            continue

        # ---------- CHARGE LE CHANGELOG UNE SEULE FOIS ----------
        changelog_cache = parse_changelog_page(driver, major_version)

        patch_pattern = re.compile(r"(\d+\.\d+\.\d+)\s*-\s*(.+)")

        for line in lines:
            match = patch_pattern.match(line.strip())
            if not match:
                continue

            patch_version = match.group(1)
            date = match.group(2)

            # ✅ Sécurité : s'assurer que le patch correspond à la version majeure
            if not patch_version.startswith(major_version + "."):
                continue

            print(f"   ➜ Patch {patch_version}")

            result.append({
                "database": "MongoDB",
                "major_version": major_version,
                "patch_version": patch_version,
                "date": date,
                "changes": changelog_cache.get(patch_version, [])
            })

    # ===================== SAUVEGARDE =====================
    with open("..\..\..\..\..\API\sources\mongodb-versions.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)

    print(f"\n✅ {len(result)} patchs sauvegardés")

finally:
    driver.quit()
