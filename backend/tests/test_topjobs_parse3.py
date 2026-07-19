from bs4 import BeautifulSoup

with open("topjobs_response.html", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")
rows = soup.select("tr")

# Look at the TD[2] more carefully to find job title vs company name
row = rows[9]
tds = row.select("td")
td2 = tds[2]
print("=== TD[2] Full HTML ===")
print(td2)
print()

# Check for links and spans
print("=== Spans ===")
for span in td2.select("span"):
    print(f"  id={span.get('id')}, text={span.get_text(strip=True)}")

print("\n=== Links ===")
for a in td2.select("a"):
    print(f"  href={a.get('href')}, text={a.get_text(strip=True)[:100]}")
    
# Also look at row onclick attribute for any useful identifiers
print("\n=== Row onclick ===")
for row in rows[9:13]:
    print(row.get("onclick"))
    
# Look at the img in the row
print("\n=== Images in first job row ===")
for img in rows[9].select("img"):
    print(img)
