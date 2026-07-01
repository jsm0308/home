"""
Extract rules from .mdc files with human-readable summaries.
Outputs rules.json with: file, title, subtitle (domain hint), alwaysApply, summary, sections, fullContent.
"""
import os, json, re, yaml

RULES_DIR = r"C:\Users\Gram\Desktop\jsm personal agents\.cursor\rules"
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rules.json")


def extract_frontmatter(content):
    """Extract YAML frontmatter. Returns (dict, body_without_fm)."""
    fm = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1]) or {}
            except Exception:
                pass
            body = parts[2].strip()
    return fm, body


def extract_rule(path):
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    fm, body = extract_frontmatter(content)
    fname = os.path.basename(path)

    # alwaysApply
    always_apply = fm.get("alwaysApply", False) or "always_applied_workspace_rule" in content[:1000]

    # Title: first # heading
    title = fname.replace(".mdc", "").replace("-", " ").title()
    subtitle = ""
    lines = body.split("\n")
    content_start = 0
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            content_start = i + 1
            break

    # Subtitle: first non-empty non-heading line after title
    for i in range(content_start, len(lines)):
        line = lines[i].strip()
        if line and not line.startswith("#"):
            subtitle = line[:120]
            break

    # Summary: first meaningful paragraph (skip ## headings, find paragraph block)
    summary = ""
    in_paragraph = False
    paragraph_lines = []
    for i in range(content_start, len(lines)):
        stripped = lines[i].strip()
        if not stripped:
            if in_paragraph and paragraph_lines:
                break
            continue
        if stripped.startswith("## ") or stripped.startswith("# "):
            if in_paragraph and paragraph_lines:
                break
            continue
        if stripped.startswith("```") or stripped.startswith("---"):
            if in_paragraph and paragraph_lines:
                break
            continue
        in_paragraph = True
        clean = stripped
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)
        clean = re.sub(r'\*(.+?)\*', r'\1', clean)
        clean = re.sub(r'`(.+?)`', r'\1', clean)
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', clean)
        paragraph_lines.append(clean)
        if len(" ".join(paragraph_lines)) > 200:
            break

    summary = " ".join(paragraph_lines) if paragraph_lines else subtitle

    # Sections: extract ## headings
    sections = []
    current_section = None
    current_lines = []
    for i in range(content_start, len(lines)):
        stripped = lines[i].strip()
        if stripped.startswith("## "):
            if current_section and current_lines:
                sections.append({
                    "heading": current_section,
                    "body": " ".join(current_lines)[:500]
                })
            current_section = stripped[3:].strip()
            current_lines = []
        elif current_section and stripped and not stripped.startswith("# "):
            clean = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
            clean = re.sub(r'`(.+?)`', r'\1', clean)
            current_lines.append(clean)
    if current_section and current_lines:
        sections.append({
            "heading": current_section,
            "body": " ".join(current_lines)[:500]
        })

    # Domain hint from description or filename
    desc = fm.get("description", "")
    domain = _guess_domain(fname, desc, body[:500])

    # Full content (keep for detail view)
    full_content = body[:5000]

    return {
        "file": fname,
        "title": title,
        "subtitle": subtitle,
        "domain": domain,
        "alwaysApply": always_apply,
        "summary": summary[:300],
        "sections": sections[:6],
        "fullContent": full_content
    }


def _guess_domain(fname, desc, body):
    combined = (fname + " " + desc + " " + body).lower()
    domains = []
    if any(w in combined for w in ["core", "coach", "constitu"]): domains.append("Core")
    if any(w in combined for w in ["wiki", "obsidian", "vault"]): domains.append("Wiki")
    if any(w in combined for w in ["commit", "git"]): domains.append("Git")
    if any(w in combined for w in ["invest", "econom", "trad", "btc"]): domains.append("Economy")
    if any(w in combined for w in ["career", "resume", "cv"]): domains.append("Career")
    if any(w in combined for w in ["study", "learn", "course", "paper"]): domains.append("Study")
    if any(w in combined for w in ["life", "hous", "fit", "routin"]): domains.append("Life")
    if any(w in combined for w in ["design", "ui", "css", "style", "mermaid"]): domains.append("Design")
    if any(w in combined for w in ["human", "writ"]): domains.append("Style")
    if any(w in combined for w in ["sprint", "pipeline"]): domains.append("Process")
    if any(w in combined for w in ["safet", "freeze", "investig"]): domains.append("Safety")
    if any(w in combined for w in ["mece", "sourc"]): domains.append("Research")
    if any(w in combined for w in ["qualit", "verif"]): domains.append("Quality")
    if any(w in combined for w in ["soonsal", "brief"]): domains.append("News")
    return domains if domains else ["General"]


def main():
    rules = []
    for f in sorted(os.listdir(RULES_DIR)):
        if not f.endswith(".mdc"):
            continue
        path = os.path.join(RULES_DIR, f)
        rules.append(extract_rule(path))

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(rules, fh, ensure_ascii=False, indent=2)

    always = sum(1 for r in rules if r["alwaysApply"])
    on_demand = len(rules) - always
    print(f"Extracted {len(rules)} rules -> {OUTPUT}")
    print(f"Always-on: {always}, On-demand: {on_demand}")


if __name__ == "__main__":
    main()
