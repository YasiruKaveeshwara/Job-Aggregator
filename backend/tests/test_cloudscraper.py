import cloudscraper
from bs4 import BeautifulSoup

scraper = cloudscraper.create_scraper()
url = "https://anyjobok.com/?q=software+engineer"
r = scraper.get(url)
soup = BeautifulSoup(r.text, 'html.parser')
cards = soup.select('a[href*="/jobs/"]')
print(f'Number of cards found for URL {url}: {len(cards)}')
if len(cards) > 0:
    for c in cards[:5]:
        print(c.get('href'))
