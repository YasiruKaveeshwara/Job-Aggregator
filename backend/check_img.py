import sys
from bs4 import BeautifulSoup
import httpx

for url, selector in [
    ("https://jobenvoy.com/jobs?cat=17", "div.job-card-section a"),
    ("https://www.governmentjob.lk/category/it-jobs", "div.job-card a") # Guessing gov job selector
]:
    print(f"\n--- {url} ---")
    try:
        r = httpx.get(url, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        cards = soup.select(selector)
        if not cards:
            print("No cards found")
        for card in cards[:3]:
            img = card.find('img')
            if img:
                print("Image:", img.get('src'))
            else:
                print("No image")
    except Exception as e:
        print(e)

