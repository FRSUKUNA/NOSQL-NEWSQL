import json
import os
import re
from collections import Counter, defaultdict
from etape2 import classify_change, CATEGORIES

def extract_remaining_other_deep():
    """Extrait les descriptions encore classées comme 'other' après les améliorations"""
    remaining_other = []
    
    for filename in os.listdir("output"):
        if not filename.endswith(".json"):
            continue
            
        filepath = os.path.join("output", filename)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        items = data if isinstance(data, list) else [data]
        
        for item in items:
            if "ai_analysis" in item and "details" in item["ai_analysis"]:
                for detail in item["ai_analysis"]["details"]:
                    # Tester avec la classification actuelle
                    category = classify_change(detail["description"])
                    if category == "other":
                        remaining_other.append(detail["description"])
    
    return remaining_other

def find_patterns_and_context(descriptions):
    """Trouve des motifs et contextes spécifiques dans les descriptions restantes"""
    
    # Analyser les patterns de phrases
    patterns = {
        "add_support": re.compile(r'\b(add|support|enable|allow) (for|of|to)\b', re.IGNORECASE),
        "fix_issue": re.compile(r'\b(fix|fixes|fixed|resolve|resolves|resolved) (an? )?(issue|problem|bug|error)\b', re.IGNORECASE),
        "improve_performance": re.compile(r'\b(improve|improves|improved|optimize|optimizes|optimized) (the )?(performance|speed|latency|throughput|efficiency)\b', re.IGNORECASE),
        "update_version": re.compile(r'\b(update|updates|updated|upgrade|upgrades|upgraded) (to|version)\b', re.IGNORECASE),
        "remove_deprecated": re.compile(r'\b(remove|removes|removed|deprecate|deprecates|deprecated)\b', re.IGNORECASE),
        "enhance_security": re.compile(r'\b(secure|secures|secured|protect|protects|protected|hardens|hardened)\b', re.IGNORECASE),
        "implement_feature": re.compile(r'\b(implement|implements|implemented|add|adds|added) (a |an )?(new )?(feature|functionality|capability)\b', re.IGNORECASE),
        "handle_error": re.compile(r'\b(handle|handles|handled|catch|catches|caught) (an? )?(error|exception|failure)\b', re.IGNORECASE),
        "prevent_issue": re.compile(r'\b(prevent|prevents|prevented|avoid|avoids|avoided)\b', re.IGNORECASE),
        "refactor_code": re.compile(r'\b(refactor|refactors|refactored|restructure|restructures|restructured|cleanup|cleanups|cleaned)\b', re.IGNORECASE)
    }
    
    # Mots-clés techniques spécifiques par contexte
    technical_keywords = {
        "database_ops": ["insert", "update", "delete", "select", "query", "execute", "commit", "rollback", "transaction", "lock", "unlock", "deadlock", "isolation", "consistency", "durability", "atomicity"],
        "storage_ops": ["write", "read", "flush", "sync", "fsync", "checkpoint", "wal", "journal", "log", "segment", "block", "page", "buffer", "cache", "evict", "compact", "merge", "split"],
        "network_ops": ["connect", "disconnect", "reconnect", "timeout", "retry", "backoff", "heartbeat", "ping", "bind", "listen", "accept", "close", "socket", "tcp", "udp", "tls", "ssl", "handshake"],
        "config_ops": ["configure", "config", "setting", "option", "parameter", "property", "tune", "adjust", "modify", "change", "override", "default", "environment", "variable"],
        "monitoring_ops": ["metric", "monitor", "track", "trace", "log", "audit", "report", "statistics", "measure", "collect", "gather", "export", "expose", "publish"],
        "testing_ops": ["test", "verify", "validate", "check", "assert", "mock", "stub", "fixture", "benchmark", "profile", "debug", "inspect"],
        "build_ops": ["build", "compile", "link", "package", "deploy", "release", "version", "dependency", "library", "module", "component"],
        "data_ops": ["serialize", "deserialize", "encode", "decode", "parse", "format", "convert", "transform", "migrate", "backup", "restore", "import", "export"]
    }
    
    # Mots-clés spécifiques aux types de problèmes
    problem_keywords = {
        "memory_issues": ["memory", "leak", "allocation", "deallocation", "gc", "garbage", "heap", "stack", "buffer", "overflow", "underflow", "oom", "outofmemory"],
        "performance_issues": ["slow", "slowdown", "bottleneck", "latency", "delay", "timeout", "throughput", "scalability", "concurrency", "contention", "race", "hotspot"],
        "reliability_issues": ["crash", "hang", "freeze", "deadlock", "livelock", "starvation", "corruption", "inconsistency", "race", "flaky", "unstable"],
        "security_issues": ["vulnerability", "exploit", "attack", "breach", "injection", "xss", "csrf", "auth", "bypass", "escalation", "privilege", "access"],
        "compatibility_issues": ["compatibility", "migration", "upgrade", "downgrade", "version", "legacy", "deprecated", "obsolete", "break", "regression"]
    }
    
    all_text = " ".join(descriptions).lower()
    
    # Analyser les patterns
    pattern_matches = {}
    for pattern_name, pattern in patterns.items():
        matches = pattern.findall(all_text)
        if matches:
            pattern_matches[pattern_name] = len(matches)
    
    # Analyser les mots-clés techniques
    technical_matches = defaultdict(int)
    for category, keywords in technical_keywords.items():
        for keyword in keywords:
            count = all_text.count(keyword)
            if count > 3:  # Seulement si apparaît fréquemment
                # Vérifier si le mot-clé n'est pas déjà dans CATEGORIES
                already_exists = any(keyword in cat_keywords for cat_keywords in CATEGORIES.values())
                if not already_exists:
                    technical_matches[category] += count
    
    # Analyser les mots-clés de problèmes
    problem_matches = defaultdict(int)
    for category, keywords in problem_keywords.items():
        for keyword in keywords:
            count = all_text.count(keyword)
            if count > 3:
                already_exists = any(keyword in cat_keywords for cat_keywords in CATEGORIES.values())
                if not already_exists:
                    problem_matches[category] += count
    
    return pattern_matches, technical_matches, problem_matches

