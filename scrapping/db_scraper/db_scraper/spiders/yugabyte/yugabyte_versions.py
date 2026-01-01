
import json
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

DOC_2025_1_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/v2025.1/'
DOC_2025_2_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/v2025.2/'
DOC_2024_1_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/v2024.1/'
DOC_2024_2_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/v2024.2/'

DOC_2_12_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.12/'
DOC_2_13_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.13/'
DOC_2_14_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.14/'
DOC_2_15_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.15/'
DOC_2_16_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.16/'
DOC_2_17_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.17/'
DOC_2_18_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.18/'
DOC_2_19_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/end-of-life/v2.19/'
DOC_2_20_URL = 'https://docs.yugabyte.com/stable/releases/ybdb-releases/v2.20/'

ACID_URL = 'https://www.yugabyte.com/key-concepts/acid-properties/'

SECURITY_KEYWORDS = [
    "security", "vulnerability", "authentication",
    "authorization", "privilege", "bypass", "exploit", "cve"
]

PERFORMANCE_KEYWORDS = [
    "performance", "latency", "throughput", "slow", "slower", "faster",
    "optimiz", "regression", "degradation", "degrade", "bottleneck",
    "memory", "cpu", "qps", "tps", "p99", "p95"
]

MAJOR_CHANGE_KEYWORDS = [
    "major", "significant", "critical", "severe", "breaking",
    "regression", "degradation", "degrade", "outage"
]


def _parse_version_parts(tag: str) -> Optional[Dict[str, str]]:
    m = re.search(r'v?(\d+(?:\.\d+)+)', tag)
    if not m:
        return None

    version_text = m.group(1)
    parts = version_text.split('.')
    if len(parts) < 2:
        return None

    return {
        'version': parts[0],
        'patch': '.'.join(parts[1:])
    }


def _extract_releases_from_soup(soup: BeautifulSoup) -> List[Dict]:
    releases: List[Dict] = []
    seen = set()

    links = soup.select('a[href*="/yugabyte/yugabyte-db/releases/tag/"]') or soup.select('a[href*="/releases/tag/"]')
    for a in links:
        href = a.get('href', '').strip()
        text = a.get_text(strip=True)
        tag_candidate = text or (href.split('/')[-1] if href else '')

        vp = _parse_version_parts(tag_candidate)
        if not vp:
            continue
        key = f"{vp['version']}.{vp['patch']}"
        if key in seen:
            continue
        seen.add(key)

        # Date: chercher un relative-time dans les parents
        date_tag = None
        parent = a
        for _ in range(0, 6):
            if parent is None:
                break
            date_tag = parent.select_one('relative-time')
            if date_tag:
                break
            parent = parent.parent

        if not date_tag or not date_tag.get('datetime'):
            formatted_date = 'Date non disponible'
        else:
            try:
                date_obj = datetime.strptime(date_tag['datetime'], '%Y-%m-%dT%H:%M:%SZ')
                formatted_date = date_obj.strftime('%Y-%m-%d')
            except Exception:
                formatted_date = 'Date non disponible'

        releases.append({
            **vp,
            'date': formatted_date,
            'url': f"https://github.com{href}" if href.startswith('/') else f"https://github.com/yugabyte/yugabyte-db/releases/tag/v{key}",
        })

    return releases


def _fetch_soup(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, 'html.parser')
    except Exception:
        return None


