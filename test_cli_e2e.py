"""
End-to-end CLI test script
==========================
Tests every CLI function via the cloud API (same backend the CLI uses).
"""
import sys
import time
import io
import json
import requests

API = "https://ocrapi.nsunexus.app"
PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  — {detail}")


# ═════════════════════════════════════════════════════════════════
# 1. BACKEND HEALTH
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 1. BACKEND HEALTH ━━━")
r = requests.get(f"{API}/health/live", timeout=10)
test("Live endpoint", r.status_code == 200 and r.json().get("status") == "live")

r = requests.get(f"{API}/health/ready", timeout=10)
test("Ready endpoint", r.status_code == 200)

r = requests.get(f"{API}/", timeout=10)
test("Root endpoint", r.status_code == 200 and r.json().get("status") == "running")

r = requests.get(f"{API}/health", timeout=10)
h = r.json()
test("DB connected", h.get("layers", {}).get("database", {}).get("status") == "connected")
test("OCR engines ready", h.get("layers", {}).get("ocr", {}).get("status") == "operational")
test("0 errors", h.get("metrics", {}).get("errors", -1) == 0)


# ═════════════════════════════════════════════════════════════════
# 2. AUTH CONFIG
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 2. AUTH CONFIG ━━━")
r = requests.get(f"{API}/auth/config", timeout=10)
d = r.json()
test("Auth config returns success", d.get("success") is True)
test("Auth available", d.get("auth_available") is True)
test("DB available", d.get("db_available") is True)
test("Supabase URL present", bool(d.get("config", {}).get("supabase_url")))
test("Google client ID present", bool(d.get("config", {}).get("google_client_id")))


# ═════════════════════════════════════════════════════════════════
# 3. DEVICE CODE FLOW (CRITICAL FIX VERIFICATION)
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 3. DEVICE CODE FLOW ━━━")
r = requests.post(f"{API}/auth/device/code", timeout=10)
d = r.json()
test("Device code creation", d.get("success") is True)
device_code = d.get("device_code")
test("Device code returned", bool(device_code))
test("User code returned", bool(d.get("user_code")))
test("Verification URL returned", bool(d.get("verification_url")))
test("Expires in 600s", d.get("expires_in") == 600)

# Poll before verification — should be pending
r = requests.post(f"{API}/auth/device/poll", json={"device_code": device_code}, timeout=10)
d = r.json()
test("Poll returns pending before verify", d.get("status") == "pending")

# Poll with invalid code — should fail gracefully
r = requests.post(f"{API}/auth/device/poll", json={"device_code": "INVALID1"}, timeout=10)
d = r.json()
test("Invalid device code handled", d.get("status") in ("expired", "error") or not d.get("success", True))


# ═════════════════════════════════════════════════════════════════
# 4. CSV UPLOAD (asyncio.to_thread FIX VERIFICATION)
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 4. CSV UPLOAD ━━━")
csv_data = """Course Code,Course Title,Credits,Grade,Semester
ENG101,English Composition,3,A,Fall 2020
MAT120,Basic Mathematics,3,A-,Fall 2020
CSE115,Programming Language I,3,A,Spring 2021
PHY107,Physics I,3,B+,Spring 2021
CSE173,Discrete Mathematics,3,A,Summer 2021
CSE215,Programming Language II,3,A-,Spring 2021
CSE231,Data Structures,3,B+,Fall 2021
CSE253,Numerical Methods,3,B,Fall 2021
"""

files = {"file": ("transcript.csv", io.BytesIO(csv_data.encode()), "text/csv")}
data = {"source": "cli"}
r = requests.post(f"{API}/upload", files=files, data=data, timeout=120)
resp = r.json()
test("Upload returns 200", r.status_code == 200)
test("Upload success", resp.get("success") is True)

upload_data = resp.get("data", {})
test("Data returned", bool(upload_data))
test("Level1 present", "level1" in upload_data, f"keys: {list(upload_data.keys())[:10]}")
test("Level2 present", "level2" in upload_data)
test("Courses returned", len(upload_data.get("courses", [])) > 0)

