"""
naverland-scrapper CSV/Excel output → jeonse_data.json converter.

naverland-scrapper columns (approximate):
  복합단지코드(complexNo), 단지명(complexName), 거래유형(tradeType): 전세=B1,
  보증금(deposit), 월세(monthlyRent) - 전세는 보증금만,
  전용면적(exclusiveArea), 공급면적(supplyArea),
  층(floor), 방향(direction), 방수(roomCount), 욕실수(bathroomCount),
  주소(address), 매물번호(articleNo), 등록일(registrationDate),
  중개사(agentName), 중개사연락처(agentPhone)

Usage:
  python scripts/convert_naverland.py naverland-scrapper/output.csv
  → jeonse_data.json 업데이트

Or detect the latest output file automatically:
  python scripts/convert_naverland.py
"""

import csv
import json
import sys
import os
import glob
import re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# Target areas we care about (extracted via dong detection)
TARGET_DONGS = ["홍제동", "홍은동", "연희동", "남가좌동", "북가좌동", "신사동", "응암동"]

# Excluded floor types
EXCLUDED_FLOORS = {
    "1층", "1 층",
    "반지하", "반지층", "지하", "지층", "지하1층", "지하 1층", "B1",
    "옥탑", "옥탑방", "꼭대기",
}

# Max deposit for jeonse (KRW 2.5억 = 25000만원)
MAX_DEPOSIT_MAN = 25000

# Preferred area range (pyeong): 15~25
MIN_PYEONG = 15
MAX_PYEONG = 30


def extract_dong(address: str) -> str | None:
    """Extract 동 name from Korean address like '서울 서대문구 홍제동 123-4'."""
    if not address:
        return None
    # Try: 서울 서대문구 XX동 or 경기 수원시 영통구 XX동
    m = re.search(r'(\S{1,4}동)\b', address)
    if m:
        dong = m.group(1)
        # Filter out non-dong matches like "00동" (complex building numbers)
        if re.search(r'[가-힣]', dong):
            return dong
    return None


def parse_deposit_manwon(value_str: str) -> int | None:
    """Parse deposit string to integer만원. Handles '3억9,000' → 39000."""
    if not value_str:
        return None
    value_str = value_str.replace(" ", "").replace(",", "")
    # "3억9000" or "3억9,000" pattern
    m = re.match(r'(\d+)억(\d*)', value_str)
    if m:
        eok = int(m.group(1)) * 10000
        man = int(m.group(2)) if m.group(2) else 0
        return eok + man
    # Pure 만원: "39000"
    try:
        return int(value_str)
    except ValueError:
        return None


def find_latest_csv() -> str | None:
    """Find the latest CSV output from naverland-scrapper."""
    candidates = glob.glob("naverland-scrapper/**/*.csv", recursive=True)
    if not candidates:
        candidates = glob.glob("naverland-scrapper/**/*.xlsx", recursive=True)
    if candidates:
        return max(candidates, key=os.path.getmtime)
    return None


