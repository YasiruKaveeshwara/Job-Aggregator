import asyncio
from app.scrapers.anyjobok import AnyjobokScraper

def test():
    scraper = AnyjobokScraper()
    jobs = scraper.fetch()
    print(f"Total jobs collected: {len(jobs)}")
    for j in jobs[:5]:
        print(j.job_title, j.company_name)

if __name__ == "__main__":
    test()