def _extract_doc_changes_for_series(session: requests.Session, doc_url: str) -> Dict[str, Dict[str, object]]:
    """Retourne un mapping: '2025.1.2.2' -> {'date': 'YYYY-MM-DD'|'Date non disponible', 'changes': [..]}"""
    soup = _fetch_soup(session, doc_url)
    if not soup:
        return {}

    # La doc est structurée en headings contenant 'v2025.x.y.z - <date>' ou 'v2.x.y.z - <date>'
    headings = soup.find_all(['h2', 'h3'])
    versions: List[Dict[str, object]] = []
    for h in headings:
        title = h.get_text(' ', strip=True)
        m = re.search(
            r'v(?P<ver>(?:(?:2024|2025)\.(?:1|2)\.\d+\.\d+)|(?:2\.\d+\.\d+\.\d+))\s*-\s*(?P<date>.+)$',
            title,
        )
        if not m:
            continue
        full_version = m.group('ver').strip()
        date_text = m.group('date').strip()
        versions.append({'full_version': full_version, 'heading': h, 'date_text': date_text})

    if not versions:
        return {}

    def _normalize_date(date_text: str) -> str:
        # Ex: 'December 17, 2025'
        try:
            dt = datetime.strptime(date_text, '%B %d, %Y')
            return dt.strftime('%Y-%m-%d')
        except Exception:
            return 'Date non disponible'

    out: Dict[str, Dict[str, object]] = {}
    for idx, v in enumerate(versions):
        h = v['heading']
        next_h = versions[idx + 1]['heading'] if idx + 1 < len(versions) else None
        
        changes: List[str] = []
        node = h.next_sibling
        while node is not None and node is not next_h:
            # Certains parsers mettent des \n en tant que NavigableString; ignorer
            try:
                if getattr(node, 'name', None) in ['ul', 'ol']:
                    for li in node.find_all('li'):
                        text = li.get_text(' ', strip=True)
                        if text and len(text) >= 10:
                            changes.append(text)
                elif getattr(node, 'name', None) in ['p']:
                    text = node.get_text(' ', strip=True)
                    if text and len(text) >= 10 and not text.lower().startswith('downloads'):
                        changes.append(text)
            except Exception:
                pass
            node = getattr(node, 'next_sibling', None)

        out[v['full_version']] = {
            'date': _normalize_date(v['date_text']),
            'changes': list(dict.fromkeys(changes))
        }

    return out


def get_doc_changes_cache(session: requests.Session) -> Dict[str, Dict[str, object]]:
    """Cache doc: combine v2025.1 + v2025.2."""
    cache: Dict[str, Dict[str, object]] = {}
    cache.update(_extract_doc_changes_for_series(session, DOC_2024_1_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2024_2_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2025_1_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2025_2_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_12_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_13_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_14_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_15_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_16_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_17_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_18_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_19_URL))
    cache.update(_extract_doc_changes_for_series(session, DOC_2_20_URL))
    return cache


def _should_use_docs(full_version: str) -> bool:
    if full_version.startswith('2024.1.') or full_version.startswith('2024.2.') or full_version.startswith('2025.1.') or full_version.startswith('2025.2.'):
        return True

    # Ex: 2.12.6.0 => versions 2.12.* à 2.20.*
    if full_version.startswith('2.'):
        parts = full_version.split('.')
        if len(parts) >= 2 and parts[1].isdigit():
            minor = int(parts[1])
            return 12 <= minor <= 20
    return False


