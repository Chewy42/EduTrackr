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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_headers() -> Dict[str, str]:
    return {
        "accept": "text/plain, */*; q=0.01",
        "referer": "https://www.coursicle.com/chapman/",
        "user-agent": random.choice(USER_AGENTS),
        "x-requested-with": "XMLHttpRequest",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
    }

# Retry settings
MAX_RETRIES = 3
BASE_BACKOFF = 10  # seconds

# Timing settings (seconds)
DELAY_BETWEEN_PAGES_MIN = 1.5
DELAY_BETWEEN_PAGES_MAX = 3.0
DELAY_BETWEEN_LETTERS_MIN = 3.0
DELAY_BETWEEN_LETTERS_MAX = 6.0


# ============================================================================
# SCRAPER FUNCTIONS
# ============================================================================

def fetch_page_with_retry(offset: int, query: str = "") -> List[Dict[str, Any]]:
    """Fetch a single page of results with exponential backoff retry."""
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

    for attempt in range(MAX_RETRIES):
        try:
            # Add jitter to request timing
            if attempt > 0:
                backoff = BASE_BACKOFF * (2 ** attempt) + random.uniform(0, 10)
                print(f"    Rate limited. Waiting {backoff:.1f}s before retry {attempt + 1}/{MAX_RETRIES}...")
                time.sleep(backoff)
            
            response = requests.get(
                BASE_URL, 
                params=params, 
                headers=get_headers(), 
                timeout=30
            )
            
            if response.status_code == 429:
                # Rate limited - will retry with backoff
                if attempt < MAX_RETRIES - 1:
                    continue
                else:
                    print(f"    Max retries exceeded. Skipping.")
                    return []
            
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
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and attempt < MAX_RETRIES - 1:
                continue
            raise
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                print(f"    Request error: {e}. Retrying...")
                continue
            raise
    
    return []


def scrape_letter_pages(letter: str) -> Generator[List[Dict[str, Any]], None, None]:
    """Yield pages of results for a single letter query."""
    offset = 0
    consecutive_empty = 0
    
    while offset < 100:
        try:
            page = fetch_page_with_retry(offset, letter)
        except Exception as e:
            print(f"  Error fetching page {offset} for letter {letter}: {e}")
            # Wait before continuing
            time.sleep(random.uniform(5.0, 10.0))
            break
            
        if not page:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
        else:
            consecutive_empty = 0
            yield page
            
        offset += 1
        # Delay between pages
        time.sleep(random.uniform(DELAY_BETWEEN_PAGES_MIN, DELAY_BETWEEN_PAGES_MAX))


def scrape_all() -> None:
    """Scrape all classes by querying each letter a-z, saving incrementally."""
    filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scraper_output.csv")
    seen_ids: set = set()
    existing_fieldnames: List[str] = []
    file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0

    # Load existing IDs if file exists to avoid duplicates
    if file_exists:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                existing_fieldnames = list(reader.fieldnames) if reader.fieldnames else []
                for row in reader:
                    if "class" in row and row["class"]:
                        seen_ids.add(row["class"])
            print(f"Resuming. Loaded {len(seen_ids)} existing classes from {filename}")
        except Exception as e:
            print(f"Error reading existing file: {e}")
            file_exists = False

    print(f"Scraping Chapman {SEMESTER} classes...")

    for i, letter in enumerate(string.ascii_lowercase):
        if i > 0:
            # Delay between letters
            delay = random.uniform(DELAY_BETWEEN_LETTERS_MIN, DELAY_BETWEEN_LETTERS_MAX)
            print(f"Waiting {delay:.1f}s before next letter...")
            time.sleep(delay)

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
                # Determine fieldnames - merge existing with new
                new_keys = set().union(*(d.keys() for d in new_rows))
                if existing_fieldnames:
                    # Add any new keys not in existing fieldnames
                    all_fieldnames = existing_fieldnames + sorted(new_keys - set(existing_fieldnames))
                else:
                    all_fieldnames = sorted(new_keys)
                
                # Write to file
                write_mode = "a" if file_exists else "w"
                with open(filename, write_mode, newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=all_fieldnames, extrasaction='ignore')
                    if not file_exists:
                        writer.writeheader()
                        file_exists = True
                        existing_fieldnames = all_fieldnames
                    writer.writerows(new_rows)
                
                letter_new_count += len(new_rows)
                print(f"  Saved {len(new_rows)} new classes (Total unique: {len(seen_ids)})")
        
        print(f"Finished letter '{letter}'. Found {letter_new_count} new classes.")


def main() -> None:
    scrape_all()
    print(f"\nScraping complete. Data saved to scraper_output.csv")


if __name__ == "__main__":
    main()
