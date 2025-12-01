#!/usr/bin/env python3
"""
Standalone Chapman Coursicle scraper - combines scraper and decoder in one file.
Run: python chapman_coursicle_standalone.py

Output: chapman_coursicle_spring2026.csv in the current directory.
"""

import base64
import csv
import json
import string
import time
from typing import Any, Dict, List

import requests

# ============================================================================
# DECODER (from coursicle_decoder.py)
# ============================================================================

def _shift_char(c: str) -> str:
    code = ord(c)
    if code == 0x2f:  # '/'
        return 'f'
    if code == 0x2b:  # '+'
        return 'e'
    if code >= 0x6b:  # >= 'k'
        return chr(code - 0x2a)
    if code >= 0x61:  # >= 'a'
        return chr(code + 0x10)
    if code >= 0x57:  # >= 'W'
        return chr(code + 0x0a)
    if code == 0x4b:  # 'K'
        return '+'
    if code >= 0x4c:  # >= 'L'
        return chr(code - 0x1d)
    if code >= 0x41:  # >= 'A'
        return chr(code + 0x10)
    return chr(code + 0x37)


def _transform_string(s: str) -> str:
    return "".join(_shift_char(c) for c in s)


def decode_coursicle_response(encrypted: str) -> str:
    s = encrypted
    replacements = {
        '-': '2', '?': '5', '(': '7', ')': 'c', ',': 'f', '.': 'h',
        '!': 'l', '&': 'o', '[': 'q', '@': 'u', '#': 'B', '*': 'G',
        '$': 'I', ']': 'K', '%': 'O', '<': 'R', '>': 'S', '^': 'V'
    }
    for old, new in replacements.items():
        s = s.replace(old, new)
    for _ in range(3):
        s = _transform_string(s)
    missing_padding = len(s) % 4
    if missing_padding:
        s += '=' * (4 - missing_padding)
    decoded_bytes = base64.b64decode(s)
    return decoded_bytes.decode('utf-8')


# ============================================================================
# SCRAPER CONFIG
# ============================================================================

BASE_URL = "https://www.coursicle.com/shared/getClasses.php"
SCHOOL = "chapman"
SEMESTER = "spring2026"
UUID = "c8e4ae55-4b07-4fcd-9a5a-ed17fd22b885"
COUNT = 25  # API max per page

HEADERS = {
    "accept": "text/plain, */*; q=0.01",
    "referer": "https://www.coursicle.com/chapman/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
    "x-requested-with": "XMLHttpRequest",
}


# ============================================================================
# SCRAPER FUNCTIONS
# ============================================================================

def fetch_page(offset: int, query: str = "") -> List[Dict[str, Any]]:
    """Fetch a single page of results."""
    params = {
        "school": SCHOOL,
        "semester": SEMESTER,
        "uuid": UUID,
        "client": "web",
        "offset": offset,
        "count": COUNT,
        "days": "",
    }
    if query:
        params["query"] = query

    response = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()

    try:
        data = response.json()
    except ValueError:
        decrypted = decode_coursicle_response(response.text)
        start = decrypted.find("{")
        end = decrypted.rfind("}") + 1
        data = json.loads(decrypted[start:end])

    classes = data.get("classes", [])
    return [row for row in classes if isinstance(row, dict)]


def scrape_letter(letter: str) -> List[Dict[str, Any]]:
    """Scrape all pages for a single letter query."""
    rows: List[Dict[str, Any]] = []
    offset = 0

    while offset < 100:
        page = fetch_page(offset, letter)
        if not page:
            break
        rows.extend(page)
        offset += 1
        time.sleep(0.5)  # Small delay between pages

    return rows


def scrape_all() -> List[Dict[str, Any]]:
    """Scrape all classes by querying each letter a-z."""
    seen: Dict[str, Dict[str, Any]] = {}

    print(f"Scraping Chapman {SEMESTER} classes...")

    for i, letter in enumerate(string.ascii_lowercase):
        if i > 0:
            time.sleep(1.0)  # Delay between letters

        rows = scrape_letter(letter)
        new_count = 0
        for row in rows:
            class_id = row.get("class", "")
            if class_id and class_id not in seen:
                seen[class_id] = row
                new_count += 1

        print(f"  '{letter}': {len(rows)} results, {new_count} new (total: {len(seen)})")

    return sorted(seen.values(), key=lambda r: r.get("class", ""))


def write_csv(rows: List[Dict[str, Any]], filename: str) -> None:
    """Write rows to CSV file."""
    if not rows:
        print("No data to write!")
        return

    # Collect all field names
    fieldnames = sorted(set(k for row in rows for k in row.keys()))

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rows = scrape_all()
    filename = f"chapman_coursicle_{SEMESTER}.csv"
    write_csv(rows, filename)
    print(f"\nWrote {len(rows)} classes to {filename}")


if __name__ == "__main__":
    main()
