import httpx
from bs4 import BeautifulSoup

url = "https://anyjobok.com/?q=software+engineer"
r = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(r.text, 'html.parser')
cards = soup.select('a[href*="/jobs/"]')
print(f'Number of cards found for URL {url}: {len(cards)}')
if len(cards) > 0:
    for c in cards[:5]:
        print(c.get('href'))

url2 = "https://anyjobok.com"
r2 = httpx.get(url2, headers={'User-Agent': 'Mozilla/5.0'})
soup2 = BeautifulSoup(r2.text, 'html.parser')
cards2 = soup2.select('a[href*="/jobs/"]')
print(f'Number of cards found for URL {url2}: {len(cards2)}')
if len(cards2) > 0:
    for c in cards2[:5]:
        print(c.get('href'))
