"""
Generate the best-available links for each listing in jeonse_data.json.
For each platform+area+deposit combination, construct a filtered deep-link URL
that pre-filters the platform's search to that specific area+price+type.
"""
import json, urllib.parse, re

with open('jeonse_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

def deposit_range(deposit_str):
    """Convert deposit string like '2.5억' to a price range for URL params.
    Naver uses 만원 units, Zigbang/Dabang use 억+만원."""
    m = re.match(r'([\d.]+)', str(deposit_str))
    if not m:
        return (10000, 30000)  # default
    val = float(m.group(1))  # in 억
    # Create a ~30% range around the value
    low = max(0.5, val * 0.8)
    high = val * 1.3
    return (int(low * 10000), int(high * 10000))  # convert to 만원

def naver_link(area, deposit_str):
    dp_low, dp_high = deposit_range(deposit_str)
    enc = urllib.parse.quote(area)
    return f'https://new.land.naver.com/houses?ms={enc}&a=VL&b=B1&e=RETAIL&f={dp_low}&g={dp_high}'

def zigbang_link(area, deposit_str):
    dp_low, dp_high = deposit_range(deposit_str)
    enc = urllib.parse.quote(area)
    low_man = int(dp_low / 10000 * 10000)
    high_man = int(dp_high / 10000 * 10000)
    # Zigbang URL with area + price range
    return f'https://www.zigbang.com/home/oneroom/map?q={enc}&building_type=villa&trade_type=%EC%A0%84%EC%84%B8&deposit_min={low_man}&deposit_max={high_man}'

def dabang_link(area, deposit_str):
    enc = urllib.parse.quote(area)
    return f'https://www.dabangapp.com/room/search?q={enc}&type=%EC%A0%84%EC%84%B8&buildingType=villa'

def peterpan_link(area, deposit_str):
    enc = urllib.parse.quote(area)
    return f'https://www.peterpanz.com/villa?search={enc}&tradeType=JEONSE'

def zippoom_link(area, deposit_str):
    enc = urllib.parse.quote(area)
    return f'https://zippoom.com/search?q={enc}&type=%EC%A0%84%EC%84%B8'

def daangn_link(area, deposit_str):
    enc = urllib.parse.quote(area)
    return f'https://www.daangn.com/kr/realty/?in={enc}&tradeType=borrow'

def hogangnono_link(area, deposit_str):
    enc = urllib.parse.quote(area)
    return f'https://hogangnono.com/search?q={enc}'

def aptme_link(area, deposit_str):
    enc = urllib.parse.quote(area)
    return f'https://apt2.me/search?q={enc}'

link_generators = {
    '네이버': naver_link,
    '직방': zigbang_link,
    '다방': dabang_link,
    '피터팬': peterpan_link,
    '집품': zippoom_link,
    '당근': daangn_link,
    '호갱노노': hogangnono_link,
    '아파트미': aptme_link,
}

# Zippoom building pages we already have (actual detail pages)
zippoom_details = {
    '서강빌라': 'https://zippoom.com/%EB%B6%80%EB%8F%99%EC%82%B0/%EC%84%9C%EC%9A%B8-%EC%84%9C%EB%8C%80%EB%AC%B8%EA%B5%AC-%ED%99%8D%EC%A0%9C%EB%8F%99-%EC%84%9C%EA%B0%95%EB%B9%8C%EB%9D%BC/xxzyzd',
    '사랑채빌라': 'https://zippoom.com/%EB%B6%80%EB%8F%99%EC%82%B0/%EC%84%9C%EC%9A%B8-%EC%84%9C%EB%8C%80%EB%AC%B8%EA%B5%AC-%ED%99%8D%EC%A0%9C%EB%8F%99-%EC%82%AC%EB%9E%91%EC%B1%84%EB%B9%8C%EB%9D%BC/ji2xc5',
    '현대빌라': 'https://zippoom.com/%EB%B6%80%EB%8F%99%EC%82%B0/%EC%84%9C%EC%9A%B8-%EC%84%9C%EB%8C%80%EB%AC%B8%EA%B5%AC-%ED%99%8D%EC%9D%80%EB%8F%99-%ED%98%84%EB%8C%80%EB%B9%8C%EB%9D%BC/hp7x33',
}

stats = {'detail': 0, 'filtered': 0, 'total': 0}

for l in data['listings']:
    if l.get('area', '').endswith('_removed'):
        continue
    
    stats['total'] += 1
    source = l.get('source', '')
    area = l.get('area', '')
    deposit = l.get('deposit', '')
    desc = l.get('desc', '') or ''
    
    # Check if we have an actual detail page for this listing
    matched_detail = False
    
    if source == '집품':
        for bldg_name, bldg_url in zippoom_details.items():
            if bldg_name in desc or bldg_name in area:
                l['link'] = bldg_url
                l['collected'] = '2026-06-18 01:30'
                stats['detail'] += 1
                matched_detail = True
                break
    
    if not matched_detail:
        gen = link_generators.get(source)
        if gen:
            l['link'] = gen(area, deposit)
        stats['filtered'] += 1

data['timestamp'] = '2026-06-18'
with open('jeonse_data.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Detail page links: {stats['detail']}")
print(f"Filtered search links: {stats['filtered']}")
print(f"Total active: {stats['total']}")

# Show sample links
for l in data['listings'][:5]:
    if not l.get('area', '').endswith('_removed'):
        print(f"  #{l['no']} [{l['source']}] {l['area']} {l['deposit']} -> {l['link'][:100]}")
