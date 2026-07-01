"""Extract rule titles and metadata from .mdc files for dashboard display."""
import os, json, re

RULES_DIR = r"C:\Users\Gram\Desktop\jsm personal agents\.cursor\rules"
OUTPUT = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rules.json")

rules = []
for f in sorted(os.listdir(RULES_DIR)):
    if not f.endswith(".mdc"):
        continue
    path = os.path.join(RULES_DIR, f)
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Parse frontmatter
    title = f.replace(".mdc", "").replace("-", " ").title()
    in_fm = False
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "---" and i == 0:
            in_fm = True
            continue
        if line.strip() == "---" and in_fm:
            in_fm = False
            continue
        if in_fm:
            continue
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            title = stripped[:100]
            break

    always_apply = "alwaysApply: true" in content or "always_applied_workspace_rule" in content[:1000]
    # Clean content: remove frontmatter
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            body = parts[2].strip()

    rules.append({
        "file": f,
        "title": title,
        "alwaysApply": always_apply,
        "content": body[:3000]
    })

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
with open(OUTPUT, "w", encoding="utf-8") as fh:
    json.dump(rules, fh, ensure_ascii=False, indent=2)

print(f"Extracted {len(rules)} rules -> {OUTPUT}")
print(f"Always-on: {sum(1 for r in rules if r['alwaysApply'])}, On-demand: {sum(1 for r in rules if not r['alwaysApply'])}")
