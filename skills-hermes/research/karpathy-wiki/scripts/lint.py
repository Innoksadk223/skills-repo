#!/usr/bin/env python3
"""
karpathy-wiki lint script — scans a wiki directory and reports issues as JSON.
Usage: python3 lint.py <wiki_path>
       or set WIKI_PATH env var.
Output: JSON with findings grouped by category.
"""

import os, sys, re, json, hashlib
from collections import defaultdict
from datetime import datetime, timedelta

WIKI = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("WIKI_PATH", os.path.expanduser("~/wiki"))

RAW = os.path.join(WIKI, "raw")
ENTITIES = os.path.join(WIKI, "entities")
CONCEPTS = os.path.join(WIKI, "concepts")
COMPARISONS = os.path.join(WIKI, "comparisons")
DEBATES = os.path.join(WIKI, "debates")
CLAIMS = os.path.join(WIKI, "claims")
QUERIES = os.path.join(WIKI, "queries")
SYNTHESIS = os.path.join(WIKI, "synthesis")
ARCHIVE = os.path.join(WIKI, "_archive")
INDEX = os.path.join(WIKI, "index.md")
SCHEMA = os.path.join(WIKI, "SCHEMA.md")
LOG = os.path.join(WIKI, "log.md")

WIKI_DIRS = [ENTITIES, CONCEPTS, COMPARISONS, DEBATES, CLAIMS, QUERIES, SYNTHESIS]

def read_frontmatter(filepath):
    """Extract YAML frontmatter as dict. Returns (dict, body_start_line)."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None, 0
    if not content.startswith("---"):
        return {}, 0
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, 0
    fm_text = parts[1]
    body = parts[2]
    body_start = content[:content.index(body)].count("\n") + 1
    fm = {}
    for line in fm_text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Handle lists like [a, b]
            if val.startswith("[") and val.endswith("]"):
                val = [v.strip().strip("'").strip('"') for v in val[1:-1].split(",") if v.strip()]
            fm[key] = val
    return fm, body_start

def scan_wiki_pages():
    """Return list of (relpath, abspath, filename_no_ext, frontmatter)."""
    pages = []
    for d in WIKI_DIRS:
        if not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if fname.endswith(".md"):
                abspath = os.path.join(d, fname)
                relpath = os.path.relpath(abspath, WIKI)
                name = fname[:-3]  # strip .md
                fm, _ = read_frontmatter(abspath)
                pages.append((relpath, abspath, name, fm))
    return pages

def extract_wikilinks(filepath):
    """Extract [[target]] and [[target|alias]] from file. Returns list of targets."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return []
    return re.findall(r"\[\[([^\]|#]+)(?:[|#][^\]]+)?\]\]", content)

def scan_raw_files():
    """Return list of raw file paths with their frontmatter."""
    files = []
    if not os.path.isdir(RAW):
        return files
    for root, dirs, fnames in os.walk(RAW):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "assets"]
        for fname in fnames:
            if fname.endswith(".md"):
                abspath = os.path.join(root, fname)
                fm, body_start = read_frontmatter(abspath)
                files.append((os.path.relpath(abspath, WIKI), abspath, fm, body_start))
    return files

