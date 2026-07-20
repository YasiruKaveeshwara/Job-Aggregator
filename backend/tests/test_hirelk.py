from app.scrapers.hirelk import HirelkScraper

scraper = HirelkScraper()
jobs = scraper.fetch()
print(f"Total jobs collected: {len(jobs)}")
for j in jobs[:5]:
    print(f"  {j.job_title} | {j.company_name} | {j.location_raw}")
    print(f"  URL: {j.source_url}")
    print(f"  Logo: {j.image_url}")
