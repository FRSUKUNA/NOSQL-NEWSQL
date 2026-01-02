import json
import os
import re
from collections import defaultdict
from typing import Dict, List, Union

# ==============================
# CONFIGURATION
# ==============================
INPUT_DIR = "sources"
OUTPUT_DIR = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================
# DICTIONNAIRE INTELLIGENT (IA MÉTIER)
# ==============================
CATEGORIES = {
    "performance": [
        "performance", "optimize", "latency", "throughput","improvement","enhance"
        "scalability", "speed", "faster", "timeout","reduce","adds",
        "metrics", "eviction","improve","efficiency","improving","update",
        "reduce", "contention", "allocation", "cache", "memory", "fast", "efficient",
        "lazy", "eager", "resource", "io", "disk", "cpu", "network", "bandwidth",
        "compression", "decompression", "serialize", "deserialize", "bottleneck", "overhead",
        "compaction", "sstables", "cql", "nodetool", "repair", "replication", "consistency",
        "shard", "sharding", "balancer", "chunk", "oplog", "replica", "rs", "transaction",
        "sql", "query", "index", "range", "replica", "plan", "execution", "optimizer",
        "slow", "slowdown", "delay", "concurrency", "hotspot", "optimized",
        "ysql", "tablet", "yb", "cluster", "master", "split", "tserver", "node", "leader",
        "async", "balance", "batch", "buffer", "clock", "consensus", "election", "follower", "heartbeat"
    ],
    "bug_fix": [
        "fix", "bug","bugs", "crash", "hang", "race","fixed","adjusts",
        "deadlock", "error", "fail", "issue","freaking fixes",
        "incorrect", "properly", "missing", "wrong", "broken", 
        "exception", "null", "empty", "invalid", "failure", "stale", "corrupt",
        "leak", "overflow", "underflow", "uninitialized", "unbound", "undefined",
        "malformed", "truncated", "incomplete", "outdated", "deprecated",
        "npe", "nullpointer", "concurrent", "mutation", "read", "write", "connection",
        "socket", "document", "cursor", "plan", "limit", "skip", "delete", "insert",
        "default", "type", "key", "round", "cast", "foreign", "oom", "outofmemory",
        "inconsistency", "bypass", "freeze", "livelock", "starvation", "flaky", "unstable",
        "gc", "retry", "condition", "throttle", "backoff", "reference", "pointer", "garbage"
    ],
    "new_feature": [
        "add", "introduce", "new", "support","added","allows",
        "enable", "feature", "initial", "allow", "create", 
        "implement", "provide", "extend", "offer", "build", "import", "export",
        "generate", "setup", "configure", "initialize", "register", "subscribe",
        "construct", "establish", "cqlsh", "view", "function", "trigger", "role",
        "change", "stream", "transaction", "multi", "document", "session", "concern",
        "aggregation", "pipeline", "statement", "changefeed", "json", "array", "type",
        "expose", "functionality", "publish", "capability", "deliver",
        "ysql", "ui", "ycql", "api", "cli", "schema", "admin", "tool", "migration", "utility"
    ],
    "security": [
        "security", "auth", "authentication",
        "authorization", "permission","ensures",
        "vulnerability", "cve", "encryption","secure",
        "sast", "check", "control", "validate", "verify", "restrict", "protect",
        "prevent", "filter", "block", "token", "access", "sign", "hash", "alert",
        "detect", "password", "certificate", "audit", "login", "authenticate", "authorize",
        "ssl", "tls", "role", "user", "key", "ldap", "rest", "privilege", "logging", "sql",
        "exploit", "attack", "breach", "injection", "xss", "csrf", "escalation", "hardens", "hardened",
        "ip", "proxy"
    ],
    "refactoring": [
        "refactor", "restructure", "cleanup", "simplify", "modularize",
        "refactors", "refactored", "restructures", "restructured", "cleanups", "cleaned"
    ],
    "maintenance": [
        "upgrade", "migrate", "compatibility", "deprecated", 
        "remove", "replace", "maintenance", "version", "deprecate", "deprecates",
        "downgrade", "break", "regression", "legacy", "obsolete",
        "ha", "backup", "restore", "dr", "snapshot", "checkpoint", "failover", "health", "pick", "backport"
    ],
    "monitoring": [
        "metric", "log", "track", "monitor", "observe", 
        "report", "statistics", "monitoring", "collect", "trace", "gather",
        "event", "rate", "prometheus", "availability", "status"
    ],
    "configuration": [
        "config", "setting", "option", "parameter", 
        "property", "tune", "configuration", "variable", "modify", "adjust",
        "override", "environment", "flag", "disable", "bootstrap", "gate", "restart", "runtime", "switch", "settings"
    ],
    "testing": [
        "test", "verify", "validate", "check", "assert", "testing",
        "debug", "inspect", "mock", "stub", "fixture", "benchmark", "profile",
        "load", "integration", "validation", "pending", "result", "pass"
    ]
}

# ==============================
# CLASSIFICATION D'UN CHANGEMENT
# ==============================
def classify_change(text: str) -> str:
    text = text.lower()
    scores = defaultdict(int)

    for category, keywords in CATEGORIES.items():
        for kw in keywords:
            if re.search(rf"\b{kw}\b", text):
                scores[category] += 1

    if not scores:
        return "other"

    return max(scores, key=scores.get)

# ==============================
# ANALYSE D'UN PATCH COMPLET
# ==============================
def analyze_patch(patch: Dict) -> Dict:
    summary = {
        "performance": 0,
        "bug_fix": 0,
        "new_feature": 0,
        "security": 0,
        "refactoring": 0,
        "maintenance": 0,
        "monitoring": 0,
        "configuration": 0,
        "testing": 0,
        "other": 0
    }

    details = []

    for change in patch.get("changes", []):
        category = classify_change(change)
        summary[category] += 1
        details.append({
            "description": change,
            "category": category
        })

    patch["ai_analysis"] = {
        "dominant_type": max(summary, key=summary.get),
        "summary": summary,
        "details": details
    }

    return patch

# ==============================
# TRAITEMENT DES FICHIERS JSON
# ==============================
def process_files():
    for filename in os.listdir(INPUT_DIR):
        if not filename.endswith(".json"):
            continue

        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)

        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Cas 1 : liste de patches
        if isinstance(data, list):
            analyzed_data = [analyze_patch(patch) for patch in data]

        # Cas 2 : un seul patch
        elif isinstance(data, dict):
            analyzed_data = analyze_patch(data)

        else:
            print(f"❌ Format inconnu : {filename}")
            continue

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(analyzed_data, f, indent=2, ensure_ascii=False)

        print(f"✅ Analyse IA terminée : {filename}")

# ==============================
# POINT D'ENTRÉE
# ==============================
if __name__ == "__main__":
    print("🚀 Démarrage analyse IA des patchs...\n")
    process_files()
    print("\n🎯 Analyse terminée. Fichiers enrichis dans /output")