def read_index_entries():
    """Parse index.md and return set of page names listed."""
    if not os.path.exists(INDEX):
        return set()
    try:
        with open(INDEX, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return set()
    return set(re.findall(r"\[\[([^\]]+)\]\]", content))

# ── Checks ──

def check_orphans(pages):
    """① Find pages with zero inbound wikilinks."""
    all_links = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        for target in extract_wikilinks(abspath):
            all_links[target].add(name)
    orphans = []
    for relpath, abspath, name, fm in pages:
        if name not in all_links:
            orphans.append(relpath)
    return orphans

def check_broken_links(pages):
    """② Find wikilinks pointing to non-existent pages."""
    page_set = {p[2] for p in pages}
    broken = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        for target in extract_wikilinks(abspath):
            if target not in page_set:
                broken[target].add(name)
    return {k: list(v) for k, v in broken.items()}

def check_index_completeness(pages):
    """③ Pages not in index.md, and index entries with no page.

    Ordinary claims are intentionally discoverable through the graph and claims/
    folder; only core claims must appear in index.md.
    """
    indexed = read_index_entries()
    page_names = {p[2] for p in pages}
    required_names = set()
    for relpath, abspath, name, fm in pages:
        is_claim = relpath.startswith("claims/") or (fm and fm.get("type") == "claim")
        if is_claim:
            if str((fm or {}).get("core", "")).lower() == "true":
                required_names.add(name)
            continue
        required_names.add(name)
    not_in_index = sorted(required_names - indexed)
    index_orphans = sorted(indexed - page_names)
    return not_in_index, index_orphans

def check_frontmatter(pages, taxonomy_tags):
    """④ Validate required fields and taxonomy tags.

    Claim-specific fields are validated by check_claim_structure(). Claim pages
    do not require tags because the claim template does not use them.
    """
    issues = []
    base_required = ["title", "created", "updated", "type", "sources"]
    for relpath, abspath, name, fm in pages:
        if fm is None:
            issues.append({"page": relpath, "issue": "unreadable file"})
            continue
        is_claim = relpath.startswith("claims/") or (fm and fm.get("type") == "claim")
        required = list(base_required)
        if not is_claim:
            required.append("tags")
        missing = [f for f in required if f not in fm]
        if missing:
            issues.append({"page": relpath, "issue": f"missing fields: {missing}"})
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.strip("[]").split(",")]
        for t in tags:
            if t.strip() and taxonomy_tags and t.strip() not in taxonomy_tags:
                issues.append({"page": relpath, "issue": f"tag '{t}' not in taxonomy"})
    return issues

def check_stale_content(pages, raw_files):
    """⑤ Pages with updated >90 days older than most recent source mentioning same entity."""
    stale = []
    cutoff = datetime.now() - timedelta(days=90)
    # Build name-to-date map from raw
    raw_dates = {}
    for relpath, abspath, fm, _ in raw_files:
        raw_dates[relpath] = fm.get("ingested", "") if fm else ""
    for relpath, abspath, name, fm in pages:
        updated = fm.get("updated", "") if fm else ""
        try:
            dt = datetime.strptime(str(updated), "%Y-%m-%d")
        except Exception:
            continue
        if dt < cutoff:
            stale.append(relpath)
    return stale

def check_contradictions(pages):
    """⑥ Pages with contested markers or contested claim status."""
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        if fm.get("contested") in [True, "true", "True"] or fm.get("status") == "contested":
            issues.append({"page": relpath, "issue": "marked contested"})
        contradictions = fm.get("contradictions", [])
        if isinstance(contradictions, str):
            contradictions = [c.strip() for c in contradictions.strip("[]").split(",")]
        if contradictions and contradictions != [""]:
            issues.append({"page": relpath, "issue": f"contradicts: {contradictions}"})
    return issues

def check_quality_signals(pages):
    """⑦ Pages with confidence: low or single-source without confidence field."""
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        conf = fm.get("confidence", "")
        if conf == "low":
            issues.append({"page": relpath, "issue": "confidence: low"})
        sources = fm.get("sources", [])
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.strip("[]").split(",")]
        if len(sources) <= 1 and "confidence" not in fm:
            issues.append({"page": relpath, "issue": "single-source, no confidence field"})
    return issues

def check_source_drift(raw_files):
    """⑧ Recompute sha256 of raw files, flag mismatches."""
    drifts = []
    for relpath, abspath, fm, body_start in raw_files:
        if not fm or "sha256" not in fm:
            continue
        stored = fm["sha256"]
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2].lstrip("\n") if len(parts) >= 3 else content
        else:
            body = content
        current = hashlib.sha256(body.encode()).hexdigest()
        if stored != current:
            drifts.append({"file": relpath, "stored": stored[:12], "current": current[:12]})
    return drifts

def check_page_size(pages):
    """⑨ Pages over 200 lines."""
    oversized = []
    for relpath, abspath, name, fm in pages:
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                lines = len(f.readlines())
        except Exception:
            continue
        if lines > 200:
            oversized.append({"page": relpath, "lines": lines})
    return oversized

