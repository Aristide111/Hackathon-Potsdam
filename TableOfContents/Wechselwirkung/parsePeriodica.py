import csv
import json
import re
from pathlib import Path
from urllib.parse import quote
import requests


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/ld+json, application/json, text/html,*/*;q=0.01",
    "Referer": "https://www.e-periodica.ch/",
}


def pick_text(value):
    # Return the first available localized text value from IIIF objects.
    if isinstance(value, dict):
        for key in ("en", "de", "fr", "none"):
            if key in value and value[key]:
                return value[key][0]
        for item in value.values():
            text = pick_text(item)
            if text is not None:
                return text
    elif isinstance(value, list):
        for item in value:
            text = pick_text(item)
            if text is not None:
                return text
    elif isinstance(value, str):
        return value
    return None


def encode_pid(pid):
    # Encode PID for RIS and homepage URLs.
    return quote(pid, safe="")


def band_pid_for_year(year):
    # Build the band PID, e.g. wsw-001:1979:1.
    n = year - 1978
    return f"wsw-001:{year}:{n}"


def band_manifest_url(pid):
    # Band-level IIIF manifest URL.
    return f"https://www.e-periodica.ch/iiif/{pid}/manifest"


def manifest_url_from_range_id(range_id):
    # Convert range ID like ...::272/range into ...::272/manifest.
    return range_id.replace("/range", "/manifest")


def ris_url(pid):
    # RIS endpoint for the given PID.
    return f"https://www.e-periodica.ch/ris?pid={encode_pid(pid)}"


def fetch_json(url):
    # Download JSON from the given URL, fail gracefully on decoding errors.
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        print(f"Warning: could not fetch JSON from {url} ({exc})")
        return {}


def fetch_text(url):
    # Download text content from the given URL, fail gracefully.
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        print(f"Warning: could not fetch text from {url} ({exc})")
        return ""


def parse_article_manifest(manifest):
    # Extract only required IIIF fields for one article.
    metadata = {}
    for item in manifest.get("metadata", []):
        label = pick_text(item.get("label"))
        value = pick_text(item.get("value"))
        if label:
            metadata[label] = value

    pages = []
    for canvas in manifest.get("items", []):
        label = pick_text(canvas.get("label"))
        if label and str(label).isdigit():
            pages.append(label)

    return {
        "title": pick_text(manifest.get("label")) or "",
        "pages": f"{pages[0]}-{pages[-1]}" if pages else "",
    }


def parse_ris(text):
    # Parse RIS and extract author(s) and publication year.
    if not text.strip():
        return {"author": "", "year": ""}

    authors = []
    year = None

    for line in text.splitlines():
        if len(line) < 6 or "-" not in line[:6]:
            continue
        tag = line[:2]
        value = line[6:].strip()
        if tag == "AU":
            authors.append(value)
        elif tag in ("Y1", "PY") and year is None:
            match = re.search(r"(\d{4})", value)
            year = match.group(1) if match else value

    return {
        "author": "; ".join(authors) if authors else "",
        "year": year or "",
    }


def scrape_article(article_range_id):
    # Scrape one article using its manifest and RIS record.
    article_pid = article_range_id.split("/range")[0].split("/iiif/")[-1]
    manifest_url = manifest_url_from_range_id(article_range_id)
    iiif_manifest = fetch_json(manifest_url)
    iiif_data = parse_article_manifest(iiif_manifest)

    # Try RIS fetch; fall back silently if missing or invalid.
    ris_data = {"author": "", "year": ""}
    try:
        ris_text = fetch_text(ris_url(article_pid))
        ris_data = parse_ris(ris_text)
    except Exception as exc:
        print(f"Warning: missing or invalid RIS for {article_pid} ({exc})")

    return {
        "manifest_url": manifest_url,
        "article_pid": article_pid,
        "year": ris_data.get("year", "") or "",
        "author": ris_data.get("author", "") or "",
        "title": iiif_data.get("title", "") or "",
        "pages": iiif_data.get("pages", "") or "",
    }


def get_nested_range_ids(manifest):
    # Recursively collect all range IDs from manifest structures.
    range_ids = []

    def recurse(items):
        for item in items:
            item_id = item.get("id")
            item_type = item.get("type")
            if item_id and item_type == "Range":
                range_ids.append(item_id)
            elif "items" in item:
                recurse(item["items"])

    for structure in manifest.get("structures", []):
        recurse(structure.get("items", []))
    return range_ids


def parse_issue_manifest(manifest):
    # Extract issue-level metadata, including ISSN and issue number.
    metadata = {}
    for item in manifest.get("metadata", []):
        label = pick_text(item.get("label"))
        value = pick_text(item.get("value"))
        if label:
            metadata[label] = value

    issue_number = metadata.get("Heftnummer") or metadata.get("Number") or ""
    issn = metadata.get("ISSN") or ""

    return {
        "issn": issn,
        "issue_number": issue_number,
    }


def scrape_issue(issue_pid):
    # Scrape one issue and collect all articles beneath it.
    issue_manifest_url = manifest_url_from_range_id(f"https://www.e-periodica.ch/iiif/{issue_pid}/range")
    issue_manifest = fetch_json(issue_manifest_url)
    issue_info = parse_issue_manifest(issue_manifest)
    article_range_ids = get_nested_range_ids(issue_manifest)

    articles = []
    for article_range_id in article_range_ids:
        try:
            articles.append(scrape_article(article_range_id))
        except Exception as exc:
            manifest_url = manifest_url_from_range_id(article_range_id)
            article_pid = article_range_id.split("/range")[0].split("/iiif/")[-1]
            articles.append({
                "manifest_url": manifest_url,
                "article_pid": article_pid,
                "year": "",
                "author": "",
                "title": "",
                "pages": "",
                "error": str(exc),
            })

    return {
        "issue_pid": issue_pid,
        "issue_manifest_url": issue_manifest_url,
        "issue_number": issue_info["issue_number"],
        "issn": issue_info["issn"],
        "articles": articles,
    }


def scrape_periodical(start_year=1979, end_year=1990):
    # Scrape all bands/years and return a nested structure.
    bands = []

    for year in range(start_year, end_year + 1):
        band_pid = band_pid_for_year(year)
        band_manifest = fetch_json(band_manifest_url(band_pid))
        issue_range_ids = get_nested_range_ids(band_manifest)

        issues = []
        for issue_range_id in issue_range_ids:
            issue_pid = issue_range_id.split("/range")[0].split("/iiif/")[-1]
            try:
                issues.append(scrape_issue(issue_pid))
            except Exception as exc:
                issues.append({
                    "issue_pid": issue_pid,
                    "issue_manifest_url": manifest_url_from_range_id(issue_range_id),
                    "issue_number": "",
                    "issn": "",
                    "error": str(exc),
                    "articles": [],
                })

        bands.append({
            "band_pid": band_pid,
            "band_manifest_url": band_manifest_url(band_pid),
            "issues": issues,
        })

    return bands


def save_output(data):
    # Save the nested result as JSON and flattened CSV.
    Path("output").mkdir(exist_ok=True)

    with open("output/eperiodica_nested.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    rows = []
    for band in data:
        for issue in band.get("issues", []):
            for article in issue.get("articles", []):
                row = dict(article)
                row["band_pid"] = band.get("band_pid", "")
                row["issue_pid"] = issue.get("issue_pid", "")
                row["issue_number"] = issue.get("issue_number", "")
                row["issn"] = issue.get("issn", "")
                rows.append(row)

    fieldnames = [
        "band_pid", "issue_pid", "issue_number", "article_pid", 
        "manifest_url", "year", "author", "title", "pages", "issn", "error"
    ]
    with open("output/eperiodica_flat.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    result = scrape_periodical(1979, 1990)
    save_output(result)
    print(json.dumps(result[:1], ensure_ascii=False, indent=2))