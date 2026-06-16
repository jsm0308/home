"""Semi-automated listing updater for jeonse_data.json.

Usage:
    python update_listings.py new_listings.json
    python update_listings.py --mark-removed 5,12,23
    python update_listings.py --check-stale

The script:
1. Loads new listings from a JSON file and merges with existing data
2. Deduplicates by address/deposit/pyeong/floor combo
3. Marks listings as removed (appends "_removed" to area)
4. Regenerates jeonse_listings.csv
"""
import json, csv, sys, os, re, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
JSON_PATH = DATA_DIR / 'jeonse_data.json'
CSV_PATH = DATA_DIR / 'jeonse_listings.csv'

def load_json():
    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data):
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def listing_key(l):
    """Generate a dedup key: area + deposit + pyeong + floor + rooms."""
    area = (l.get('area') or '').replace('_removed', '')
    deposit = l.get('deposit', '')
    pyeong = str(l.get('pyeong', ''))
    floor = l.get('floor', '')
    rooms = str(l.get('rooms', ''))
    return f"{area}|{deposit}|{pyeong}|{floor}|{rooms}"

def merge_new(new_file):
    """Merge new listings from a JSON file."""
    with open(new_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    old = load_json()
    old_listings = [l for l in old['listings'] if not l.get('area', '').endswith('_removed')]

    existing_keys = set(listing_key(l) for l in old_listings)
    new_count = 0
    skip_count = 0
    next_no = max((l.get('no', 0) for l in old_listings), default=0) + 1

    for nl in new_data.get('listings', []):
        if listing_key(nl) in existing_keys:
            skip_count += 1
            continue
        nl['no'] = next_no
        next_no += 1
        old['listings'].append(nl)
        existing_keys.add(listing_key(nl))
        new_count += 1

    old['timestamp'] = datetime.date.today().isoformat()
    old['stats']['total'] = len([l for l in old['listings'] if not l.get('area', '').endswith('_removed')])
    save_json(old)
    print(f"Added {new_count} new listings, skipped {skip_count} duplicates.")
    return new_count

def mark_removed(no_list):
    """Mark listings as removed by appending '_removed' to area."""
    old = load_json()
    removed = 0
    for l in old['listings']:
        if l['no'] in no_list and not l.get('area', '').endswith('_removed'):
            l['area'] = l['area'] + '_removed'
            l['desc'] = (l.get('desc', '') + ' [매물없음]').strip()
            removed += 1

    old['stats']['total'] = len([l for l in old['listings'] if not l.get('area', '').endswith('_removed')])
    old['timestamp'] = datetime.date.today().isoformat()
    save_json(old)
    print(f"Marked {removed} listings as removed.")
    return removed

def regenerate_csv():
    """Regenerate CSV from JSON data."""
    data = load_json()
    rows = [
        ['번호', '지역', '유형', '보증금', '면적(m²)', '면적(평)', '층수', '방', '욕실', '향', '특징', '중개사', '출처', '등록일', '링크']
    ]
    for l in data['listings']:
        is_removed = l.get('area', '').endswith('_removed')
        area = l['area'].replace('_removed', '')
        rows.append([
            l['no'], area, l['type'], l['deposit'], l['m2'], l['pyeong'],
            l.get('floor', ''), l.get('rooms', ''), l.get('bath', ''),
            l.get('dir', ''), l.get('desc', ''), l.get('agent', ''),
            l.get('source', ''), l.get('date', ''), l.get('link', '')
        ])

    with open(CSV_PATH, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"CSV regenerated with {len(rows)-1} rows.")

def check_stale(days=3):
    """Check if data is stale and print status."""
    data = load_json()
    ts = data.get('timestamp', 'unknown')
    print(f"Last update: {ts}")
    print(f"Total active listings: {data['stats']['total']}")
    try:
        last_date = datetime.date.fromisoformat(ts)
        age = (datetime.date.today() - last_date).days
        print(f"Age: {age} days {'(STALE!)' if age >= days else '(OK)'}")
    except:
        print("Could not parse timestamp.")

if __name__ == '__main__':
    if '--check-stale' in sys.argv:
        days = 3
        try:
            idx = sys.argv.index('--days')
            days = int(sys.argv[idx + 1])
        except:
            pass
        check_stale(days)
    elif '--mark-removed' in sys.argv:
        try:
            idx = sys.argv.index('--mark-removed')
            no_list = [int(x.strip()) for x in sys.argv[idx + 1].split(',')]
            mark_removed(no_list)
            regenerate_csv()
        except (IndexError, ValueError) as e:
            print(f"Error parsing --mark-removed: {e}")
            print("Usage: python update_listings.py --mark-removed 5,12,23")
    elif len(sys.argv) > 1 and not sys.argv[1].startswith('--'):
        count = merge_new(sys.argv[1])
        if count > 0:
            regenerate_csv()
    else:
        print("Usage:")
        print("  python update_listings.py new_listings.json   # merge new listings")
        print("  python update_listings.py --mark-removed 5,12 # mark removed")
        print("  python update_listings.py --check-stale        # check freshness")