def get_acid_consistency(session: requests.Session) -> Dict[str, str]:
    defaults = {
        'atomicity': 'Atomicity ensures a transaction is treated as a single unit of work: either all operations succeed, or none are applied.',
        'consistency': 'Consistency ensures each transaction moves the database from one valid state to another, respecting integrity constraints.',
        'isolation': 'Isolation ensures concurrently running transactions do not interfere with each other; intermediate states are not visible to others.',
        'durability': 'Durability ensures once a transaction is committed, its effects persist even after crashes or failures.',
        'acid_vs_cap_consistency': 'In ACID, consistency refers to integrity constraints and valid states, while CAP consistency (often strong consistency/linearizability) refers to what reads are allowed to observe in a distributed system.',
        'what_is_acid_database': 'An ACID-compliant database upholds Atomicity, Consistency, Isolation, and Durability for reliable transactions.'
    }

    try:
        soup = _fetch_soup(session, ACID_URL)
        if not soup:
            # Fallback requête directe avec headers plus complets
            try:
                resp = requests.get(
                    ACID_URL,
                    headers={
                        **headers,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
                        'Referer': 'https://www.yugabyte.com/'
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
            except Exception:
                return defaults

        # 1) Extraction structurée: headings + paragraphes
        def _extract_after_heading(heading_text: str) -> str:
            h = soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3', 'h4'] and heading_text.lower() in tag.get_text(' ', strip=True).lower())
            if not h:
                return ''
            parts: List[str] = []
            node = h.find_next_sibling()
            while node is not None:
                if getattr(node, 'name', None) in ['h1', 'h2', 'h3', 'h4']:
                    break
                if getattr(node, 'name', None) in ['p', 'li']:
                    txt = node.get_text(' ', strip=True)
                    if txt and len(txt) >= 20:
                        parts.append(txt)
                node = node.find_next_sibling()
                if len(parts) >= 5:
                    break
            return ' '.join(parts).strip()

        result = {
            'what_is_acid_database': _extract_after_heading('What is an ACID database?'),
            'acid_vs_cap_consistency': _extract_after_heading('What is the Difference Between ACID Consistency and CAP Theorem Consistency?'),
        }

        # Les pages marketing peuvent ne pas avoir de sections dédiées pour Atomicity/Consistency/Isolation/Durability.
        # On tente une extraction par regex sur tout le texte.
        text = soup.get_text('\n', strip=True)

        def _extract_sentence_block(keyword: str) -> str:
            m = re.search(rf'\b{re.escape(keyword)}\b[^\n]{{0,600}}', text, flags=re.IGNORECASE)
            return m.group(0).strip() if m else ''

        for k in ['atomicity', 'consistency', 'isolation', 'durability']:
            result[k] = _extract_sentence_block(k)

        # Nettoyage: fallback sur defaults si champs vides
        out = {}
        for k, default_val in defaults.items():
            val = result.get(k, '')
            if val:
                out[k] = val
            else:
                out[k] = default_val

        return out
    except Exception:
        return defaults


def _classify_change(change: str) -> Optional[Dict[str, str]]:
    """Retourne None si pas d'alerte, sinon {'type': ..., 'severity': ...}."""
    c = change.lower()

    is_security = any(k in c for k in SECURITY_KEYWORDS)
    is_perf = any(k in c for k in PERFORMANCE_KEYWORDS)
    is_major = any(k in c for k in MAJOR_CHANGE_KEYWORDS)

    # 1) Vulnérabilité critique: CVE / exploit / bypass / privilege escalation / vuln
    if is_security:
        if any(k in c for k in ["cve", "exploit", "bypass", "privilege", "escalat", "vulnerability", "security fix"]):
            return {'type': 'VULNERABILITÉ', 'severity': 'Critique'}
        # Mention sécurité plus faible => pas d'alerte (conformément à ta règle "vulnérabilité critique")
        return None

    # 2) Changement majeur de performance: régression/dégradation ou mention perf + "major" etc.
    if is_perf:
        if any(k in c for k in ["regression", "degradation", "degrade", "outage"]):
            return {'type': 'PERFORMANCE', 'severity': 'Critique'}
        if is_major:
            return {'type': 'PERFORMANCE', 'severity': 'Élevée'}
        return None

    return None


def detect_alerts(version_data: Dict) -> List[Dict]:
    alerts: List[Dict] = []
    version_str = f"{version_data.get('version', '')}.{version_data.get('patch', '')}".strip('.')
    date_str = version_data.get('date', 'Date non disponible')

    for change in version_data.get('changes', []) or []:
        if not isinstance(change, str):
            continue

        classification = _classify_change(change)
        if not classification:
            continue

        alerts.append({
            "technology": "YugabyteDB",
            "type": classification['type'],
            "severity": classification['severity'],
            "version": version_str,
            "description": change,
            "date": date_str
        })

    return alerts


def get_all_releases(max_pages: int = 25) -> List[Dict]:
    print(f"Récupération des versions YugabyteDB sur GitHub (pages 1..{max_pages})...")

    session = requests.Session()
    session.headers.update({
        **headers,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8'
    })

    all_releases: List[Dict] = []
    seen = set()

    for page in range(1, max_pages + 1):
        url = f"https://github.com/yugabyte/yugabyte-db/releases?page={page}"
        print(f"Page {page}/{max_pages}...", end=' ', flush=True)

        try:
            soup = _fetch_soup(session, url)
            if not soup:
                print("Erreur de lecture")
                break

            page_releases = _extract_releases_from_soup(soup)
            for r in page_releases:
                key = f"{r['version']}.{r['patch']}"
                if key in seen:
                    continue
                seen.add(key)
                all_releases.append(r)

            print(f"OK (+{len(page_releases)}, total={len(all_releases)})")
            time.sleep(0.1)

        except Exception as e:
            print(f"Erreur: {e}")
            break

    return all_releases


def get_release_changes(release_url: str) -> List[str]:
    try:
        resp = requests.get(release_url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        content = soup.find('div', class_='markdown-body') or soup.find('div', class_='release-body')
        if not content:
            return []

        items = []

        # Priorité: puces
        for li in content.find_all('li'):
            text = li.get_text(' ', strip=True)
            if text and len(text) >= 10:
                items.append(text)

        if items:
            return list(dict.fromkeys(items))

        # Fallback: lignes de texte
        text = content.get_text('\n', strip=True)
        for line in text.split('\n'):
            line = line.strip('-•* \t').strip()
            if line and len(line) >= 10:
                items.append(line)

        return list(dict.fromkeys(items))

    except Exception:
        return []


def get_release_changes_with_session(session: requests.Session, release_url: str) -> List[str]:
    try:
        resp = session.get(release_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        content = soup.find('div', class_='markdown-body') or soup.find('div', class_='release-body')
        if not content:
            return []

        items: List[str] = []
        for li in content.find_all('li'):
            text = li.get_text(' ', strip=True)
            if text and len(text) >= 10:
                items.append(text)

        if items:
            return list(dict.fromkeys(items))

        text = content.get_text('\n', strip=True)
        for line in text.split('\n'):
            line = line.strip('-•* \t').strip()
            if line and len(line) >= 10:
                items.append(line)

        return list(dict.fromkeys(items))
    except Exception:
        return []


def main():
    # Session partagée pour accélérer
    session = requests.Session()
    session.headers.update({
        **headers,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8'
    })

    releases = get_all_releases(max_pages=25)
    if not releases:
        print('Aucune version trouvée')
        return

    # Charger une seule fois les pages docs 2025.1 / 2025.2
    doc_cache = get_doc_changes_cache(session)

    acid_consistency = get_acid_consistency(session)

    # Trier du plus récent au plus ancien
    def sort_key(r: Dict) -> List[int]:
        parts = [int(r['version'])]
        for p in r['patch'].split('.'):
            parts.append(int(p) if p.isdigit() else 0)
        while len(parts) < 4:
            parts.append(0)
        return parts

    releases.sort(key=sort_key, reverse=True)

    # Préparer les jobs: pour 2025.1/2025.2 on utilise la doc (rapide), sinon GitHub release.
    output: List[Dict] = []
    pending = []

    for r in releases:
        full_version = f"{r['version']}.{r['patch']}"

        # cas: versions supportées par la doc => récupérer depuis docs
        if _should_use_docs(full_version):
            doc = doc_cache.get(full_version)
            if doc:
                output.append({
                    'version': r['version'],
                    'patch': r['patch'],
                    'date': doc.get('date', r['date']),
                    'changes': doc.get('changes', [])
                })
            else:
                # fallback GitHub si pas trouvé dans la doc
                pending.append(r)
        else:
            pending.append(r)

    # Accélération: fetch GitHub changes en parallèle (limité)
    max_workers = 8
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        future_map = {
            ex.submit(get_release_changes_with_session, session, r['url']): r
            for r in pending
        }
        for fut in as_completed(future_map):
            r = future_map[fut]
            full_version = f"{r['version']}.{r['patch']}"
            try:
                changes = fut.result()
            except Exception:
                changes = []
            output.append({
                'version': r['version'],
                'patch': r['patch'],
                'date': r['date'],
                'changes': changes
            })

    # Re-trier (car exécution parallèle => ordre non déterministe)
    output.sort(key=lambda x: [int(x['version'])] + [int(p) if p.isdigit() else 0 for p in x['patch'].split('.')], reverse=True)

    alerts: List[Dict] = []
    for version_data in output:
        alerts.extend(detect_alerts(version_data))

    output_file = "..\..\..\..\..\API\sources\yugabyte-versions.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(
            [
                {    
                    'database': 'YugabyteDB',
                    'major_version': v.get('version', ''),
                    'patch_version': f"{v.get('version', '')}.{v.get('patch', '')}".strip('.'),
                    'date': v.get('date', ''),
                    'changes': v.get('changes', []) or [],
                }
                for v in output
            ],
            f,
            indent=4,
            ensure_ascii=False,
        )

    alerts_file = 'yugabyte_alert.json'
    with open(alerts_file, 'w', encoding='utf-8') as f:
        json.dump(alerts, f, indent=4, ensure_ascii=False)

    print(f"\nRapport sauvegardé dans {output_file}")
    print(f"Versions: {len(output)}")
    print(f"Alertes sécurité: {len(alerts)}")


if __name__ == '__main__':
    main()
