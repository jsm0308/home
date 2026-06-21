"""Verify filtered data."""
import json
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "jeonse_data.json"
d = json.loads(path.read_text(encoding="utf-8"))
listings = d["listings"]
areas = sorted(set(l.get("area", "") for l in listings))
m2s = [l["m2"] for l in listings]
print(f"Total: {len(listings)}")
print(f"Areas: {areas}")
print(f"m2 range: {min(m2s)}~{max(m2s)}")