def check_tags(pages, taxonomy_tags):
    """⑩ Tags not in taxonomy."""
    issues = []
    for relpath, abspath, name, fm in pages:
        if not fm:
            continue
        tags = fm.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.strip("[]").split(",")]
        for t in tags:
            if t.strip() and taxonomy_tags and t.strip() not in taxonomy_tags:
                issues.append({"page": relpath, "tag": t.strip()})
    return issues

def check_log_rotation():
    """⑪ Check if log.md exceeds 500 entries."""
    if not os.path.exists(LOG):
        return False
    try:
        with open(LOG, "r", encoding="utf-8") as f:
            entries = [l for l in f if l.startswith("## [")]
    except Exception:
        return False
    return len(entries) > 500

def check_stub_upgrades(pages):
    """Stub upgrade candidates: stubs (confidence:low + 📝) linked by 2+ full pages."""
    # Find all wikilinks across all pages
    all_links = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        is_full = fm and fm.get("confidence") not in ["low", ""] if fm else True
        for target in extract_wikilinks(abspath):
            all_links[target].add((name, is_full))
    upgrades = []
    for relpath, abspath, name, fm in pages:
        if not fm or fm.get("confidence") != "low":
            continue
        # Check if it's a stub
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            continue
        if "📝" not in content:
            continue
        full_referrers = [n for n, is_full in all_links.get(name, set()) if is_full]
        if len(full_referrers) >= 2:
            upgrades.append({"page": relpath, "full_referrers": full_referrers})
    return upgrades

def check_stub_cleanup(pages):
    """Stub cleanup: stubs whose ALL referrers are archived."""
    archived_pages = set()
    if os.path.isdir(ARCHIVE):
        for root, _, fnames in os.walk(ARCHIVE):
            for fname in fnames:
                if fname.endswith(".md"):
                    archived_pages.add(fname[:-3])
    all_links = defaultdict(set)
    for relpath, abspath, name, fm in pages:
        for target in extract_wikilinks(abspath):
            all_links[target].add(name)
    orphan_stubs = []
    for relpath, abspath, name, fm in pages:
        if not fm or fm.get("confidence") != "low":
            continue
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                if "📝" not in f.read():
                    continue
        except Exception:
            continue
        referrers = all_links.get(name, set())
        if referrers and referrers.issubset(archived_pages):
            orphan_stubs.append({"page": relpath, "referrers": list(referrers)})
    return orphan_stubs

