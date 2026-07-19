from bs4 import BeautifulSoup

with open("topjobs_response.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Row 8 is the header row, Row 9+ are job rows
# Let's look at rows 9-12 in detail
rows = soup.select("tr")
print(f"Total rows: {len(rows)}")

# Print row 9 - first job listing
for i in range(9, min(13, len(rows))):
    row = rows[i]
    tds = row.select("td")
    print(f"\n=== Row {i} has {len(tds)} tds ===")
    for j, td in enumerate(tds):
        text = td.get_text(" ", strip=True)
        print(f"  TD[{j}]: {text[:200]}")
        # Check for links
        links = td.select("a")
        for lnk in links:
            print(f"    LINK: href={lnk.get('href')}, text={lnk.get_text(strip=True)}")
