import requests
from bs4 import BeautifulSoup
import json
import re
import os
import time
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Force utf-8 encoding for stdout/stderr to avoid charmap errors on Windows
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_URL = "https://catalog.chapman.edu"
CATALOG_LIST_URL = f"{BASE_URL}/misc/catalog_list.php"

def get_catalogs():
    print(f"Fetching catalog list from {CATALOG_LIST_URL}...")
    try:
        response = requests.get(CATALOG_LIST_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        catalogs = []
        links = soup.find_all('a', href=True)
        
        for link in links:
            text = link.get_text().strip()
            href = link['href']
            
            # Match "YYYY-YYYY Undergraduate Catalog"
            match = re.search(r'(\d{4}-\d{4}).*Undergraduate Catalog', text, re.IGNORECASE)
            if match:
                year = match.group(1)
                if not href.startswith('http'):
                    if href.startswith('/'):
                        full_url = BASE_URL + href
                    else:
                        if 'index.php' in href or 'content.php' in href:
                             full_url = f"{BASE_URL}/{href}"
                        else:
                             full_url = f"{BASE_URL}/misc/{href}"
                else:
                    full_url = href
                
                catoid_match = re.search(r'catoid=(\d+)', full_url)
                if catoid_match:
                    catoid = catoid_match.group(1)
                    catalogs.append({
                        'year': year,
                        'url': full_url,
                        'catoid': catoid,
                        'text': text
                    })
        
        unique_catalogs = {}
        for c in catalogs:
            unique_catalogs[c['year']] = c
        
        return sorted(unique_catalogs.values(), key=lambda x: x['year'], reverse=True)
    except Exception as e:
        print(f"Error fetching catalog list: {e}")
        return []

def get_programs_page_url(catalog_url, catoid):
    print(f"Fetching catalog home: {catalog_url}")
    try:
        response = requests.get(catalog_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        targets = [
            "Undergraduate Degrees by School/College",
            "Undergraduate Degrees by School",
            "Undergraduate Degrees", 
            "Undergraduate Programs", 
            "Majors and Minors", 
            "Degrees and Programs"
        ]
        
        # 1. Try finding exact text match
        for target in targets:
            link = soup.find('a', string=re.compile(target, re.IGNORECASE))
            if link:
                print(f"Found link for '{target}'")
                href = link['href']
                if not href.startswith('http'):
                     if href.startswith('/'):
                         return BASE_URL + href
                     else:
                         return f"{BASE_URL}/{href}"
                return href
        
        # 2. Search all links for navoid and keywords in text
        links = soup.find_all('a', href=True)
        for link in links:
            if f"catoid={catoid}" in link['href'] and "navoid=" in link['href']:
                text = link.get_text().strip()
                if any(t in text for t in targets):
                     href = link['href']
                     if not href.startswith('http'):
                         return f"{BASE_URL}/{href}"
                     return href
                     
        return None
    except Exception as e:
        print(f"Error fetching catalog home: {e}")
        return None

def parse_program_details(program_url):
    """
    Visits the specific program page and extracts requirements, courses, and text.
    """
    try:
        # print(f"  Parsing details: {program_url}")
        response = requests.get(program_url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # The main content area
        content_div = soup.find('div', class_='custom_leftpad_20') or \
                      soup.find('td', class_='block_content') or \
                      soup.find('div', class_='block_content') or \
                      soup
        
        requirements = []
        current_section = {"title": "General Information", "content": []}
        
        # Helper to process an element
        def process_element(el):
            # Text / Paragraphs
            if el.name in ['p', 'div', 'span', 'li']:
                text = el.get_text(" ", strip=True)
                if text and len(text) > 1:
                    # Check if it's a course link
                    course_link = el.find('a', href=re.compile(r'preview_course'))
                    if course_link:
                        return {
                            "type": "course",
                            "text": text,
                            "course_code": course_link.get_text().strip(),
                            "url": f"{BASE_URL}/{course_link['href']}" if not course_link['href'].startswith('http') else course_link['href']
                        }
                    else:
                        return {"type": "text", "text": text}
            return None

        # Iterate through elements to structure data
        # This is a simplified approach; robust parsing of nested lists/tables is hard generically
        for element in content_div.descendants:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong']:
                header_text = element.get_text().strip()
                if header_text and len(header_text) < 200:
                    # Save previous section if it has content
                    if current_section["content"]:
                        requirements.append(current_section)
                    
                    current_section = {"title": header_text, "content": []}
            
            elif element.name == 'a' and element.has_attr('href') and 'preview_course' in element['href']:
                 # It's a course
                 text = element.parent.get_text(" ", strip=True) # Context
                 current_section["content"].append({
                     "type": "course",
                     "code": element.get_text().strip(),
                     "description": text,
                     "link": f"{BASE_URL}/{element['href']}" if not element['href'].startswith('http') else element['href']
                 })
            
            elif element.name == 'p':
                text = element.get_text(" ", strip=True)
                if text:
                    current_section["content"].append({"type": "text", "value": text})
                    
        # Append final section
        if current_section["content"]:
            requirements.append(current_section)
            
        return requirements

    except Exception as e:
        print(f"  Error parsing details for {program_url}: {e}")
        return []

def parse_programs_page(url):
    print(f"Parsing programs from: {url}")
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        programs = []
        content_div = soup.find('td', class_='block_content') or soup.find('div', class_='block_content') or soup
        
        current_school = "General / Unknown"
        
        # Iterate through all elements to track headers (schools) and links (programs)
        for element in content_div.descendants:
            # Check for school headers
            if element.name in ['h1', 'h2', 'h3', 'strong']:
                text = element.get_text().strip()
                # Heuristic: valid school names usually contain these words
                if any(x in text for x in ["College", "School", "Conservatory", "Institute"]) and len(text) < 100:
                    # Clean up formatting if needed
                    current_school = text.replace(':', '').strip()
            
            # Check for program links
            if element.name == 'a' and element.has_attr('href'):
                href = element['href']
                if 'preview_program.php' in href:
                    name = element.get_text().strip()
                    if not name:
                        continue
                        
                    poid_match = re.search(r'poid=(\d+)', href)
                    poid = poid_match.group(1) if poid_match else None
                    
                    # Infer degree type
                    degree_type = "Other"
                    if ", B.A." in name: degree_type = "B.A."
                    elif ", B.S." in name: degree_type = "B.S."
                    elif ", B.F.A." in name: degree_type = "B.F.A."
                    elif ", B.M." in name: degree_type = "B.M."
                    elif "Minor" in name: degree_type = "Minor"
                    
                    programs.append({
                        'name': name,
                        'type': degree_type,
                        'school': current_school,
                        'poid': poid,
                        'url': f"{BASE_URL}/{href}" if not href.startswith('http') else href
                    })
        
        # Deduplicate logic
        unique_programs = {}
        for p in programs:
            # Use POID as unique key if available, otherwise name
            key = p['poid'] if p['poid'] else p['name']
            
            if key not in unique_programs:
                unique_programs[key] = p
            else:
                # If we already have this program, prefer the one with a specific school
                if unique_programs[key]['school'] == "General / Unknown" and p['school'] != "General / Unknown":
                    unique_programs[key]['school'] = p['school']
                    
        return list(unique_programs.values())
    except Exception as e:
        print(f"Error parsing programs page: {e}")
        return []

def _make_program_key(prog: dict) -> str:
    """Create a stable key for a program (POID if present, else name)."""
    return prog.get('poid') or prog.get('name') or ""


def _ensure_catalog_entry(all_data: list, cat: dict, programs_url: str) -> dict:
    """Find or create the catalog entry for a given year in all_data."""
    for entry in all_data:
        if entry.get('year') == cat['year']:
            # Backfill URLs if they were missing before
            entry.setdefault('catalog_url', cat['url'])
            if programs_url:
                entry.setdefault('programs_list_url', programs_url)
            entry.setdefault('programs', [])
            return entry

    new_entry = {
        'year': cat['year'],
        'catoid': cat['catoid'],
        'catalog_url': cat['url'],
        'programs_list_url': programs_url,
        'programs': [],
    }
    all_data.append(new_entry)
    return new_entry


def _process_catalog(cat: dict, output_file: str, all_data: list, lock: threading.Lock) -> None:
    """Process a single catalog (one year): fetch programs and details.

    This function is safe to run in parallel across years. It checkpoints
    each program into the shared all_data list and writes the full JSON file
    after every program, guarded by a lock so reruns can resume cleanly.
    """
    year = cat['year']
    print(f"\n=== Processing Catalog {year} ({cat['catoid']}) ===")

    programs_url = get_programs_page_url(cat['url'], cat['catoid'])
    if not programs_url:
        print("Could not find programs URL for this catalog.")
        return

    programs = parse_programs_page(programs_url)
    print(f"Found {len(programs)} programs. Fetching details...")

    # Snapshot existing programs for this catalog so we can resume.
    with lock:
        cat_entry = _ensure_catalog_entry(all_data, cat, programs_url)
        existing_by_key = {}
        for existing_prog in cat_entry.get('programs', []):
            key = _make_program_key(existing_prog)
            if key:
                existing_by_key[key] = existing_prog

    total = len(programs)

    def _process_program_item(args):
        idx, prog = args
        key = _make_program_key(prog)
        already = existing_by_key.get(key)

        # If we already have this program and it has requirements, skip it.
        if already and already.get('requirements'):
            print(f"[{year}] [{idx}/{total}] Skipping already-scraped: {prog['name']}")
            return

        print(f"[{year}] [{idx}/{total}] Scraping: {prog['name']}")
        prog_copy = dict(prog)
        prog_copy['requirements'] = parse_program_details(prog['url'])

        # Be polite to the remote server
        time.sleep(0.1)

        # Checkpoint: merge into shared all_data and write file atomically
        with lock:
            cat_entry = _ensure_catalog_entry(all_data, cat, programs_url)
            prog_list = cat_entry.setdefault('programs', [])

            replaced = False
            for i, existing_prog in enumerate(prog_list):
                if _make_program_key(existing_prog) == key:
                    prog_list[i] = prog_copy
                    replaced = True
                    break
            if not replaced:
                prog_list.append(prog_copy)

            tmp_path = output_file + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, indent=2)

            # Windows can briefly hold the destination file handle; retry a few times.
            replace_ok = False
            for attempt in range(3):
                try:
                    os.replace(tmp_path, output_file)
                    replace_ok = True
                    break
                except PermissionError as e:
                    print(f"[{year}] Warning: os.replace failed (attempt {attempt+1}/3): {e}")
                    time.sleep(0.2)
            if not replace_ok:
                print(f"[{year}] ERROR: Failed to replace {output_file} after retries; leaving {tmp_path} for inspection.")

    # Use a small per-catalog thread pool (2 workers) so each year can fetch
    # program details in parallel while keeping total load reasonable.
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(_process_program_item, list(enumerate(programs, start=1))))

    print(f"Finished catalog {year}")


def main():
    catalogs = get_catalogs()
    print(f"Found {len(catalogs)} catalogs.")

    # Filter for the last 6 years as requested
    recent_catalogs = [c for c in catalogs if int(c['year'].split('-')[0]) >= 2019]
    print(f"Processing {len(recent_catalogs)} catalogs from 2019 onwards.")

    # Always write to backend/data relative to the backend root, regardless of CWD
    # __file__ = backend/app/scrapers/scrape_chapman.py
    # parents[0] = scrapers, [1] = app, [2] = backend
    backend_root = Path(__file__).resolve().parents[2]
    output_dir = backend_root / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = str(output_dir / "chapman_catalogs_full.json")

    # Load existing data so reruns can resume without losing prior work
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            if not isinstance(all_data, list):
                print("Existing catalog file was not a list; starting fresh.")
                all_data = []
        except Exception as e:
            print(f"Failed to read existing catalog file, starting fresh: {e}")
            all_data = []
    else:
        all_data = []

    if not recent_catalogs:
        print("No recent catalogs to process.")
        return

    lock = threading.Lock()
    max_workers = min(len(recent_catalogs), 6) or 1

    # Run each catalog (year) in parallel. Each catalog itself processes
    # programs sequentially but checkpoints per program.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_process_catalog, cat, output_file, all_data, lock)
            for cat in recent_catalogs
        ]
        # Ensure any exceptions surface
        for fut in futures:
            fut.result()

    print(f"\nFull data saved to {output_file}")

if __name__ == "__main__":
    main()
