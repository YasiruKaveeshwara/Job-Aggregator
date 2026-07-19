from app.scrapers.topjobs import TopjobsScraper

scraper = TopjobsScraper()
jobs = scraper.fetch()
print(f"Total jobs collected: {len(jobs)}")
for j in jobs[:5]:
    print(f"  {j.job_title} | {j.company_name} | {j.location_raw} | {j.posted_date_raw}")
    print(f"  URL: {j.source_url}")
