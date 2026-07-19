from bs4 import BeautifulSoup

with open("topjobs_response.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")

# Print first few rows with content to understand structure
rows = soup.select("tr")
print(f"Total rows: {len(rows)}")
for i, row in enumerate(rows[:10]):
    text = row.get_text(" ", strip=True)
    if text:
        print(f"\n--- Row {i} ---")
        print(text[:300])
        print("HTML:", str(row)[:400])
