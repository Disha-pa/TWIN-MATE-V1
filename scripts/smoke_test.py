"""Quick smoke test against running Twin-Mate server."""
import re
import sys
import requests

BASE = "http://127.0.0.1:5000"
EMAIL = "smoke_fresh@example.com"
PASSWORD = "secret12"

session = requests.Session()
results = []


def check(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append((name, ok, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def get_csrf(html):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return m.group(1) if m else None


print("\n=== Twin-Mate Smoke Test ===\n")

r = session.get(f"{BASE}/")
check("GET / landing", r.status_code == 200 and b"TWIN MATE" in r.content)

r = session.get(f"{BASE}/signup")
check("GET /signup", r.status_code == 200 and b"Create Account" in r.content)

csrf = get_csrf(r.text)
r = session.post(f"{BASE}/signup", data={
    "csrf_token": csrf,
    "email": EMAIL,
    "password": PASSWORD,
}, allow_redirects=True)
check("POST /signup", r.status_code == 200 and b"What should we call you" in r.content)

if b"What should we call you" in r.content:
    csrf = get_csrf(r.text)
    r = session.post(f"{BASE}/onboarding", data={
        "csrf_token": csrf,
        "step": "1",
        "name": "Smoke Tester",
    }, allow_redirects=True)
    check("POST /onboarding step 1", r.status_code == 200 and b"Step 2" in r.content)

passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
print(f"\n=== Results: {passed}/{total} passed ===\n")
sys.exit(0 if passed == total else 1)
