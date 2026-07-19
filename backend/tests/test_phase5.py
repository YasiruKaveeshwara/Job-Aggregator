import httpx
import time
import json
import sys

def run_tests():
    try:
        c = httpx.Client(base_url='http://127.0.0.1:8000')
        
        # Test sources endpoint
        print("Testing GET /api/sources...")
        r = c.get('/api/sources')
        r.raise_for_status()
        sources = r.json()
        print(f"Sources: {[s['name'] for s in sources]}")
        
        # Test scrape run
        print("\nTesting POST /api/scrape/run...")
        r = c.post('/api/scrape/run', json={'sites': ['itpro.lk']})
        r.raise_for_status()
        start_res = r.json()
        print(f"Started run: {start_res}")
        run_id = start_res['run_id']
        
        # Poll status
        print(f"\nPolling status for run_id {run_id}...")
        for _ in range(15):
            r = c.get(f'/api/scrape/status/{run_id}')
            r.raise_for_status()
            status = r.json()
            print(f"Status: {status['status']}")
            if status['status'] in ['COMPLETED', 'FAILED']:
                print(f"Final site_results:\n{json.dumps(status['site_results'], indent=2)}")
                break
            time.sleep(2)
            
        # Test jobs endpoint
        print("\nTesting GET /api/jobs...")
        r = c.get('/api/jobs')
        r.raise_for_status()
        jobs = r.json()
        print(f"Total jobs: {len(jobs)}")
        if jobs:
            print("First 5 jobs:")
            for j in jobs[:5]:
                print(f"  - {j['job_title']} @ {j['company_name']} [{j['role_match']}]")
                
        print("\nAll Phase 5 API tests completed successfully!")
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
