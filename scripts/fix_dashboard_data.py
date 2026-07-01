"""
Fix and update all dashboard JSON data files.

1. Clean soonsal-briefings.json — strip raw HTML/CSS from summaries
2. Add investmentDaily + investmentWeekly to investment.json
3. Create prompt journal weekly review in system-health.json
4. Update market data from CSV caches
"""
import os, json, re, csv
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CSV_DIR = r"C:\Users\Gram\Desktop\jsm personal agents\scripts\investment\data\cache"
PROMPT_JOURNAL_PATH = r"C:\Users\Gram\Desktop\jsm obsidian\jsm personal agents (obsidian files)\Agents\2_Wiki\System-Meta\prompt-journal.md"


def clean_html(text):
    """Strip HTML tags, CSS blocks, and email template cruft."""
    if not text:
        return ""
    # Remove CSS blocks
    text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove CSS blocks (raw CSS inside markdown)
    text = re.sub(r'\{[^}]*\}', ' ', text)
    # Remove email template cruft (CSS properties that survived)
    text = re.sub(r'@import\s+url\([^)]+\);?', '', text)
    # Remove standalone CSS property leftovers
    css_props = ['font-family', 'background-color', 'background', 'margin', 'padding',
                 'color', 'font-size', 'line-height', 'border-radius', 'max-width',
                 'width', 'display', 'flex-direction', 'align-items', 'gap',
                 'border', 'box-sizing', 'overflow', 'text-decoration', 'position',
                 'top', 'left', 'right', 'bottom', 'z-index', 'min-height',
                 'cursor', 'visibility', 'opacity', 'transform', 'transition']
    for prop in css_props:
        text = re.sub(r'\b' + prop + r'\s*:\s*[^;}\n]+[;}]?\s*', '', text, flags=re.IGNORECASE)
    # Remove leftover CSS class selectors like ".wrapper", ".bd-body", etc
    text = re.sub(r'\.\w[\w-]*\s*\{[^}]*\}', '', text)
    # Remove "body " and "html " leftovers
    text = re.sub(r'\b(body|html|div|span|p|a|h\d|ul|li|table|tr|td|th)\s*\{[^}]*\}', '', text)
    # Remove emoji markers
    text = re.sub(r'[\U0001F300-\U0001F9FF]', '', text)
    # Remove "body" and ".wrapper" remnants
    text = re.sub(r'\b(body|\.wrapper|\.container)\b', '', text)
    # Clean up whitespace
    text = re.sub(r'\s{3,}', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    # Remove empty brackets and parentheses remnants
    text = re.sub(r'[{}\[\]]', '', text)
    text = text.strip()
    return text


def clean_soonsal():
    """Clean HTML garbage from soonsal-briefings.json summaries."""
    path = os.path.join(DATA_DIR, "soonsal-briefings.json")
    if not os.path.exists(path):
        print("soonsal-briefings.json not found")
        return

    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    cleaned = 0
    for entry in data:
        for t in entry.get("types", {}):
            item = entry["types"][t]
            old_summary = item.get("summary", "")
            new_summary = clean_html(old_summary)
            if new_summary != old_summary:
                item["summary"] = new_summary
                cleaned += 1

            old_title = item.get("title", "")
            new_title = clean_html(old_title)
            if new_title != old_title:
                item["title"] = new_title

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    print(f"Soonsal briefings: cleaned {cleaned} summaries, {len(data)} days total")


def extract_csv_tail(path, rows=1):
    """Get last N rows of a CSV."""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        reader = list(csv.reader(fh))
    if len(reader) < 2:
        return None
    row = reader[-1]
    try:
        return {
            "date": row[0] if len(row) > 0 else "",
            "close": float(row[4]) if len(row) > 4 else 0
        }
    except (ValueError, IndexError):
        return None


def update_investment():
    """Update investment.json with market data and briefing."""
    path = os.path.join(DATA_DIR, "investment.json")

    # Load existing
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            inv = json.load(fh)
    else:
        inv = {}

    # Update market data
    btc = extract_csv_tail(os.path.join(CSV_DIR, "BTC_1d.csv"))
    spx = extract_csv_tail(os.path.join(CSV_DIR, "SPX_1d.csv"))
    kospi = extract_csv_tail(os.path.join(CSV_DIR, "KOSPI_1d.csv"))
    nasdaq = extract_csv_tail(os.path.join(CSV_DIR, "NASDAQ_1d.csv"))

    inv["lastUpdated"] = datetime.now().isoformat()
    inv["markets"] = {
        "btc": {"price": int(btc["close"]) if btc else 0, "date": btc["date"] if btc else ""},
        "sp500": {"price": round(spx["close"], 2) if spx else 0, "date": spx["date"] if spx else ""},
        "kospi": {"price": round(kospi["close"], 2) if kospi else 0, "date": kospi["date"] if kospi else ""},
        "nasdaq": {"price": round(nasdaq["close"], 2) if nasdaq else 0, "date": nasdaq["date"] if nasdaq else ""}
    }

    if "portfolio" not in inv:
        inv["portfolio"] = {
            "totalValue": 1500000,
            "currency": "KRW",
            "allocations": [
                {"asset": "현금 (버퍼)", "amount": 1000000, "target": "67%", "drift": 0},
                {"asset": "BTC 진입 대기", "amount": 500000, "target": "33%", "drift": 0}
            ],
            "lastRebalance": None,
            "needsRebalance": False
        }

    # Add investment daily briefing (updated manually or via Coach)
    inv["investmentDaily"] = inv.get("investmentDaily", {
        "summary": "7/1: BTC 9,695만원. 순살브리핑 아카이브 정리 완료 (210개→인사이트 요약). PCE 데이터 대기 중. 투자 루틴 정상 작동.",
        "date": datetime.now().strftime("%Y-%m-%d")
    })

    inv["investmentWeekly"] = inv.get("investmentWeekly", {
        "summary": "6/23-6/29 주간: BTC $64K 박스권 (Fear & Greed 23 극한공포). S&P 7,431, KOSPI 8,123. 워시 매파 FOMC 이후 시장 관망세. 청년미래적금 7/3 마감. BTC 1차 진입은 PCE 이후 결정 유지.",
        "date": "2026-06-29"
    })

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(inv, fh, ensure_ascii=False, indent=2)

    btc_won = inv['markets']['btc']['price']
    print(f"Investment data updated:")
    print(f"  BTC: {btc_won:,.0f} KRW ({inv['markets']['btc']['date'][:10]})")
    print(f"  SP500: {inv['markets']['sp500']['price']}")
    print(f"  KOSPI: {inv['markets']['kospi']['price']}")
    print(f"  NASDAQ: {inv['markets']['nasdaq']['price']}")
    print(f"  Daily briefing: {inv['investmentDaily']['date']}")
    print(f"  Weekly briefing: {inv['investmentWeekly']['date']}")


def parse_prompt_journal():
    """Parse prompt-journal.md and create weekly review for system-health.json."""
    health_path = os.path.join(DATA_DIR, "system-health.json")

    if os.path.exists(health_path):
        with open(health_path, "r", encoding="utf-8") as fh:
            health = json.load(fh)
    else:
        health = {}

    # Parse prompt-journal.md to find entries from last week (6/23-6/29)
    pj_data = {
        "weekOf": "2026-06-23 ~ 2026-06-29",
        "totalSessions": 0,
        "totalPrompts": 0,
        "avgScore": 0,
        "topPatterns": [],
        "antipatterns": [],
        "focus": ""
    }

    if os.path.exists(PROMPT_JOURNAL_PATH):
        with open(PROMPT_JOURNAL_PATH, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Find entries from 6/23-6/29
        entries = re.findall(r'### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}).*?session: (\S+)', content)
        week_entries = [e for e in entries if "2026-06-2" in e[0] and e[0][:10] >= "2026-06-23"]

        # Count prompts in those sessions
        prompts_found = re.findall(r'\*\*Prompts analyzed\*\*: (\d+)', content)
        
        if week_entries:
            pj_data["totalSessions"] = len(week_entries)
            # Extract prompt counts - find the section after "6-24" entries
            # Look for Session Summary tables
            summaries = re.findall(r'### Session Summary.*?(?=###|---$)', content, re.DOTALL)
            
            total_clarity = 0
            total_prompts = 0
            dims = {"Clarity": [], "Structure": [], "Context Density": [], "Token Efficiency": [], "Outcome": []}
            
            # Parse individual prompt scores
            score_blocks = re.findall(r'\*\*Prompts analyzed\*\*: (\d+)(.*?)(?=#### Prompt|---\s*$|### Session)', content, re.DOTALL)
            
            for block in prompts_found:
                total_prompts += int(block)

            # Extract scores from prompt entries
            score_matches = re.findall(r'\*\*(Clarity|Structure|Context Density|Token Efficiency|Outcome)\*\*: (\d)/5', content)
            for dim, score in score_matches:
                if dim in dims:
                    dims[dim].append(int(score))

            if total_prompts > 0:
                pj_data["totalPrompts"] = total_prompts
                
                # Calculate average from scores
                all_scores = []
                for d in dims.values():
                    all_scores.extend(d)
                if all_scores:
                    pj_data["avgScore"] = round(sum(all_scores) / len(all_scores), 1)

            # Find patterns
            antipatterns = re.findall(r'\*\*Antipattern.*?\*\*:\s*(.+?)(?=\n|$)', content)
            if antipatterns:
                pj_data["antipatterns"] = [a.strip() for a in antipatterns[-2:]]
            
            patterns = re.findall(r'\*\*Top Pattern.*?\*\*:\s*(.+?)(?=\n|$)', content)
            if patterns:
                pj_data["topPatterns"] = [p.strip() for p in patterns[-2:]]

            # Focus
            focus = re.findall(r'\*\*Next.*?Focus\*\*:\s*(.+?)(?=\n|$)', content)
            if focus:
                pj_data["focus"] = focus[-1].strip()
            elif not pj_data["focus"]:
                pj_data["focus"] = "프롬프트 저널 데이터 있음. 주간 리뷰 실행 필요."
        else:
            pj_data["focus"] = "지난주(6/23-6/29) 프롬프트 저널 엔트리 없음. 세션 기록 확인 필요."

    health["lastUpdated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
    health["promptJournal"] = pj_data

    # Ensure systemHealth has a default
    if "systemHealth" not in health:
        health["systemHealth"] = {
            "lastAudit": None,
            "lastLint": None,
            "wikiPages": 340,
            "orphanPages": 0,
            "brokenLinks": 0,
            "skills": [
                {"name": "crypto-bot", "version": "v1", "status": "active", "lastTested": "2026-06-29"},
                {"name": "deep-research", "version": "v2", "status": "active", "lastTested": "2026-06-27"},
                {"name": "investment-agent", "version": "v1", "status": "active", "lastTested": "2026-06-29"},
                {"name": "study-coach", "version": "v1", "status": "active", "lastTested": "2026-06-28"},
                {"name": "career-coach", "version": "v1", "status": "active", "lastTested": "2026-06-25"},
                {"name": "research-review", "version": "v1", "status": "active", "lastTested": "2026-06-23"},
                {"name": "spec", "version": "v1", "status": "active", "lastTested": "2026-06-20"},
                {"name": "frontend-design", "version": "v1", "status": "active", "lastTested": "2026-07-01"},
                {"name": "product-search", "version": "v1", "status": "active", "lastTested": "2026-06-30"}
            ],
            "alwaysOnRules": 17,
            "onDemandRules": 9,
            "targetMax": 6
        }
    else:
        health["systemHealth"]["wikiPages"] = 340
        health["systemHealth"]["skills"] = [
            {"name": "crypto-bot", "version": "v1", "status": "active", "lastTested": "2026-06-29"},
            {"name": "deep-research", "version": "v2", "status": "active", "lastTested": "2026-06-27"},
            {"name": "investment-agent", "version": "v1", "status": "active", "lastTested": "2026-06-29"},
            {"name": "study-coach", "version": "v1", "status": "active", "lastTested": "2026-06-28"},
            {"name": "career-coach", "version": "v1", "status": "active", "lastTested": "2026-06-25"},
            {"name": "research-review", "version": "v1", "status": "active", "lastTested": "2026-06-23"},
            {"name": "spec", "version": "v1", "status": "active", "lastTested": "2026-06-20"},
            {"name": "frontend-design", "version": "v1", "status": "active", "lastTested": "2026-07-01"},
            {"name": "product-search", "version": "v1", "status": "active", "lastTested": "2026-06-30"}
        ]
        health["systemHealth"]["alwaysOnRules"] = 17
        health["systemHealth"]["targetMax"] = 6

    with open(health_path, "w", encoding="utf-8") as fh:
        json.dump(health, fh, ensure_ascii=False, indent=2)

    print(f"Prompt journal updated: {pj_data['totalSessions']} sessions, {pj_data['totalPrompts']} prompts, avg {pj_data['avgScore']}")
    print(f"  Focus: {pj_data['focus']}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    print("=== Cleaning Soonsal briefings ===")
    clean_soonsal()

    print("\n=== Updating investment data ===")
    update_investment()

    print("\n=== Parsing prompt journal ===")
    parse_prompt_journal()

    print("\nDone. All JSON files updated.")


if __name__ == "__main__":
    main()
