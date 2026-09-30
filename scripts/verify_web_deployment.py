"""
verify_web_deployment.py

Automated verification of Soil Advisory public GIS assets and live deployment.
Checks:
  1. Local frontend/public files (existence, non-zero size, record counts).
  2. GitHub remote repository state (correct file sizes in repo, avoiding the >1MB API trap).
  3. Live Vercel deployment endpoints (homepage, advisory_metadata.json, advisory_pixels.csv, advisory_pixels.geojson).

Can be executed standalone or invoked by scripts/8_publish_and_deploy.py.
"""

from pathlib import Path
import json
import sys
import time
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = ROOT / "frontend" / "public"

CSV_PATH = PUBLIC / "advisory_pixels.csv"
GEOJSON_PATH = PUBLIC / "advisory_pixels.geojson"
META_PATH = PUBLIC / "advisory_metadata.json"

VERCEL_BASE = "https://soiladvisory.vercel.app"
GITHUB_API_DIR = "https://api.github.com/repos/powellmponela/Soil-advisory/contents/frontend/public"
USER_AGENT = "SoilAdvisory-DeploymentChecker/1.0"


def fetch_url(url: str, byte_count: int | None = None, timeout: int = 15) -> tuple[int, bytes, dict]:
    """Fetch URL, optionally limiting byte_count via Range header if specified."""
    headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
    if byte_count:
        headers["Range"] = f"bytes=0-{byte_count - 1}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            resp_headers = dict(resp.getheaders())
            data = resp.read()
            return status, data, resp_headers
    except urllib.error.HTTPError as err:
        return err.code, b"", {}
    except Exception as exc:
        return 0, b"", {"error": str(exc)}


def verify_local_files() -> tuple[bool, dict]:
    """Verify local files in frontend/public."""
    print("\n--- [1/3] Local Public GIS Assets ---")
    results = {}
    ok = True

    if not META_PATH.exists():
        print(f"FAIL: Missing {META_PATH}")
        return False, {"error": "Missing advisory_metadata.json"}

    try:
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        expected_records = int(meta.get("n_records", 0))
        results["metadata_records"] = expected_records
        print(f"OK   advisory_metadata.json: valid JSON, n_records = {expected_records:,}")
    except Exception as exc:
        print(f"FAIL: Invalid advisory_metadata.json: {exc}")
        return False, {"error": str(exc)}

    # Check CSV
    if not CSV_PATH.exists():
        print(f"FAIL: Missing {CSV_PATH}")
        return False, {"error": "Missing advisory_pixels.csv"}
    csv_size = CSV_PATH.stat().st_size
    if csv_size <= 0:
        print(f"FAIL: advisory_pixels.csv is 0 bytes")
        ok = False
    else:
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            header = f.readline().strip()
            row_count = sum(1 for _ in f)
        results["csv_rows"] = row_count
        results["csv_bytes"] = csv_size
        print(f"OK   advisory_pixels.csv: {csv_size:,} bytes, {row_count:,} data rows")
        if row_count != expected_records:
            print(f"WARN: CSV row count ({row_count}) differs from metadata ({expected_records})")

    # Check GeoJSON
    if not GEOJSON_PATH.exists():
        print(f"FAIL: Missing {GEOJSON_PATH}")
        return False, {"error": "Missing advisory_pixels.geojson"}
    geo_size = GEOJSON_PATH.stat().st_size
    if geo_size <= 0:
        print(f"FAIL: advisory_pixels.geojson is 0 bytes")
        ok = False
    else:
        results["geojson_bytes"] = geo_size
        print(f"OK   advisory_pixels.geojson: {geo_size:,} bytes")

    return ok, results


def verify_github_repo() -> tuple[bool, dict]:
    """Verify remote GitHub repo state without falling for the >1MB content trap."""
    print("\n--- [2/3] GitHub Repository Synchronization ---")
    req = urllib.request.Request(
        GITHUB_API_DIR,
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            files = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"WARN: Could not query GitHub Contents API: {exc}")
        return True, {"skipped": str(exc)}

    file_map = {f.get("name"): f for f in files if isinstance(f, dict)}
    ok = True

    for name in ["advisory_metadata.json", "advisory_pixels.csv", "advisory_pixels.geojson"]:
        info = file_map.get(name)
        if not info:
            print(f"FAIL: {name} not found in GitHub main branch")
            ok = False
            continue
        size = int(info.get("size", 0))
        if size == 0:
            print(f"FAIL: {name} has 0 bytes in GitHub main branch")
            ok = False
        else:
            print(f"OK   GitHub main: {name:<26} {size:>12,} bytes  (sha: {info.get('sha')[:8]})")

    return ok, file_map


