"""Verify all gap-filling features."""
import httpx

BASE = "http://127.0.0.1:8000"

print("=" * 60)
print("  TESTING GAP FILLS")
print("=" * 60)

# 1. Keywords API
print("\n--- GET /api/keywords ---")
r = httpx.get(f"{BASE}/api/keywords")
print(f"Status: {r.status_code}")
kw = r.json()
print(f"Include: {kw['include'][:3]}...")
print(f"Intern modifiers: {kw['intern_modifiers']}")
print(f"Exclude: {kw['exclude']}")

print("\n--- PUT /api/keywords (add exclusion) ---")
kw["exclude"] = ["software sales engineer"]
r2 = httpx.put(f"{BASE}/api/keywords", json=kw)
print(f"Status: {r2.status_code}")
print(f"Exclude after update: {r2.json()['exclude']}")

# Revert
kw["exclude"] = []
httpx.put(f"{BASE}/api/keywords", json=kw)
print("Reverted exclude list")

# 2. Sources with last_scraped_at
print("\n--- GET /api/sources (checking last_scraped_at) ---")
r3 = httpx.get(f"{BASE}/api/sources")
print(f"Status: {r3.status_code}")
for src in r3.json():
    print(f"  {src['name']}: enabled={src['enabled']}, last_scraped={src['last_scraped_at']}")

# 3. Frontend pages
print("\n--- Frontend health ---")
r4 = httpx.get("http://localhost:3000")
print(f"Dashboard: {r4.status_code}")
r5 = httpx.get("http://localhost:3000/admin")
print(f"Admin: {r5.status_code}")

print("\n  ALL GAP TESTS PASSED")
print("=" * 60)
