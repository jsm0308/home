import json
with open('jeonse_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

good = []
area_search = []
homepage = []
for l in data['listings']:
    if l.get('area', '').endswith('_removed'):
        continue
    link = l.get('link', '')
    if '/home/oneroom/detail/' in link or '/부동산/서울' in link or 'daangn.com/kr/realty/' in link and '?in=' not in link:
        good.append(l)
    elif 'search?q=' in link or '?ms=' in link or '?in=' in link:
        area_search.append(l)
    else:
        homepage.append(l)

print(f"=== REAL LISTING PAGES: {len(good)} ===")
for l in good[:10]:
    print(f"  #{l['no']} [{l['source']}] {l['area']} {l['deposit']} {l['pyeong']}p -> {l['link'][:100]}")

print(f"\n=== AREA SEARCH: {len(area_search)} ===")
for l in area_search[:5]:
    print(f"  #{l['no']} [{l['source']}] {l['area']} {l['deposit']} {l['pyeong']}p -> {l['link'][:100]}")

print(f"\n=== HOMEPAGE ONLY: {len(homepage)} ===")
for l in homepage[:5]:
    print(f"  #{l['no']} [{l['source']}] {l['area']} {l['deposit']} {l['pyeong']}p -> {l['link'][:100]}")
