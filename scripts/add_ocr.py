import json
from datetime import datetime

jpath = r'C:\Users\Gram\Desktop\전세\jeonse_data.json'
with open(jpath, 'r', encoding='utf-8') as f:
    data = json.load(f)

listing = {
    'no': len(data['listings']) + 1,
    'area': '홍제동',
    'type': '다가구',
    'deposit': '2.5억',
    'm2': 53.25,
    'pyeong': round(53.25 / 3.306, 1),
    'floor': '2층/2층',
    'rooms': '3',
    'bath': '-',
    'dir': '-',
    'desc': '홍제역세권 올수리 후첫입주 방3 욕실단독사용, 준공1992, 즉시입주',
    'agent': '정공인중개사사무소 02-379-1472',
    'source': '네이버',
    'date': '2026-06-18',
    'link': 'https://new.land.naver.com/houses?articleNo=2631630284',
    'collected': '2026-06-18 03:01'
}

data['listings'].append(listing)
data['timestamp'] = '2026-06-18'
with open(jpath, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Added: {listing['area']} {listing['deposit']} {listing['pyeong']}평")
print(f"Total: {len(data['listings'])} listings")
print(f"Link: {listing['link']}")