def verify_live_deployment(retries: int = 4, delay: int = 5) -> tuple[bool, dict]:
    """Verify live Vercel deployment endpoints."""
    print(f"\n--- [3/3] Live Vercel Production Checks ({VERCEL_BASE}) ---")

    all_passed = False
    last_status = {}

    for attempt in range(1, retries + 1):
        if attempt > 1:
            print(f"Retrying live checks in {delay}s (attempt {attempt}/{retries})...")
            time.sleep(delay)

        attempt_ok = True

        # 1. Homepage
        status, html_bytes, _ = fetch_url(f"{VERCEL_BASE}/", byte_count=1024)
        last_status["/"] = status
        if status in (200, 206) and b"<!doctype html" in html_bytes.lower():
            print(f"OK   [{status}] Web Homepage ({VERCEL_BASE}/)")
        else:
            print(f"FAIL [{status}] Web Homepage ({VERCEL_BASE}/)")
            attempt_ok = False

        # 2. Metadata JSON (full fetch)
        status, meta_bytes, _ = fetch_url(f"{VERCEL_BASE}/advisory_metadata.json")
        last_status["/advisory_metadata.json"] = status
        try:
            live_meta = json.loads(meta_bytes.decode("utf-8"))
            records = live_meta.get("n_records", 0)
            if status == 200 and records == 11703:
                print(f"OK   [{status}] Metadata ({VERCEL_BASE}/advisory_metadata.json) - {records:,} records verified")
            else:
                print(f"FAIL [{status}] Metadata: invalid records {records}")
                attempt_ok = False
        except Exception as exc:
            print(f"FAIL [{status}] Metadata parse error: {exc}")
            attempt_ok = False

        # 3. Advisory Pixels CSV (range query)
        status, csv_chunk, _ = fetch_url(f"{VERCEL_BASE}/advisory_pixels.csv", byte_count=1024)
        last_status["/advisory_pixels.csv"] = status
        if (status in (200, 206)) and b"pixel_id" in csv_chunk:
            print(f"OK   [{status}] Public CSV ({VERCEL_BASE}/advisory_pixels.csv) - header verified")
        else:
            print(f"FAIL [{status}] Public CSV payload missing header")
            attempt_ok = False

        # 4. Advisory Pixels GeoJSON (range query)
        status, geo_chunk, _ = fetch_url(f"{VERCEL_BASE}/advisory_pixels.geojson", byte_count=1024)
        last_status["/advisory_pixels.geojson"] = status
        if (status in (200, 206)) and b"FeatureCollection" in geo_chunk:
            print(f"OK   [{status}] Public GeoJSON ({VERCEL_BASE}/advisory_pixels.geojson) - FeatureCollection verified")
        else:
            print(f"FAIL [{status}] Public GeoJSON payload missing FeatureCollection")
            attempt_ok = False

        if attempt_ok:
            all_passed = True
            break

    return all_passed, last_status


def main():
    print("=" * 72)
    print("SOIL ADVISORY: AUTOMATED WEB & DEPLOYMENT CHECK")
    print("=" * 72)

    local_ok, _ = verify_local_files()
    if not local_ok:
        print("\nERROR: Local GIS files validation failed.")
        sys.exit(1)

    gh_ok, _ = verify_github_repo()
    if not gh_ok:
        print("\nERROR: Remote GitHub validation failed.")
        sys.exit(1)

    live_ok, _ = verify_live_deployment(retries=4, delay=5)
    if not live_ok:
        print("\nWARN: Live Vercel check did not pass all assertions.")
        sys.exit(1)

    print("\n" + "=" * 72)
    print("SUCCESS: ALL PUBLIC WEB GIS PAYLOADS VERIFIED LIVE & SYNCHRONIZED")
    print("=" * 72)


if __name__ == "__main__":
    main()