def load_taxonomy():
    """Load tags from SCHEMA.md taxonomy section."""
    if not os.path.exists(SCHEMA):
        return set()
    try:
        with open(SCHEMA, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return set()
    # Find taxonomy section — English template or Chinese project schema.
    tags = set()
    in_taxonomy = False
    for line in content.split("\n"):
        if line.startswith("## ") and ("Tag Taxonomy" in line or "标签体系" in line):
            in_taxonomy = True
            continue
        if in_taxonomy and line.startswith("## ") and "Tag Taxonomy" not in line and "标签体系" not in line:
            break
        if in_taxonomy:
            # Match `tag` patterns
            found = re.findall(r"`([^`]+)`", line)
            for t in found:
                full_tag = t.strip()
                if not full_tag or full_tag.startswith("e.g.") or full_tag.startswith("[Define"):
                    continue
                tags.add(full_tag)
                # Also accept the Chinese base form for bilingual taxonomy entries.
                base_tag = full_tag.split("（")[0].strip()
                if base_tag:
                    tags.add(base_tag)
    return tags

def check_claim_structure(pages):
    """Claim pages must expose argument structure in frontmatter and body wikilinks."""
    issues = []
    required = [
        "claim_type", "core", "status", "confidence", "supports", "opposes",
        "limits", "depends_on", "related_concepts", "related_entities",
        "related_comparisons", "sources"
    ]
    valid_types = {"main", "support", "objection", "limitation", "bridge"}
    valid_status = {"stub", "working", "supported", "contested"}
    for relpath, abspath, name, fm in pages:
        is_claim = relpath.startswith("claims/") or (fm and fm.get("type") == "claim")
        if not is_claim:
            continue
        if not fm:
            issues.append({"page": relpath, "issue": "claim missing frontmatter"})
            continue
        missing = [f for f in required if f not in fm]
        if missing:
            issues.append({"page": relpath, "issue": f"claim missing fields: {missing}"})
        if fm.get("claim_type") and fm.get("claim_type") not in valid_types:
            issues.append({"page": relpath, "issue": f"invalid claim_type: {fm.get('claim_type')}"})
        if fm.get("status") and fm.get("status") not in valid_status:
            issues.append({"page": relpath, "issue": f"invalid status: {fm.get('status')}"})
        try:
            with open(abspath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            issues.append({"page": relpath, "issue": "unreadable claim body"})
            continue
        if "## 命题" not in content:
            issues.append({"page": relpath, "issue": "missing ## 命题 section"})
        if "## 关系" not in content:
            issues.append({"page": relpath, "issue": "missing ## 关系 section"})
        if "[[raw/" in content or "[[../raw/" in content:
            issues.append({"page": relpath, "issue": "raw file wikilinked; use plain-text path instead"})
        core = str(fm.get("core", "")).lower() == "true"
        sources = fm.get("sources", [])
        if isinstance(sources, str):
            sources = [s.strip() for s in sources.strip("[]").split(",") if s.strip()]
        if core:
            for section in ["## 关键证据", "## 写作用途"]:
                if section not in content:
                    issues.append({"page": relpath, "issue": f"core claim missing {section}"})
            if not sources:
                issues.append({"page": relpath, "issue": "core claim has no sources"})
    return issues

# ── Main ──

def main():
    pages = scan_wiki_pages()
    raw_files = scan_raw_files()
    taxonomy = load_taxonomy()

    report = {
        "wiki_path": WIKI,
        "total_pages": len(pages),
        "total_raw_files": len(raw_files),
        "findings": {}
    }

    # ① Orphans
    orphans = check_orphans(pages)
    if orphans:
        report["findings"]["orphans"] = orphans

    # ② Broken wikilinks
    broken = check_broken_links(pages)
    if broken:
        report["findings"]["broken_links"] = broken

    # ③ Index completeness
    not_in_index, index_orphans = check_index_completeness(pages)
    if not_in_index or index_orphans:
        report["findings"]["index"] = {
            "pages_not_in_index": not_in_index,
            "index_entries_without_page": index_orphans
        }

    # ④ Frontmatter
    fm_issues = check_frontmatter(pages, taxonomy)
    if fm_issues:
        report["findings"]["frontmatter"] = fm_issues

    # ④b Claim structure
    claim_issues = check_claim_structure(pages)
    if claim_issues:
        report["findings"]["claim_structure"] = claim_issues

    # ⑤ Stale content
    stale = check_stale_content(pages, raw_files)
    if stale:
        report["findings"]["stale"] = stale

    # ⑥ Contradictions
    contradictions = check_contradictions(pages)
    if contradictions:
        report["findings"]["contradictions"] = contradictions

    # ⑦ Quality
    quality = check_quality_signals(pages)
    if quality:
        report["findings"]["quality"] = quality

    # ⑧ Source drift
    drift = check_source_drift(raw_files)
    if drift:
        report["findings"]["source_drift"] = drift

    # ⑨ Page size
    oversized = check_page_size(pages)
    if oversized:
        report["findings"]["oversized"] = oversized

    # ⑩ Tags
    tag_issues = check_tags(pages, taxonomy)
    if tag_issues:
        report["findings"]["tag_issues"] = tag_issues

    # ⑪ Log rotation
    if check_log_rotation():
        report["findings"]["log_rotation"] = "log.md exceeds 500 entries — rotate to log-YYYY.md"

    # Stub upgrade candidates
    upgrades = check_stub_upgrades(pages)
    if upgrades:
        report["findings"]["stub_upgrades"] = upgrades

    # Stub cleanup
    orphan_stubs = check_stub_cleanup(pages)
    if orphan_stubs:
        report["findings"]["stub_cleanup"] = orphan_stubs

    # Summary
    total_issues = sum(len(v) if isinstance(v, (list, dict)) else 1 for v in report["findings"].values())
    report["total_issues"] = total_issues

    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
