import json
import os
import re
from collections import Counter, defaultdict
from etape2 import classify_change, CATEGORIES

def extract_other_by_database():
    """Extrait les descriptions 'other' par base de données spécifique"""
    
    db_other = {
        "cassandra": [],
        "mongodb": [], 
        "cockroachdb": []
    }
    
    # Fichiers à analyser
    files_to_analyze = {
        "cassandra": "cassandra_versions.json",
        "mongodb": "mongodb-versions.json", 
        "cockroachdb": "cockroachdb-versions.json"
    }
    
    for db_name, filename in files_to_analyze.items():
        filepath = os.path.join("output", filename)
        if not os.path.exists(filepath):
            continue
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = data if isinstance(data, list) else [data]
        
        for item in items:
            if "ai_analysis" in item and "details" in item["ai_analysis"]:
                for detail in item["ai_analysis"]["details"]:
                    if detail["category"] == "other":
                        db_other[db_name].append(detail["description"])
    
    return db_other

def analyze_database_specific_keywords(db_other):
    """Analyse les mots-clés spécifiques à chaque base de données"""
    
    # Mots-clés spécifiques à Cassandra
    cassandra_keywords = {
        "performance": ["compaction", "sstables", "memtable", "cql", "nodetool", "gossip", "cms", "repair", "replication", "consistency", "tombstone", "hint", "streaming", "bootstrap", "decommission", "schema", "keyspace", "table", "index", "materialized", "view", "trigger", "function", "aggregate", "role", "permission", "authentication", "authorization", "encryption", "ssl", "jmx", "metrics", "logging", "snapshot", "backup", "restore", "upgrade", "migration", "compatibility"],
        "bug_fix": ["npe", "nullpointer", "concurrent", "mutation", "read", "write", "timeout", "connection", "socket", "exception", "error", "fail", "crash", "hang", "deadlock", "race", "corrupt", "damage", "inconsistent", "stale", "outdated", "missing", "incorrect", "invalid", "malformed", "truncated", "incomplete"],
        "new_feature": ["cqlsh", "shema", "table", "index", "view", "trigger", "function", "aggregate", "role", "permission", "feature", "support", "enable", "allow", "add", "create", "implement", "introduce", "provide", "extend"],
        "security": ["auth", "authentication", "authorization", "permission", "role", "encrypt", "decrypt", "ssl", "tls", "certificate", "secure", "protect", "validate", "verify", "check", "control", "restrict", "prevent", "block", "filter"]
    }
    
    # Mots-clés spécifiques à MongoDB
    mongodb_keywords = {
        "performance": ["aggregation", "pipeline", "index", "compound", "wildcard", "text", "geospatial", "shard", "sharding", "balancer", "chunk", "split", "merge", "move", "rs", "replica", "primary", "secondary", "arbiter", "election", "stepdown", "heartbeat", "sync", "oplog", "journal", "wiredtiger", "cache", "compression", "checkpoint", "eviction"],
        "bug_fix": ["cursor", "document", "bson", "objectid", "decimal", "decimal128", "array", "nested", "query", "update", "delete", "insert", "find", "count", "distinct", "group", "sort", "limit", "skip", "projection", "explain", "execution", "plan", "optimizer"],
        "new_feature": ["change", "stream", "pipeline", "stage", "operator", "expression", "function", "aggregation", "transaction", "multi", "document", "session", "retryable", "write", "read", "concern", "majority", "linearizable", "snapshot"],
        "security": ["auth", "authentication", "authorization", "role", "privilege", "user", "password", "scram", "x509", "ldap", "kerberos", "audit", "logging", "encryption", "rest", "tls", "ssl", "certificate", "key", "vault"]
    }
    
    # Mots-clés spécifiques à CockroachDB
    cockroachdb_keywords = {
        "performance": ["sql", "query", "optimizer", "plan", "execution", "index", "composite", "partial", "inverted", "full", "text", "geospatial", "join", "nested", "loop", "hash", "merge", "distributed", "transaction", "isolation", "serializable", "snapshot", "read", "committed", "write", "skew", "hotspot", "range", "split", "merge", "rebalance", "replica", "lease", "follower", "leader", "election", "raft", "consensus", "log", "storage", "engine", "rocksdb", "pebble", "cache", "buffer", "pool"],
        "bug_fix": ["sql", "parser", "planner", "executor", "error", "exception", "panic", "assert", "check", "constraint", "foreign", "key", "unique", "check", "not", "null", "default", "collation", "encoding", "decoding", "type", "conversion", "cast", "overflow", "underflow", "precision", "scale", "round", "truncate"],
        "new_feature": ["sql", "statement", "command", "type", "function", "procedure", "trigger", "view", "materialized", "sequence", "domain", "composite", "enum", "range", "json", "jsonb", "array", "vector", "geo", "gis", "spatial", "full", "text", "search", "changefeed", "sink", "source", "connection", "pool"],
        "security": ["auth", "authentication", "authorization", "role", "privilege", "user", "password", "certificate", "tls", "ssl", "encryption", "at", "rest", "in", "transit", "audit", "logging", "sql", "injection", "rbac", "acl", "network", "firewall", "allowlist", "denylist"]
    }
    
    all_keywords = {
        "cassandra": cassandra_keywords,
        "mongodb": mongodb_keywords,
        "cockroachdb": cockroachdb_keywords
    }
    
    suggestions = defaultdict(lambda: defaultdict(list))
    
    for db_name, descriptions in db_other.items():
        if not descriptions:
            continue
            
        # Combiner toutes les descriptions pour analyse
        all_text = " ".join(descriptions).lower()
        db_specific_keywords = all_keywords[db_name]
        
        for category, keywords in db_specific_keywords.items():
            for keyword in keywords:
                if keyword in all_text and keyword not in [kw for cat in CATEGORIES.values() for kw in cat]:
                    count = all_text.count(keyword)
                    if count > 2:  # Seulement si apparaît fréquemment
                        suggestions[db_name][category].append((keyword, count))
    
    return suggestions

