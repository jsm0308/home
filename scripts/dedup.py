import json

jpath = 'jeonse_data.json'
with open(jpath, 'r', encoding='utf-8') as f:
    d = json.load(f)

seen = set()
unique = []
for l in d['listings']:
    key = str(l.get('no', '')) + '|' + str(l.get('area', '')) + '|' + str(l.get('deposit', '')) + '|' + str(l.get('pyeong', ''))
    if key not in seen:
        seen.add(key)
        unique.append(l)

d['listings'] = unique
with open(jpath, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f'Dedup: {len(unique)} listings')
