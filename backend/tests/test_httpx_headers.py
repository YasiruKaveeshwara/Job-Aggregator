import httpx
from bs4 import BeautifulSoup

url = 'https://anyjobok.com/'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Dest': 'document'
}
r = httpx.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')
cards = soup.select('a[href*="/jobs/"]')
print(f'Found {len(cards)} cards')
