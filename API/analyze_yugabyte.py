import json
import os
import re
from collections import Counter, defaultdict
from etape2 import classify_change, CATEGORIES

def extract_yugabyte_other():
    """Extrait les descriptions 'other' spécifiquement pour YugabyteDB"""
    
    yugabyte_other = []
    filepath = os.path.join("output", "yugabyte-versions.json")
    
    if not os.path.exists(filepath):
        print("❌ Fichier yugabyte-versions.json non trouvé")
        return yugabyte_other
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    items = data if isinstance(data, list) else [data]
    
    for item in items:
        if "ai_analysis" in item and "details" in item["ai_analysis"]:
            for detail in item["ai_analysis"]["details"]:
                if detail["category"] == "other":
                    yugabyte_other.append(detail["description"])
    
    return yugabyte_other

def analyze_yugabyte_specific_patterns(descriptions):
    """Analyse les patterns spécifiques à YugabyteDB"""
    
    # Mots-clés spécifiques à YugabyteDB
    yugabyte_keywords = {
        "performance": [
            "ysql", "ycql", "yb", "tserver", "master", "tablet", "raft", "consensus", 
            "replication", "leader", "follower", "election", "heartbeat", "rpc", "async",
            "batch", "buffer", "pool", "connection", "session", "transaction", "isolation",
            "snapshot", "mvcc", "timestamp", "clock", "hybrid", "time", "htap",
            "oltp", "olap", "distributed", "cluster", "node", "zone", "region",
            "shard", "sharding", "split", "merge", "rebalance", "load", "balance",
            "compaction", "sstables", "memtable", "wal", "write", "read", "scan",
            "index", "btree", "lsm", "storage", "engine", "rocksdb", "block", "cache",
            "compression", "encoding", "decoding", "serialize", "deserialize",
            "throughput", "latency", "qps", "tps", "concurrency", "parallel",
            "optimize", "optimization", "efficient", "fast", "slow", "bottleneck"
        ],
        "bug_fix": [
            "crash", "panic", "assert", "check", "verify", "validate", "error", 
            "exception", "failure", "fail", "incorrect", "wrong", "missing", "broken",
            "corrupt", "damage", "inconsistent", "stale", "outdated", "leak", "memory",
            "deadlock", "race", "condition", "timeout", "hang", "freeze", "unresponsive",
            "disconnect", "reconnect", "retry", "backoff", "circuit", "breaker",
            "overflow", "underflow", "null", "nil", "undefined", "uninitialized",
            "unbound", "pointer", "reference", "garbage", "collect", "gc", "oom",
            "outofmemory", "resource", "exhaust", "limit", "quota", "throttle"
        ],
        "new_feature": [
            "add", "support", "enable", "allow", "implement", "introduce", "feature",
            "functionality", "capability", "extend", "provide", "offer", "create", "build",
            "ysql", "ycql", "ysqlsh", "cqlsh", "shell", "cli", "tool", "utility",
            "admin", "management", "monitor", "dashboard", "ui", "gui", "api", "rest",
            "graphql", "protobuf", "json", "avro", "schema", "migration", "upgrade",
            "version", "compatibility", "backward", "forward", "breaking", "change",
            "enhancement", "improvement", "optimization", "tuning", "parameter",
            "configuration", "setting", "option", "property", "environment", "variable"
        ],
        "security": [
            "security", "auth", "authentication", "authorization", "permission", "role",
            "user", "password", "token", "certificate", "ssl", "tls", "encryption", "decrypt",
            "secure", "protect", "validate", "verify", "check", "audit", "log", "monitor",
            "alert", "detect", "prevent", "block", "filter", "restrict", "control",
            "access", "login", "signin", "signout", "session", "cookie", "jwt", "oauth",
            "rbac", "acl", "privilege", "grant", "revoke", "firewall", "network",
            "ip", "allowlist", "denylist", "vpn", "proxy", "gateway", "middleware"
        ],
        "maintenance": [
            "maintenance", "upgrade", "migrate", "migration", "compatibility", "version",
            "deprecated", "deprecate", "remove", "delete", "cleanup", "purge", "archive",
            "backup", "restore", "snapshot", "checkpoint", "recovery", "failover", "ha",
            "high", "availability", "disaster", "recovery", "dr", "site", "replication",
            "cluster", "health", "status", "monitor", "check", "verify", "validate",
            "repair", "fix", "patch", "update", "hotfix", "backport", "cherry", "pick"
        ],
        "monitoring": [
            "metric", "metrics", "monitor", "monitoring", "track", "trace", "logging",
            "log", "audit", "report", "statistics", "measure", "collect", "gather",
            "export", "expose", "publish", "prometheus", "grafana", "influx", "timeseries",
            "alert", "notification", "email", "slack", "pagerduty", "webhook", "event",
            "health", "check", "status", "diagnostic", "debug", "profile", "performance",
            "throughput", "latency", "error", "rate", "success", "failure", "availability"
        ],
        "configuration": [
            "config", "configuration", "setting", "settings", "option", "options",
            "parameter", "parameters", "property", "properties", "tune", "tuning",
            "adjust", "modify", "change", "override", "default", "environment", "variable",
            "env", "flag", "switch", "feature", "gate", "toggle", "enable", "disable",
            "runtime", "dynamic", "reload", "restart", "reconfigure", "bootstrap"
        ],
        "testing": [
            "test", "testing", "unit", "integration", "e2e", "end", "to", "end",
            "functional", "performance", "load", "stress", "regression", "smoke",
            "sanity", "verification", "validation", "check", "verify", "assert",
            "mock", "stub", "fixture", "benchmark", "profile", "debug", "inspect",
            "trace", "coverage", "report", "result", "pass", "fail", "skip", "pending"
        ],
        "refactoring": [
            "refactor", "refactoring", "restructure", "restructuring", "cleanup",
            "clean", "simplify", "modularize", "modular", "component", "service",
            "microservice", "architecture", "design", "pattern", "practice", "code",
            "quality", "maintainability", "readability", "consistency", "standard",
            "convention", "style", "format", "lint", "static", "analysis", "review"
        ]
    }
    
    # Combiner toutes les descriptions
    all_text = " ".join(descriptions).lower()
    
    suggestions = defaultdict(list)
    
    for category, keywords in yugabyte_keywords.items():
        for keyword in keywords:
            if keyword in all_text:
                count = all_text.count(keyword)
                if count > 3:  # Seulement si apparaît fréquemment
                    # Vérifier si pas déjà dans CATEGORIES
                    already_exists = any(keyword in cat_keywords for cat_keywords in CATEGORIES.values())
                    if not already_exists:
                        suggestions[category].append((keyword, count))
    
    return suggestions

