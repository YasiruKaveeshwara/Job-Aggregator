import httpx

url = "https://anyjobok.com/?q=software+engineer"
r = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0'})
with open('anyjobok_debug.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
