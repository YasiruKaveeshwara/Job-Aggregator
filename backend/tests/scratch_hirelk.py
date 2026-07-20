import httpx, sys, re, json
from html import unescape
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Try a few queries
for q in ["software", "developer", "engineer"]:
    r = httpx.get(f'https://hire.lk/jobs?q={q}&location=', headers=HEADERS, timeout=20)
    soup = BeautifulSoup(r.text, 'html.parser')
    cards = soup.select('article[data-card]')
    m = re.search(r'(\d+)\s+jobs? found', r.text)
    count_text = m.group(0) if m else "not found"
    print(f"Query '{q}': {len(cards)} cards in HTML, page says: {count_text}")
    if cards:
        data = json.loads(unescape(cards[0].get('data-card', '{}')))
        print(f"  Sample: {data.get('title')} | {data.get('company_name')} | {data.get('location')}")
        print(f"  URL: {data.get('detail_url')}")

# Test pagination
r2 = httpx.get('https://hire.lk/jobs?q=software&location=&page=2', headers=HEADERS, timeout=20)
cards2 = BeautifulSoup(r2.text, 'html.parser').select('article[data-card]')
print(f"\nPage 2 for 'software': {len(cards2)} cards")

# Also try IT industry browse
r3 = httpx.get('https://hire.lk/jobs?industry=it-software-engineering-web-cloud', headers=HEADERS, timeout=20)
cards3 = BeautifulSoup(r3.text, 'html.parser').select('article[data-card]')
m3 = re.search(r'(\d+)\s+jobs? found', r3.text)
print(f"\nIT industry browse: {len(cards3)} cards, page says: {m3.group(0) if m3 else 'not found'}")