def main():
    print("🔍 Analyse spécifique de YugabyteDB...")
    yugabyte_other = extract_yugabyte_other()
    print(f"📊 YugabyteDB: {len(yugabyte_other)} descriptions dans 'other'")
    
    if not yugabyte_other:
        print("❌ Aucune description 'other' trouvée pour YugabyteDB")
        return
    
    print("\n🔤 Analyse des motifs spécifiques à YugabyteDB...")
    suggestions = analyze_yugabyte_specific_patterns(yugabyte_other)
    
    print("\n💡 Suggestions de mots-clés pour YugabyteDB:")
    
    total_suggestions = 0
    for category, keywords in suggestions.items():
        if keywords:
            print(f"\n📂 {category.upper()}:")
            # Trier par fréquence
            keywords.sort(key=lambda x: x[1], reverse=True)
            for keyword, freq in keywords[:10]:  # Top 10 par catégorie
                print(f"  - {keyword} (fréquence: {freq})")
                total_suggestions += 1
    
    print(f"\n📈 Total suggestions: {total_suggestions} mots-clés spécifiques à YugabyteDB")
    
    # Générer les suggestions pour CATEGORIES
    print("\n🔄 Mots-clés YugabyteDB à ajouter:")
    
    combined_suggestions = defaultdict(set)
    
    for category, keywords in suggestions.items():
        for keyword, freq in keywords:
            combined_suggestions[category].add(keyword)
    
    for category, keywords in combined_suggestions.items():
        if keywords:
            print(f"\n📂 {category.upper()} - Nouveaux mots-clés YugabyteDB:")
            for keyword in sorted(keywords)[:12]:  # Limiter à 12 par catégorie
                print(f"  - {keyword}")

if __name__ == "__main__":
    main()