def read_csv_to_listings(csv_path: str) -> list[dict]:
    """Read naverland-scrapper CSV and convert to jeonse_data.json listing format."""
    listings = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        has_trade_type = any(c for c in columns if c and ('tradeType' in c or 'trade_type' in c or '거래' in c))

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # --- Filter: trade type must be B1 (jeonse) ---
            if has_trade_type:
                trade = row.get("tradeType", row.get("trade_type", row.get("거래유형", "")))
                if "B1" not in str(trade) and "전세" not in str(trade):
                    continue

            # --- Filter: deposit <= 2.5억 ---
            deposit_raw = row.get("deposit", row.get("보증금", row.get("price", "")))
            deposit_man = parse_deposit_manwon(str(deposit_raw))
            if deposit_man is not None and deposit_man > MAX_DEPOSIT_MAN:
                continue

            # --- Filter: exclude 1st floor, semi-basement, rooftop ---
            floor_raw = row.get("floor", row.get("층", ""))
            floor_str = str(floor_raw).strip()
            if any(excl in floor_str for excl in EXCLUDED_FLOORS):
                continue

            # --- Area ---
            address = row.get("address", row.get("주소", row.get("roadAddress", row.get("도로명주소", ""))))
            dong = extract_dong(str(address))
            if not dong:
                # Fallback: use _source_dong from direct crawl
                dong = row.get("_source_dong", "")
            if not dong:
                continue

            # --- Pyeong ---
            m2_raw = row.get("exclusiveArea", row.get("전용면적", row.get("supplyArea", row.get("공급면적", ""))))
            try:
                m2 = float(m2_raw) if m2_raw else 0
            except (ValueError, TypeError):
                m2 = 0
            if m2 <= 0:
                continue
            pyeong = round(m2 / 3.3058, 1)
            if pyeong < MIN_PYEONG:
                continue

            # --- Floor formatting ---
            total_floor = row.get("totalFloor", row.get("전체층수", row.get("buildingFloor", "")))
            if total_floor and str(total_floor).strip():
                floor_display = f"{floor_str}층/{total_floor}층"
            else:
                # Try to parse "2/5" pattern
                if "/" in floor_str:
                    parts = floor_str.split("/")
                    floor_display = f"{parts[0].strip()}층/{parts[1].strip()}층"
                else:
                    floor_display = f"{floor_str}층"

            # --- Deposit display ---
            if deposit_man:
                if deposit_man >= 10000:
                    deposit_display = f"{deposit_man/10000:.1f}억".replace(".0억", "억")
                else:
                    deposit_display = f"{deposit_man}만원"
            else:
                deposit_display = str(deposit_raw)

            # --- Rooms/Bath ---
            rooms_raw = row.get("roomCount", row.get("방수", row.get("rooms", "")))
            bath_raw = row.get("bathroomCount", row.get("욕실수", row.get("bath", "")))

            # --- Direction ---
            dir_raw = row.get("direction", row.get("방향", row.get("dir", "")))

            # --- Link (build Naver detail URL from articleNo or complexNo) ---
            article_no = row.get("articleNo", row.get("매물번호", row.get("article_no", "")))
            complex_no = row.get("complexNo", row.get("단지번호", row.get("complex_no", "")))
            if article_no:
                link = f"https://new.land.naver.com/houses?ms=&a=VL&b=B1&e=RETAIL&articleNo={article_no}"
            elif complex_no:
                link = f"https://new.land.naver.com/complexes/{complex_no}"
            else:
                link = ""

            listings.append({
                "area": dong,
                "type": "빌라",
                "deposit": deposit_display,
                "m2": int(m2),
                "pyeong": pyeong,
                "floor": floor_display,
                "rooms": str(rooms_raw).strip() if rooms_raw else "-",
                "bath": str(bath_raw).strip() if bath_raw else "-",
                "dir": str(dir_raw).strip() if dir_raw else "-",
                "desc": row.get("complexName", row.get("단지명", "")),
                "agent": row.get("agentName", row.get("중개사", "")),
                "source": "네이버",
                "date": row.get("registrationDate", row.get("등록일", datetime.now(KST).strftime("%Y-%m-%d"))),
                "link": link,
                "collected": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
            })

    return listings


def merge_listings(existing_path: str, new_listings: list[dict]) -> list[dict]:
    """Merge new listings into existing, deduplicating by area+m2+deposit floor."""
    existing = []
    if os.path.exists(existing_path):
        with open(existing_path, encoding="utf-8") as f:
            data = json.load(f)
            existing = data.get("listings", [])

    # Build dedup key set from existing
    keys = set()
    for l in existing:
        key = (l["area"], l["m2"], l["deposit"], l.get("floor", ""))
        keys.add(key)

    # Rebuild listing numbers
    merged = []
    for l in existing:
        merged.append(l)

    added = 0
    for l in new_listings:
        key = (l["area"], l["m2"], l["deposit"], l.get("floor", ""))
        if key not in keys:
            merged.append(l)
            keys.add(key)
            added += 1

    # Renumber
    for i, l in enumerate(merged):
        l["no"] = i + 1

    # Compute stats
    areas = sorted(set(l["area"] for l in merged))

    return merged, added, areas


def main():
    if len(sys.argv) > 1:
        csv_path = sys.argv[1]
    else:
        csv_path = find_latest_csv()

    if not csv_path or not os.path.exists(csv_path):
        print("No naverland-scrapper CSV found. Usage: python convert_naverland.py <path_to_csv>")
        sys.exit(1)

    print(f"Reading: {csv_path}")
    listings = read_csv_to_listings(csv_path)
    print(f"Parsed {len(listings)} valid listings (jeonse, <=2.5억, not 1F/B1/rooftop)")

    output_path = "../jeonse_data.json"
    merged, added, areas = merge_listings(output_path, listings)

    output = {
        "timestamp": datetime.now(KST).strftime("%Y-%m-%d"),
        "version": "1.2",
        "stats": {
            "total": len(merged),
            "areas": areas,
        },
        "listings": merged,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Merged: {len(merged)} total, {added} new, {len(areas)} areas")
    print(f"Written: {os.path.abspath(output_path)}")


if __name__ == "__main__":
    main()
