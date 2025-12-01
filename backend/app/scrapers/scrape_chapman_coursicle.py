#!/usr/bin/env python3
"""
Standalone Chapman Coursicle scraper - combines scraper and decoder in one file.
Run: python chapman_coursicle_standalone.py

Output: chapman_coursicle_spring2026.csv in the current directory.
"""

import base64
import csv
import json
import os
import random
import string
import time
from typing import Any, Dict, List, Generator

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


def scrape_letter_pages(letter: str) -> Generator[List[Dict[str, Any]], None, None]:
    """Yield pages of results for a single letter query."""
    offset = 0
    while offset < 100:
        try:
            page = fetch_page(offset, letter)
        except Exception as e:
            print(f"Error fetching page {offset} for letter {letter}: {e}")
            break
            
        if not page:
            break
        yield page
        offset += 1
        # Random delay between pages to avoid rate limiting
        time.sleep(random.uniform(1.0, 3.0))


def scrape_all() -> None:
    """Scrape all classes by querying each letter a-z, saving incrementally."""
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_output.csv")
    seen_ids = set()
    fieldnames = None

    # Load existing IDs if file exists to avoid duplicates
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                for row in reader:
                    if "class" in row:
                        seen_ids.add(row["class"])
            print(f"Resuming. Loaded {len(seen_ids)} existing classes from {filename}")
        except Exception as e:
            print(f"Error reading existing file: {e}")

    print(f"Scraping Chapman {SEMESTER} classes...")

    # Open file in append mode
    with open(filename, "a", newline="", encoding="utf-8") as f:
        writer = None
        if fieldnames:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        
        for i, letter in enumerate(string.ascii_lowercase):
            if i > 0:
                # Random delay between letters
                time.sleep(random.uniform(3.0, 6.0))

            print(f"Scraping letter '{letter}'...")
            letter_new_count = 0
            
            for page_rows in scrape_letter_pages(letter):
                new_rows = []
                for row in page_rows:
                    class_id = row.get("class", "")
                    # Only add if we haven't seen this class ID
                    if class_id and class_id not in seen_ids:
                        seen_ids.add(class_id)
                        new_rows.append(row)
                
                if new_rows:
                    # Initialize writer if this is the first write
                    if writer is None:
                        # Determine fieldnames from the first batch of data
                        all_keys = set().union(*(d.keys() for d in new_rows))
                        fieldnames = sorted(all_keys)
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        # If file was empty, write header
                        if f.tell() == 0:
                            writer.writeheader()
                    
                    writer.writerows(new_rows)
                    f.flush() # Ensure data is written to disk
                    letter_new_count += len(new_rows)
                    print(f"  Saved {len(new_rows)} new classes (Total unique: {len(seen_ids)})")
            
            print(f"Finished letter '{letter}'. Found {letter_new_count} new classes.")


def main() -> None:
    scrape_all()
    print(f"\nScraping complete. Data saved to scraper_output.csv")


if __name__ == "__main__":
    main()
