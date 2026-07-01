"""
Extract existing briefing and investment data for dashboard.

Reads:
  - 순살브리핑 (2_Wiki/순살-브리핑/) -- 210 pages, 3 types
  - Investment CSV cache (scripts/investment/data/cache/) -- BTC, SPX, KOSPI

Outputs:
  - data/soonsal-briefings.json -- latest 7 days of briefings
  - data/investment.json -- real portfolio + market data
"""
import os, json, re, csv
from datetime import datetime
from collections import defaultdict

WIKI_DIR = r"C:\Users\Gram\Desktop\jsm obsidian\jsm personal agents (obsidian files)\Agents\2_Wiki"
SOONSAL_DIR = os.path.join(WIKI_DIR, "순살-브리핑")
CSV_DIR = r"C:\Users\Gram\Desktop\jsm personal agents\scripts\investment\data\cache"
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def parse_frontmatter(content):
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


def extract_soonsal():
    """Extract latest 7 days of 순살브리핑 (all 3 types)."""
    if not os.path.isdir(SOONSAL_DIR):
        return []

    files = sorted(os.listdir(SOONSAL_DIR))
    # Group by date, get latest per type per day
    by_date_type = defaultdict(dict)
    for f in files:
        if not f.endswith(".md"):
            continue
        # Parse date from filename: 순살briefing-20260622.md or 순살crypto-20260622.md etc
        match = re.search(r'(\d{8})', f)
        if not match:
            continue
        date = match.group(1)
        if "briefing" in f and "crypto" not in f:
            t = "briefing"
        elif "crypto" in f:
            t = "crypto"
        elif "cardnews" in f:
            t = "cardnews"
        else:
            continue
        by_date_type[date][t] = f

    # Get latest 7 dates
    dates = sorted(by_date_type.keys(), reverse=True)[:7]
    result = []

    for date in dates:
        entry = {"date": date, "types": {}}
        for t in ["briefing", "crypto", "cardnews"]:
            fname = by_date_type[date].get(t)
            if not fname:
                continue
            path = os.path.join(SOONSAL_DIR, fname)
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            fm, body = parse_frontmatter(content)

            # Extract title
            title = f"{t} {date}"
            for line in body.split("\n"):
                stripped = line.strip()
                if stripped.startswith("# ") and not stripped.startswith("## "):
                    title = stripped[2:].strip()
                    break

            # Extract key issues section or first meaningful content
            summary = extract_section(body, "핵심 이슈") or extract_section(body, "Key Issues") or extract_first_paragraphs(body, 3)
            markets_section = extract_section(body, "Markets") or extract_section(body, "Crypto Markets")
            # Also extract the %% section headers
            market_lines = extract_markets(body)

            entry["types"][t] = {
                "title": title,
                "summary": summary[:400] if summary else "",
                "markets": market_lines,
                "hasContent": True
            }

        result.append(entry)

    return result


def extract_section(body, heading):
    """Extract content under a ## heading."""
    lines = body.split("\n")
    capture = False
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and heading.lower() in stripped.lower():
            capture = True
            continue
        if stripped.startswith("## ") and capture:
            break
        if capture and stripped:
            clean = re.sub(r'\*{1,3}', '', stripped)
            clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', clean)
            result.append(clean)
    return " ".join(result[:8])  # first 8 lines


def extract_markets(body):
    """Extract market data lines (BTC, S&P etc)."""
    market_patterns = [r'BTC.*?\$[\d,]+', r'S&P.*?[\d,]+', r'NASDAQ.*?[\d,]+',
                       r'KOSPI.*?[\d,]+', r'ETH.*?\$[\d,]+', r'SOL.*?\$[\d,]+',
                       r'Fear & Greed.*?\d+']
    lines = body.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- ") and not stripped.startswith("* "):
            continue
        for pat in market_patterns:
            if re.search(pat, stripped):
                clean = re.sub(r'\*{1,3}', '', stripped).strip("- ")
                result.append(clean)
                break
    return result[:10]


def extract_first_paragraphs(body, count):
    """Extract first N non-heading non-empty lines."""
    lines = body.split("\n")
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("---") or stripped.startswith("```"):
            continue
        if stripped.startswith("Source:") or stripped.startswith("builds on") or stripped.startswith("applies to"):
            continue
        clean = re.sub(r'\*{1,3}', '', stripped)
        clean = re.sub(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]', r'\1', clean)
        result.append(clean)
        if len(result) >= count:
            break
    return " ".join(result)


def extract_csv_tail(path, rows=1, skip_header=True):
    """Get last N rows of a CSV."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        reader = list(csv.reader(fh))
    if len(reader) < 2:
        return None
    # last data row
    row = reader[-1]
    # Columns: ,open,high,low,close,volume
    try:
        return {
            "date": row[0] if len(row) > 0 else "",
            "close": float(row[4]) if len(row) > 4 else 0
        }
    except (ValueError, IndexError):
        return None


def extract_investment():
    """Extract real portfolio + market data."""
    btc = extract_csv_tail(os.path.join(CSV_DIR, "BTC_1d.csv"))
    spx = extract_csv_tail(os.path.join(CSV_DIR, "SPX_1d.csv"))
    kospi = extract_csv_tail(os.path.join(CSV_DIR, "KOSPI_1d.csv"))
    nasdaq = extract_csv_tail(os.path.join(CSV_DIR, "NASDAQ_1d.csv"))

    return {
        "lastUpdated": datetime.now().isoformat(),
        "portfolio": {
            "totalValue": 1500000,
            "currency": "KRW",
            "allocations": [
                {"asset": "현금 (버퍼)", "amount": 1000000, "target": "67%", "drift": 0},
                {"asset": "BTC 진입 대기", "amount": 500000, "target": "33%", "drift": 0}
            ],
            "lastRebalance": None,
            "needsRebalance": False
        },
        "markets": {
            "btc": {"price": int(btc["close"]) if btc else 0, "date": btc["date"] if btc else ""},
            "sp500": {"price": round(spx["close"], 2) if spx else 0, "date": spx["date"] if spx else ""},
            "kospi": {"price": round(kospi["close"], 2) if kospi else 0, "date": kospi["date"] if kospi else ""},
            "nasdaq": {"price": round(nasdaq["close"], 2) if nasdaq else 0, "date": nasdaq["date"] if nasdaq else ""}
        }
    }


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # 순살 브리핑 추출
    briefings = extract_soonsal()
    path = os.path.join(OUT_DIR, "soonsal-briefings.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(briefings, fh, ensure_ascii=False, indent=2)
    print(f"Soonsal briefings: {len(briefings)} days -> {path}")

    # 투자 데이터 추출
    inv = extract_investment()
    path = os.path.join(OUT_DIR, "investment.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(inv, fh, ensure_ascii=False, indent=2)
    print(f"Investment data -> {path}")
    btc_won = inv['markets']['btc']['price']
    spx_val = inv['markets']['sp500']['price']
    kospi_val = inv['markets']['kospi']['price']
    nasdaq_val = inv['markets']['nasdaq']['price']
    print(f"  BTC: {btc_won:,.0f} KRW ({inv['markets']['btc']['date'][:10]})")
    print(f"  SP500: {spx_val} ({inv['markets']['sp500']['date'][:10]})")
    print(f"  KOSPI: {kospi_val} ({inv['markets']['kospi']['date'][:10]})")
    print(f"  NASDAQ: {nasdaq_val} ({inv['markets']['nasdaq']['date'][:10]})")


if __name__ == "__main__":
    main()
