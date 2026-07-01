"""
Extract wiki page summaries for web dashboard.
Scans 2_Wiki/ recursively (handles subdirectories from legacy structure).
Output: data/wiki-index.json
"""
import os, json, re

WIKI_DIR = r"C:\Users\Gram\Desktop\jsm obsidian\jsm personal agents (obsidian files)\Agents\2_Wiki"
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wiki-index.json")

SKIP = {"log.md", "index.md", "_stubs.md"}
SKIP_DIRS = {"lint_reports"}

DOMAIN_KEYWORDS = {
    "Core": ["core", "system", "coach", "meta", "arch", "rule", "memory", "knowledge"],
    "Economy": ["invest", "btc", "etf", "econom", "trad", "portfoli", "macro", "crypto", "coin", "finance", "asset", "fear", "greed"],
    "Study": ["learn", "course", "paper", "research", "study", "academ", "mamba", "curricul", "lecture", "assignment", "algebra", "calculus", "probability"],
    "Career": ["career", "intern", "resume", "job", "labs", "grad", "research lab"],
    "Life": ["fit", "routin", "food", "workout", "exercis", "health", "cook"],
    "순살브리핑": ["순살", "soonsal", "briefing", "crypto", "cardnews"],
    "System-Meta": ["rule", "lint", "schema", "prompt", "journal", "learnings", "skill", "wiki-arch", "architecture"],
}


def extract_frontmatter(content):
    fm = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split("\n"):
                line = line.strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = parts[2].strip()
    return fm, body


def extract_first_paragraph(body):
    lines = body.split("\n")
    paragraph = []
    started = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if started and paragraph:
                break
            continue
        if stripped.startswith("#") or stripped.startswith("```") or stripped.startswith("---"):
            if started and paragraph:
                break
            continue
        started = True
        clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', stripped)
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
        clean = re.sub(r'`(.+?)`', r'\1', clean)
        paragraph.append(clean)
        if len(" ".join(paragraph)) > 180:
            break
    return " ".join(paragraph) if paragraph else ""


def classify_domain(slug, body_lower, subdir=""):
    """Classify by subdirectory first, then keywords."""
    # If in subdirectory, use that as primary domain
    if subdir == "Economy":
        return "Economy"
    if subdir == "Career":
        return "Career"
    if subdir == "Study-AI-ML":
        return "Study"
    if subdir == "Fitness":
        return "Life"
    if subdir == "Decisions":
        return "Decisions"
    if subdir == "System-Meta":
        return "System"
    if subdir == "순살-브리핑":
        return "순살브리핑"

    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in slug.lower() or kw in body_lower[:300]:
                return domain
    return "General"


def main():
    pages = []

    # Walk recursively
    for root, dirs, files in os.walk(WIKI_DIR):
        # Skip excluded dirs
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        subdir = os.path.relpath(root, WIKI_DIR)
        if subdir == ".":
            subdir = ""

        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            if f in SKIP and subdir == "":
                continue
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()

            fm, body = extract_frontmatter(content)
            slug = f.replace(".md", "")

            title = slug.replace("-", " ")
            for line in body.split("\n"):
                stripped = line.strip()
                if stripped.startswith("# ") and not stripped.startswith("## "):
                    title = stripped[2:].strip()
                    break

            kind = fm.get("kind", "")
            confidence = fm.get("confidence", "")
            created = fm.get("created", "")
            updated = fm.get("updated", "")

            summary = extract_first_paragraph(body)
            domain = classify_domain(slug, body.lower(), subdir)

            pages.append({
                "slug": slug,
                "title": title,
                "kind": kind,
                "confidence": confidence,
                "domain": domain,
                "subdir": subdir,
                "created": created,
                "updated": updated,
                "summary": summary[:250]
            })

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(pages, fh, ensure_ascii=False, indent=2)

    domains = {}
    for p in pages:
        domains.setdefault(p["domain"], []).append(p["slug"])
    print(f"Extracted {len(pages)} wiki pages -> {OUTPUT}")
    for d, slugs in sorted(domains.items()):
        print(f"  {d}: {len(slugs)} pages")


if __name__ == "__main__":
    main()
