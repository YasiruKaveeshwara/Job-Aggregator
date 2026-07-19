import httpx
from bs4 import BeautifulSoup

url = "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp"
payload = {
    "txtJSCode": "",
    "txtKeyWord": "software",
    "btnSearch": "Search",
    "FA": "",
    "pageNo": "",
    "CookieAppend": "false",
    "SID": "",
    "hdnPreJC": "",
    "hdnPreAC": "",
    "hdnPreEC": "",
    "hdnNextJC": "",
    "hdnNextAC": "",
    "hdnNextEC": "",
    "selectdRow": "",
    "hdnNavigateLink": "../applicant/vacancybyfunctionalarea.jsp?FA=&jst=OPEN&sQut=&txtKeyWord=software&chkGovt=&chkParttime=&chkWalkin=&chkNGO=&",
    "hdnBlockSize": "1000",
    "hdnTotalJobs": "44",
    "hdnCurrentPage": "1",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded",
    "Referer": "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp",
    "Origin": "https://www.topjobs.lk",
}

r = httpx.post(url, data=payload, headers=headers, follow_redirects=True)
print("Status:", r.status_code)
with open("topjobs_response.html", "w", encoding="utf-8") as f:
    f.write(r.text)
print("Saved to topjobs_response.html")

# Quick parse
soup = BeautifulSoup(r.text, "html.parser")
# Look for job listings
rows = soup.select("tr")
print(f"Found {len(rows)} rows")
# Print first 300 chars of body
print(r.text[:500])
