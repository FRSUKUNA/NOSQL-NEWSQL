import schedule
import time
import subprocess
import sys
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "scheduler.log")

SCRAPERS = [
    "../scrapping/db_scraper/db_scraper/spiders/Cassandra/Cassandra.py",
    "../scrapping/db_scraper/db_scraper/spiders/mongodb/mongodb.py",
    "../scrapping/db_scraper/db_scraper/spiders/redis/redis.py",
    "../scrapping/db_scraper/db_scraper/spiders/tidb/tidb.py",
    "../scrapping/db_scraper/db_scraper/spiders/yugabyte/yugabyte.py",
    "../scrapping/db_scraper/db_scraper/spiders/Neo4j/Neo4j.py",
    "../scrapping/db_scraper/db_scraper/spiders/cockroachdb/cockroachdb.py",
]

PIPELINE = [
    "clean.py",
    "etape2.py",
    "etape1.py",
    "ACID.py",
    "alert.py",
    "innovation.py",
    "remove-changes.py",
    "sync.py",
]

# ===================== LOG =====================
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ===================== RUN SCRIPT =====================
def run_script(script_path, stop_on_error=True):
    full_path = os.path.join(BASE_DIR, script_path)
    log(f"🚀 Lancement : {script_path}")

    try:
        subprocess.run(
            [sys.executable, full_path],
            check=True
        )
        log(f"✅ Terminé : {script_path}")

    except subprocess.CalledProcessError:
        log(f"❌ ERREUR : {script_path}")
        if stop_on_error:
            raise

# ===================== JOB =====================
def job():
    log("===== JOB DÉMARRÉ =====")

    log("PHASE 1 : SCRAPPING")
    for s in SCRAPERS:
        run_script(s, stop_on_error=False)

    log("PHASE 2 : PIPELINE")
    for p in PIPELINE:
        run_script(p, stop_on_error=True)

    log("===== JOB TERMINÉ =====\n")

# ===================== SCHEDULE =====================
# Lancer toutes les 12 heures
schedule.every(12).hours.do(job)

log("⏱️ Scheduler lancé pour toutes les 12 heures...")

# ───── PREMIER RUN IMMÉDIAT ─────
log("⏳ Exécution immédiate du pipeline...")
job()

# ───── BOUCLE DE SCHEDULER ─────
while True:
    schedule.run_pending()
    time.sleep(30)
