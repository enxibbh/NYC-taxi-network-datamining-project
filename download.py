"""
Download NYC TLC Yellow + Green taxi Parquet files for Jan 2024 - Dec 2025.

Usage:
    pip install requests tqdm pyarrow pandas
    python download.py

Files are saved to ./data/ (created if missing). Already-downloaded files are
skipped. Run again to resume after an interrupted download.
"""

from pathlib import Path
import sys
import requests
from tqdm import tqdm

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
TAXI_TYPES = ["yellow", "green"]
YEARS_MONTHS = [(y, m) for y in (2024, 2025) for m in range(1, 13)]
OUT_DIR = Path("data")
CHUNK = 1 << 16  # 64 KB


def download_one(url: str, dest: Path) -> tuple[bool, str]:
    """Download one file with a progress bar. Returns (ok, message)."""
    if dest.exists() and dest.stat().st_size > 0:
        return True, f"skip (exists, {dest.stat().st_size / 1e6:.1f} MB)"

    try:
        with requests.get(url, stream=True, timeout=30) as r:
            if r.status_code == 404:
                return False, "404 not found (file not published yet)"
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            tmp = dest.with_suffix(dest.suffix + ".part")
            with open(tmp, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True,
                desc=dest.name, leave=False,
            ) as bar:
                for block in r.iter_content(CHUNK):
                    f.write(block)
                    bar.update(len(block))
            tmp.rename(dest)
        return True, f"ok ({dest.stat().st_size / 1e6:.1f} MB)"
    except Exception as e:
        return False, f"error: {e}"


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    print(f"Saving to: {OUT_DIR.resolve()}")
    print(f"Planned: {len(TAXI_TYPES) * len(YEARS_MONTHS)} files\n")

    results: list[tuple[str, bool, str]] = []
    for taxi in TAXI_TYPES:
        for year, month in YEARS_MONTHS:
            fname = f"{taxi}_tripdata_{year}-{month:02d}.parquet"
            url = f"{BASE_URL}/{fname}"
            ok, msg = download_one(url, OUT_DIR / fname)
            print(f"{'OK ' if ok else 'XX '}{fname:40s}  {msg}")
            results.append((fname, ok, msg))

    ok_count = sum(1 for _, ok, _ in results if ok)
    print(f"\nDone: {ok_count}/{len(results)} files available.")
    failed = [name for name, ok, _ in results if not ok]
    if failed:
        print("Failed:")
        for name in failed:
            print(f"  - {name}")
    return 0 if ok_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
