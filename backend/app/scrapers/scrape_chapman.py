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

def get_catalogs(include_graduate: bool = True):
    """
    Fetch available catalogs from Chapman University.

    Args:
        include_graduate: If True, also fetch Graduate catalogs (default: True)

    Returns:
        List of catalog dictionaries with year, url, catoid, text, and catalog_type
    """
    print(f"Fetching catalog list from {CATALOG_LIST_URL}...")
    try:
        response = requests.get(CATALOG_LIST_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        catalogs = []
        links = soup.find_all('a', href=True)

        # Patterns to match both Undergraduate and Graduate catalogs
        catalog_patterns = [
            (r'(\d{4}-\d{4}).*Undergraduate Catalog', 'undergraduate'),
        ]
        if include_graduate:
            catalog_patterns.append((r'(\d{4}-\d{4}).*Graduate Catalog', 'graduate'))

        for link in links:
            text = link.get_text().strip()
            href = link['href']

            for pattern, catalog_type in catalog_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
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
                            'text': text,
                            'catalog_type': catalog_type
                        })
                    break  # Don't match both patterns for same link

        # Use (year, catalog_type) as unique key to keep both undergrad and grad
        unique_catalogs = {}
        for c in catalogs:
            key = (c['year'], c['catalog_type'])
            unique_catalogs[key] = c

        return sorted(unique_catalogs.values(), key=lambda x: (x['year'], x['catalog_type']), reverse=True)
    except Exception as e:
        print(f"Error fetching catalog list: {e}")
        return []

