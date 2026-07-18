import httpx

# Check CORS: simulate a cross-origin preflight from localhost:3000
headers = {
    "Origin": "http://localhost:3000",
    "Access-Control-Request-Method": "GET",
    "Access-Control-Request-Headers": "Content-Type",
}
r = httpx.options("http://127.0.0.1:8000/api/jobs", headers=headers)
print("CORS preflight status:", r.status_code)
print("Allow-Origin:", r.headers.get("access-control-allow-origin", "MISSING"))
print("Allow-Methods:", r.headers.get("access-control-allow-methods", "MISSING"))

# Check jobs API
r2 = httpx.get("http://127.0.0.1:8000/api/jobs", headers={"Origin": "http://localhost:3000"})
jobs = r2.json()
print(f"Jobs endpoint: {r2.status_code}, {len(jobs)} jobs")
if jobs:
    j = jobs[0]
    print(f"  title: {j['job_title']}")
    print(f"  company: {j['company_name']}")
    print(f"  state: {j['application_state']}")
    print(f"  role: {j['role_match']}")
    print(f"  sources: {[s['platform'] for s in j['sources']]}")

# Test PATCH state update
if jobs:
    job_id = jobs[0]["id"]
    r3 = httpx.patch(
        f"http://127.0.0.1:8000/api/jobs/{job_id}",
        json={"application_state": "REVIEWING"},
        headers={"Origin": "http://localhost:3000"},
    )
    print(f"PATCH state: {r3.status_code}")
    print(f"  new state: {r3.json()['application_state']}")
    # Revert
    httpx.patch(
        f"http://127.0.0.1:8000/api/jobs/{job_id}",
        json={"application_state": "DISCOVERED"},
    )
    print("  reverted OK")

# Check frontend responds
r4 = httpx.get("http://localhost:3000")
print(f"\nFrontend status: {r4.status_code}")
print(f"  Content-Type: {r4.headers.get('content-type', '?')}")
has_nav = "Job Aggregator" in r4.text
print(f"  Contains app title: {has_nav}")
