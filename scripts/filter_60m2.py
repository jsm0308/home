"""Filter jeonse_data.json: remove listings with m2 > 60 (대출 한도 초과)."""
import json, sys
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "jeonse_data.json"
data = json.loads(path.read_text(encoding="utf-8"))
before = len(data["listings"])
data["listings"] = [l for l in data["listings"] if l.get("m2", 0) <= 60]
after = len(data["listings"])

# renumber
for i, l in enumerate(data["listings"]):
    l["no"] = i + 1

areas = sorted(set(l["area"] for l in data["listings"]))
data["stats"]["total"] = after
data["stats"]["areas"] = areas
data["stats"]["note"] = "m2 <= 60 only (청년 버팀목 만25세미만 단독세대주 전용면적 제한)"

path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{before} → {after} (-{before - after})")