def get_programs_page_url(catalog_url, catoid, catalog_type: str = 'undergraduate'):
    """
    Find the programs listing page URL for a catalog.

    Args:
        catalog_url: The catalog home page URL
        catoid: The catalog ID
        catalog_type: 'undergraduate' or 'graduate'
    """
    print(f"Fetching catalog home: {catalog_url}")
    try:
        response = requests.get(catalog_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Different targets for undergraduate vs graduate catalogs
        if catalog_type == 'graduate':
            targets = [
                "Graduate Degree Programs by School/College",
                "Graduate Degrees by School/College",
                "Graduate Degrees by School",
                "Graduate Degrees",
                "Graduate Programs",
                "Degrees and Programs"
            ]
        else:
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

def _normalize_course_code(raw_code: str) -> str:
    """
    Normalize a course code to a standard format: 'SUBJ NNN' (e.g., 'CPSC 350').
    Handles various formats like 'CPSC 350', 'CPSC-350', 'CPSC350', etc.
    """
    # Remove non-breaking spaces and extra whitespace
    cleaned = raw_code.replace('\xa0', ' ').strip()
    # Try to extract subject and number
    match = re.match(r'([A-Z]{2,5})\s*[-]?\s*(\d{3}[A-Z]?)', cleaned, re.IGNORECASE)
    if match:
        subject = match.group(1).upper()
        number = match.group(2).upper()
        return f"{subject} {number}"
    return cleaned


def _classify_requirement_type(title: str) -> str:
    """
    Classify a requirement section based on its title.
    Returns one of: 'core', 'elective', 'general_education', 'prerequisite', 'other'
    """
    title_lower = title.lower()

    # Core requirements
    if any(kw in title_lower for kw in ['core', 'required', 'foundation', 'major requirement']):
        return 'core'

    # Electives
    if any(kw in title_lower for kw in ['elective', 'technical elective', 'approved elective']):
        return 'elective'

    # General education
    if any(kw in title_lower for kw in ['general education', 'ge ', 'gen ed', 'liberal arts']):
        return 'general_education'

    # Prerequisites
    if any(kw in title_lower for kw in ['prerequisite', 'pre-requisite', 'corequisite', 'co-requisite']):
        return 'prerequisite'

    # Concentration/specialization
    if any(kw in title_lower for kw in ['concentration', 'specialization', 'emphasis', 'track']):
        return 'concentration'

    # Capstone/thesis
    if any(kw in title_lower for kw in ['capstone', 'thesis', 'dissertation', 'project']):
        return 'capstone'

    return 'other'


def _extract_courses_from_text(text: str) -> list:
    """
    Extract course codes from plain text using regex.
    Matches patterns like 'CPSC 230', 'MATH 110', 'ENGR 501', etc.
    """
    # Pattern: 2-5 uppercase letters, optional space/dash, 3 digits, optional letter
    pattern = r'\b([A-Z]{2,5})\s*[-]?\s*(\d{3}[A-Z]?)\b'
    matches = re.findall(pattern, text)

    courses = []
    for subject, number in matches:
        # Filter out false positives (common non-course patterns)
        if subject in ['HELP', 'ISBN', 'HTTP', 'HTML', 'HTTPS', 'PHONE', 'FAX']:
            continue
        normalized = f"{subject} {number}"
        if normalized not in courses:
            courses.append(normalized)

    return courses


def parse_program_details(program_url):
    """
    Visits the specific program page and extracts requirements, courses, and text.
    Enhanced to categorize requirements and normalize course codes.
    Also extracts course codes from plain text (not just hyperlinks).
    """
    try:
        response = requests.get(program_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # The main content area
        content_div = soup.find('div', class_='custom_leftpad_20') or \
                      soup.find('td', class_='block_content') or \
                      soup.find('div', class_='block_content') or \
                      soup

        requirements = []
        current_section = {
            "title": "General Information",
            "requirement_type": "other",
            "content": [],
            "courses": []  # Separate list for just course codes
        }

        # Track which courses we've already added (to avoid duplicates)
        seen_courses_in_section = set()

        # Iterate through elements to structure data
        for element in content_div.descendants:
            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong']:
                header_text = element.get_text().strip()
                if header_text and len(header_text) < 200:
                    # Save previous section if it has content
                    if current_section["content"] or current_section["courses"]:
                        requirements.append(current_section)

                    current_section = {
                        "title": header_text,
                        "requirement_type": _classify_requirement_type(header_text),
                        "content": [],
                        "courses": []
                    }
                    seen_courses_in_section = set()

            elif element.name == 'a' and element.has_attr('href') and 'preview_course' in element['href']:
                # It's a course link
                raw_code = element.get_text().strip()
                normalized_code = _normalize_course_code(raw_code)
                context_text = element.parent.get_text(" ", strip=True) if element.parent else raw_code

                course_entry = {
                    "type": "course",
                    "code": normalized_code,
                    "raw_code": raw_code,
                    "description": context_text,
                    "link": f"{BASE_URL}/{element['href']}" if not element['href'].startswith('http') else element['href']
                }
                current_section["content"].append(course_entry)

                # Also add to the simplified courses list
                if normalized_code and normalized_code not in seen_courses_in_section:
                    current_section["courses"].append(normalized_code)
                    seen_courses_in_section.add(normalized_code)

            elif element.name == 'p':
                text = element.get_text(" ", strip=True)
                if text:
                    current_section["content"].append({"type": "text", "value": text})

                    # Also extract course codes from plain text
                    text_courses = _extract_courses_from_text(text)
                    for course in text_courses:
                        if course not in seen_courses_in_section:
                            current_section["courses"].append(course)
                            seen_courses_in_section.add(course)

            # Also check for text nodes that might contain course codes
            elif element.name is None and isinstance(element, str):
                text = element.strip()
                if text and len(text) > 5:
                    text_courses = _extract_courses_from_text(text)
                    for course in text_courses:
                        if course not in seen_courses_in_section:
                            current_section["courses"].append(course)
                            seen_courses_in_section.add(course)

        # Append final section
        if current_section["content"] or current_section["courses"]:
            requirements.append(current_section)

        # Create a summary of all courses found in this program
        all_courses = []
        core_courses = []
        elective_courses = []

        for req in requirements:
            courses = req.get("courses", [])
            all_courses.extend(courses)
            if req.get("requirement_type") == "core":
                core_courses.extend(courses)
            elif req.get("requirement_type") == "elective":
                elective_courses.extend(courses)

        # Return enhanced structure
        return {
            "sections": requirements,
            "all_courses": list(set(all_courses)),
            "core_courses": list(set(core_courses)),
            "elective_courses": list(set(elective_courses))
        }

    except Exception as e:
        print(f"  Error parsing details for {program_url}: {e}")
        return {"sections": [], "all_courses": [], "core_courses": [], "elective_courses": []}

def _infer_degree_type(name: str) -> str:
    """
    Infer the degree type from a program name.
    Handles both undergraduate and graduate degree types.
    """
    # Graduate degrees (check first as they're more specific)
    if ", Ph.D." in name or "Ph.D." in name:
        return "Ph.D."
    if ", M.S." in name:
        return "M.S."
    if ", M.A." in name:
        return "M.A."
    if ", M.B.A." in name or "MBA" in name:
        return "M.B.A."
    if ", M.F.A." in name:
        return "M.F.A."
    if ", M.Ed." in name:
        return "M.Ed."
    if ", Pharm.D." in name:
        return "Pharm.D."
    if ", J.D." in name:
        return "J.D."
    if ", Ed.D." in name:
        return "Ed.D."

    # Undergraduate degrees
    if ", B.A." in name:
        return "B.A."
    if ", B.S." in name:
        return "B.S."
    if ", B.F.A." in name:
        return "B.F.A."
    if ", B.M." in name:
        return "B.M."

    # Other program types
    if "Minor" in name:
        return "Minor"
    if "Certificate" in name:
        return "Certificate"
    if "Credential" in name:
        return "Credential"

    return "Other"


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

                    # Infer degree type (now handles graduate degrees too)
                    degree_type = _infer_degree_type(name)

                    # Determine if it's a graduate program
                    is_graduate = degree_type in ['Ph.D.', 'M.S.', 'M.A.', 'M.B.A.', 'M.F.A.',
                                                   'M.Ed.', 'Pharm.D.', 'J.D.', 'Ed.D.']

                    programs.append({
                        'name': name,
                        'type': degree_type,
                        'is_graduate': is_graduate,
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
    """Find or create the catalog entry for a given year and type in all_data."""
    catalog_type = cat.get('catalog_type', 'undergraduate')

    for entry in all_data:
        # Match by both year AND catalog_type to keep undergrad/grad separate
        if entry.get('year') == cat['year'] and entry.get('catalog_type', 'undergraduate') == catalog_type:
            # Backfill URLs if they were missing before
            entry.setdefault('catalog_url', cat['url'])
            if programs_url:
                entry.setdefault('programs_list_url', programs_url)
            entry.setdefault('programs', [])
            return entry

    new_entry = {
        'year': cat['year'],
        'catoid': cat['catoid'],
        'catalog_type': catalog_type,
        'catalog_url': cat['url'],
        'programs_list_url': programs_url,
        'programs': [],
    }
    all_data.append(new_entry)
    return new_entry


def _process_catalog(cat: dict, output_file: str, all_data: list, lock: threading.Lock) -> None:
    """Process a single catalog (one year, one type): fetch programs and details.

    This function is safe to run in parallel across years. It checkpoints
    each program into the shared all_data list and writes the full JSON file
    after every program, guarded by a lock so reruns can resume cleanly.
    """
    year = cat['year']
    catalog_type = cat.get('catalog_type', 'undergraduate')
    print(f"\n=== Processing {catalog_type.title()} Catalog {year} ({cat['catoid']}) ===")

    programs_url = get_programs_page_url(cat['url'], cat['catoid'], catalog_type)
    if not programs_url:
        print(f"Could not find programs URL for this {catalog_type} catalog.")
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

    print(f"Finished catalog {year} ({catalog_type})")


def build_course_to_program_mapping(all_data: list) -> dict:
    """
    Build a reverse lookup mapping from course codes to programs that require them.

    Returns a dict like:
    {
        "CPSC 350": [
            {"program": "Computer Science, B.S.", "year": "2025-2026", "type": "core"},
            {"program": "Software Engineering, B.S.", "year": "2025-2026", "type": "elective"}
        ],
        ...
    }
    """
    course_mapping = {}

    def _add_course(course: str, program_name: str, year: str, catalog_type: str, req_type: str):
        """Helper to add a course to the mapping, avoiding duplicates."""
        if not course:
            return
        if course not in course_mapping:
            course_mapping[course] = []
        # Check if this exact entry already exists
        entry = {
            'program': program_name,
            'year': year,
            'catalog_type': catalog_type,
            'requirement_type': req_type
        }
        if entry not in course_mapping[course]:
            course_mapping[course].append(entry)

    for catalog in all_data:
        year = catalog.get('year', 'unknown')
        catalog_type = catalog.get('catalog_type', 'undergraduate')

        for program in catalog.get('programs', []):
            program_name = program.get('name', 'Unknown Program')
            requirements = program.get('requirements', {})

            # Handle both old format (list) and new format (dict with sections)
            if isinstance(requirements, dict):
                # New format - track which courses we've added with specific types
                core_courses = set(requirements.get('core_courses', []))
                elective_courses = set(requirements.get('elective_courses', []))
                all_courses = set(requirements.get('all_courses', []))

                # Add core courses
                for course in core_courses:
                    _add_course(course, program_name, year, catalog_type, 'core')

                # Add elective courses
                for course in elective_courses:
                    _add_course(course, program_name, year, catalog_type, 'elective')

                # Add remaining courses from all_courses that aren't core or elective
                # These are likely technical electives or other program requirements
                remaining = all_courses - core_courses - elective_courses
                for course in remaining:
                    # Try to infer type from sections
                    req_type = 'program_requirement'
                    for section in requirements.get('sections', []):
                        if course in section.get('courses', []):
                            section_type = section.get('requirement_type', 'other')
                            if section_type != 'other':
                                req_type = section_type
                            break
                    _add_course(course, program_name, year, catalog_type, req_type)

            elif isinstance(requirements, list):
                # Old format - iterate through sections
                for section in requirements:
                    section_type = section.get('requirement_type', 'unknown')
                    # Check courses list first (new format within old)
                    for course in section.get('courses', []):
                        _add_course(course, program_name, year, catalog_type, section_type)
                    # Also check content for course entries
                    for content_item in section.get('content', []):
                        if content_item.get('type') == 'course':
                            code = content_item.get('code', '')
                            normalized = _normalize_course_code(code)
                            if normalized:
                                _add_course(normalized, program_name, year, catalog_type, section_type)

    return course_mapping


def main():
    # Now fetches both undergraduate AND graduate catalogs
    catalogs = get_catalogs(include_graduate=True)
    print(f"Found {len(catalogs)} catalogs (undergraduate + graduate).")

    # Count by type
    undergrad_count = sum(1 for c in catalogs if c.get('catalog_type') == 'undergraduate')
    grad_count = sum(1 for c in catalogs if c.get('catalog_type') == 'graduate')
    print(f"  - Undergraduate: {undergrad_count}")
    print(f"  - Graduate: {grad_count}")

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

    # Run each catalog (year + type) in parallel. Each catalog itself processes
    # programs sequentially but checkpoints per program.
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(_process_catalog, cat, output_file, all_data, lock)
            for cat in recent_catalogs
        ]
        # Ensure any exceptions surface
        for fut in futures:
            fut.result()

    # Build and save course-to-program mapping
    print("\nBuilding course-to-program mapping...")
    course_mapping = build_course_to_program_mapping(all_data)
    mapping_file = str(output_dir / "course_to_program_mapping.json")
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(course_mapping, f, indent=2)
    print(f"Course mapping saved to {mapping_file}")
    print(f"Total unique courses mapped: {len(course_mapping)}")

    # Print summary
    total_programs = sum(len(entry.get('programs', [])) for entry in all_data)
    print(f"\n=== Scraping Complete ===")
    print(f"Total catalogs: {len(all_data)}")
    print(f"Total programs: {total_programs}")
    print(f"Total unique courses: {len(course_mapping)}")
    print(f"Data saved to {output_file}")


if __name__ == "__main__":
    main()
