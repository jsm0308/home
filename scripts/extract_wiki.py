"""
Extract wiki page summaries for the web dashboard.
Scans 2_Wiki/ directory, extracts frontmatter + first paragraph per page.
Output: data/wiki-index.json
"""
import os, json, re

WIKI_DIR = r"C:\Users\Gram\Desktop\jsm obsidian\jsm personal agents (obsidian files)\Agents\2_Wiki"
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "wiki-index.json")

# Pages to skip (system pages shown elsewhere)
SKIP = {"log.md", "index.md", "learnings.md", "prompt-journal.md", "skill-inventory.md",
        "_stubs.md", "maintenance_state.json"}

# Domain keywords for auto-classification
DOMAIN_KEYWORDS = {
    "Core": ["core", "system", "coach", "meta", "arch", "rule"],
    "Economy": ["invest", "btc", "etf", "econom", "trad", "portfoli", "macro"],
    "Study": ["learn", "course", "paper", "research", "study", "academ", "mamba", "curricul"],
    "Career": ["career", "intern", "resume", "job", "labs", "grad"],
    "Life": ["fit", "routin", "food", "workout", "exercis", "health"],
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
    """Extract the first non-heading, non-empty paragraph."""
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


def classify_domain(slug, body_lower):
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in slug.lower() or kw in body_lower[:300]:
                return domain
    return "General"


def main():
    pages = []
    for f in sorted(os.listdir(WIKI_DIR)):
        if not f.endswith(".md"):
            continue
        if f in SKIP:
            continue
        path = os.path.join(WIKI_DIR, f)
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read()

        fm, body = extract_frontmatter(content)
        slug = f.replace(".md", "")
        title = slug.replace("-", " ")

        # Title from first # heading
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
        domain = classify_domain(slug, body.lower())

        pages.append({
            "slug": slug,
            "title": title,
            "kind": kind,
            "confidence": confidence,
            "domain": domain,
            "created": created,
            "updated": updated,
            "summary": summary[:250]
        })

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(pages, fh, ensure_ascii=False, indent=2)

    # Group by domain
    domains = {}
    for p in pages:
        domains.setdefault(p["domain"], []).append(p["slug"])
    print(f"Extracted {len(pages)} wiki pages -> {OUTPUT}")
    for d, slugs in sorted(domains.items()):
        print(f"  {d}: {len(slugs)} pages")


if __name__ == "__main__":
    main()
