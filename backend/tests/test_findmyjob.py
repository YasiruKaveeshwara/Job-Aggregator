from app.scrapers.findmyjob import FindmyjobScraper

scraper = FindmyjobScraper()
jobs = scraper.fetch()
print(f"Total jobs collected: {len(jobs)}")
for j in jobs[:5]:
    print(f"  {j.job_title} | {j.company_name or '(no company)'} | {j.posted_date_raw}")
    print(f"  URL: {j.source_url}")
