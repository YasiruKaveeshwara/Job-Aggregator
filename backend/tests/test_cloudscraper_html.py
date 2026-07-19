import cloudscraper
scraper = cloudscraper.create_scraper()
url = "https://anyjobok.com/?q=software+engineer"
r = scraper.get(url)
with open("anyjobok_cloudscraper.html", "w", encoding="utf-8") as f:
    f.write(r.text)