l1 = upload_data.get("level1", {})
l2 = upload_data.get("level2", {})
test("L1 earned_credits > 0", l1.get("earned_credits", 0) > 0)
test("L2 cgpa > 0", l2.get("cgpa", 0) > 0)
test("L2 standing present", bool(l2.get("standing")))

# Verify level1/level2 keys (not level_1/level_2)
test("Key is 'level1' not 'level_1'", "level1" in upload_data and "level_1" not in upload_data)
test("Key is 'level2' not 'level_2'", "level2" in upload_data and "level_2" not in upload_data)

# Curriculum info
cur = upload_data.get("curriculum", {})
test("Curriculum info present", bool(cur))
test("Curriculum version present", bool(cur.get("version")))


# ═════════════════════════════════════════════════════════════════
# 5. UPLOAD VALIDATION
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 5. UPLOAD VALIDATION ━━━")
# Invalid extension
files = {"file": ("test.exe", io.BytesIO(b"test"), "application/octet-stream")}
r = requests.post(f"{API}/upload", files=files, data={"source": "test"}, timeout=10)
test("Rejects invalid extension", r.status_code != 200 or not r.json().get("success"))

# Empty file
files = {"file": ("empty.csv", io.BytesIO(b""), "text/csv")}
r = requests.post(f"{API}/upload", files=files, data={"source": "test"}, timeout=10)
test("Rejects empty file", r.status_code != 200 or not r.json().get("success"))


# ═════════════════════════════════════════════════════════════════
# 6. UNAUTHENTICATED USER ENDPOINTS
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 6. UNAUTHENTICATED ENDPOINTS ━━━")
r = requests.get(f"{API}/auth/user", timeout=10)
test("Auth user without token fails", r.status_code != 200 or not r.json().get("success"))

r = requests.get(f"{API}/auth/me", timeout=10)
test("Auth me without token fails", r.status_code != 200 or not r.json().get("success"))

r = requests.get(f"{API}/history", timeout=10)
test("History without auth fails", r.status_code != 200 or not r.json().get("success"))


# ═════════════════════════════════════════════════════════════════
# 7. ANALYSIS ENDPOINT (level1 key fix verification)
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 7. ANALYSIS ENDPOINT ━━━")
# Without auth, should fail
r = requests.get(f"{API}/api/v1/analysis/latest", timeout=10)
test("Analysis latest requires auth", r.status_code != 200 or not r.json().get("success"))


# ═════════════════════════════════════════════════════════════════
# 8. EXPORT ENDPOINTS
# ═════════════════════════════════════════════════════════════════
print("\n━━━ 8. EXPORT ENDPOINTS ━━━")
# CSV export
csv_export = """Course Code,Course Title,Credits,Grade,Semester
CSE115,Programming Language I,3,A,Spring 2021"""
files = {"file": ("export_test.csv", io.BytesIO(csv_export.encode()), "text/csv")}
r = requests.post(f"{API}/upload", files=files, data={"source": "test"}, timeout=60)
resp = r.json()
if resp.get("success") and resp.get("data", {}).get("scan_id"):
    scan_id = resp["data"]["scan_id"]
    # Try CSV export
    r = requests.get(f"{API}/export/{scan_id}/csv", timeout=10)
    test("CSV export endpoint responds", r.status_code == 200)
    # Try JSON export
    r = requests.get(f"{API}/export/{scan_id}/json", timeout=10)
    test("JSON export endpoint responds", r.status_code == 200)
else:
    test("CSV export — skipped (no scan_id)", False, "upload didn't return scan_id")
    test("JSON export — skipped (no scan_id)", False, "upload didn't return scan_id")


# ═════════════════════════════════════════════════════════════════
# SUMMARY
# ═════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
total = PASS + FAIL
print(f"  RESULTS: {PASS}/{total} passed, {FAIL}/{total} failed")
if FAIL == 0:
    print("  🎉 ALL TESTS PASSED!")
else:
    print(f"  ⚠️  {FAIL} test(s) failed — see details above")
print("=" * 60 + "\n")