def suggest_new_keywords_from_patterns():
    """Suggère de nouveaux mots-clés basés sur l'analyse des patterns"""
    
    remaining_other = extract_remaining_other_deep()
    print(f"📊 Encore {len(remaining_other)} descriptions dans 'other'")
    
    pattern_matches, technical_matches, problem_matches = find_patterns_and_context(remaining_other)
    
    print("\n🔍 Patterns de phrases identifiés:")
    for pattern, count in sorted(pattern_matches.items(), key=lambda x: x[1], reverse=True):
        print(f"  {pattern}: {count} occurrences")
    
    print("\n🔧 Mots-clés techniques manquants:")
    for category, count in sorted(technical_matches.items(), key=lambda x: x[1], reverse=True):
        if count > 10:
            print(f"  {category}: {count} occurrences")
    
    print("\n⚠️  Mots-clés de problèmes manquants:")
    for category, count in sorted(problem_matches.items(), key=lambda x: x[1], reverse=True):
        if count > 10:
            print(f"  {category}: {count} occurrences")
    
    # Suggestions de nouveaux mots-clés par catégorie existante
    new_keywords_suggestions = {
        "performance": ["slow", "slowdown", "bottleneck", "delay", "scalability", "concurrency", "contention", "hotspot", "throughput", "latency", "timeout", "optimize", "optimizes", "optimized"],
        "bug_fix": ["crash", "hang", "freeze", "deadlock", "livelock", "starvation", "corruption", "inconsistency", "flaky", "unstable", "leak", "overflow", "underflow", "oom", "outofmemory", "race", "bypass"],
        "new_feature": ["support", "enable", "allow", "capability", "functionality", "expose", "publish", "provide", "offer", "deliver"],
        "security": ["vulnerability", "exploit", "attack", "breach", "injection", "xss", "csrf", "escalation", "privilege", "secure", "secures", "secured", "hardens", "hardened"],
        "maintenance": ["compatibility", "migration", "upgrade", "downgrade", "version", "legacy", "obsolete", "break", "regression", "deprecated", "deprecate", "deprecates"],
        "configuration": ["configure", "config", "setting", "option", "parameter", "property", "tune", "adjust", "modify", "change", "override", "default", "environment", "variable"],
        "monitoring": ["metric", "monitor", "track", "trace", "log", "audit", "report", "statistics", "measure", "collect", "gather", "export", "expose", "publish"],
        "testing": ["test", "verify", "validate", "check", "assert", "mock", "stub", "fixture", "benchmark", "profile", "debug", "inspect"],
        "refactoring": ["refactor", "refactors", "refactored", "restructure", "restructures", "restructured", "cleanup", "cleanups", "cleaned", "simplify", "modularize"]
    }
    
    print("\n💡 Nouveaux mots-clés suggérés par catégorie:")
    
    # Filtrer et compter les suggestions pertinentes
    final_suggestions = defaultdict(list)
    all_text = " ".join(remaining_other).lower()
    
    for category, keywords in new_keywords_suggestions.items():
        for keyword in keywords:
            count = all_text.count(keyword)
            if count > 5:  # Seulement si apparaît fréquemment
                # Vérifier si pas déjà dans CATEGORIES
                already_exists = any(keyword in cat_keywords for cat_keywords in CATEGORIES.values())
                if not already_exists:
                    final_suggestions[category].append((keyword, count))
    
    for category, keywords in final_suggestions.items():
        if keywords:
            print(f"\n📂 {category.upper()}:")
            keywords.sort(key=lambda x: x[1], reverse=True)
            for keyword, count in keywords[:8]:  # Top 8 par catégorie
                print(f"  - {keyword} (fréquence: {count})")
    
    return final_suggestions

if __name__ == "__main__":
    suggest_new_keywords_from_patterns()