def main():
    print("🔍 Extraction des descriptions 'other' par base de données...")
    db_other = extract_other_by_database()
    
    print("\n📊 Nombre de descriptions 'other' par base de données:")
    for db_name, descriptions in db_other.items():
        print(f"   {db_name}: {len(descriptions)}")
    
    print("\n🔤 Analyse des mots-clés spécifiques...")
    suggestions = analyze_database_specific_keywords(db_other)
    
    print("\n💡 Suggestions de mots-clés spécifiques par base de données:")
    
    total_suggestions = 0
    for db_name, categories in suggestions.items():
        if not categories:
            continue
            
        print(f"\n🗄️  {db_name.upper()}:")
        for category, keywords in categories.items():
            if keywords:
                print(f"  📂 {category.upper()}:")
                # Trier par fréquence
                keywords.sort(key=lambda x: x[1], reverse=True)
                for keyword, freq in keywords[:8]:  # Top 8 par catégorie
                    print(f"    - {keyword} (fréquence: {freq})")
                    total_suggestions += 1
    
    print(f"\n📈 Total suggestions: {total_suggestions} mots-clés spécifiques")
    
    # Générer les suggestions pour CATEGORIES
    print("\n🔄 Mots-clés à ajouter aux catégories existantes:")
    
    # Combiner toutes les suggestions par catégorie
    combined_suggestions = defaultdict(set)
    
    for db_name, categories in suggestions.items():
        for category, keywords in categories.items():
            for keyword, freq in keywords:
                combined_suggestions[category].add(keyword)
    
    for category, keywords in combined_suggestions.items():
        if keywords:
            print(f"\n📂 {category.upper()} - Nouveaux mots-clés:")
            for keyword in sorted(keywords)[:15]:  # Limiter à 15 par catégorie
                print(f"  - {keyword}")

if __name__ == "__main__":
    main()
