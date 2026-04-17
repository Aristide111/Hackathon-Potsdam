import weaviate
from weaviate.classes.init import Auth
from weaviate.util import generate_uuid5
import os, json, csv
from dotenv import load_dotenv

# Load the environmental variable 
load_dotenv()
DATA_FOLDER = os.environ['DATA_FOLDER']
# Connect to Weaviate

with weaviate.connect_to_local() as client:
    # ─────────────────────────────────────────────
    # CSV PARSING
    # ─────────────────────────────────────────────
    def parse_issues_csv(csv_path: str) -> dict:
        """
        Reads a CSV file with columns:
            year, issue_number, pages, filename, manifest

        Returns a dict keyed by manifest URL so that each issue record
        can be looked up when processing the JSON data.

        The pdf_path is built by prepending the DATA_FOLDER environment
        variable to the filename column.
        """
        data_folder = os.environ.get("DATA_FOLDER", "")
        issues_by_manifest = {}

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest = row["manifest"].strip()
                issues_by_manifest[manifest] = {
                    "publication_year": int(row["year"]) if row["year"].strip() else 0,
                    "issue_number":     int(row["issue_number"]) if row["issue_number"].strip() else 0,
                    "pages":            int(row["pages"]) if row["pages"].strip() else 0,
                    # Prepend DATA_FOLDER to the filename to get the full pdf_path
                    "pdf_path":         os.path.join(data_folder, row["filename"].strip()),
                }

        return issues_by_manifest


    # ─────────────────────────────────────────────
    # PAGE RANGE HELPER
    # ─────────────────────────────────────────────
    def parse_page_range(pages_str):
        """
        Splits a page range string such as "267-270" into (start_page, end_page).
        Returns (None, None) if the string is empty or cannot be parsed.
        """
        pages_str = str(pages_str).strip()
        if not pages_str:
            return None, None
        if "-" in pages_str:
            parts = pages_str.split("-")
            try:
                return int(parts[0].strip()), int(parts[1].strip())
            except ValueError:
                return None, None
        try:
            val = int(pages_str)
            return val, val
        except ValueError:
            return None, None


    # ─────────────────────────────────────────────
    # MAIN IMPORT
    # ─────────────────────────────────────────────

    # Load CSV metadata (keyed by manifest URL)
    csv_path = DATA_FOLDER + "metadata_wechselwirkung_complete.csv"
    csv_issues = parse_issues_csv(csv_path)

    # Load JSON data with UTF-8 encoding.
    # The top-level structure is a list of "band" objects,
    # each containing an "issues" list.
    with open("TableOfContents/Wechselwirkung/output/eperiodica_nested.json", "r", encoding="utf-8") as f:
        bands_data = json.load(f)

    # Get collection handles
    issues_collection   = client.collections.get("Issue")
    articles_collection = client.collections.get("Article")
    periodical_collection   = client.collections.get("Periodical")

    # ── CREATE ENTRY FOR PERIODICAL ───────────────────────────────────────────────
    periodical_url = "https://www.e-periodica.ch/digbib/volumes?UID=wsw-001"
    periodical_uuid = generate_uuid5(periodical_url)
    periodical_props = {
        "title":     "Wechselwirkung : Technik Naturwissenschaft Gesellschaft",
        "publisher": "Wechselwirkung Verlag GmbH",
        "access_url": periodical_url
    }
    periodical_collection.data.insert(
        properties=periodical_props,
        uuid=periodical_uuid,
    )
    # ── ITERATE OVER BANDS ────────────────────────────────────────────────────────
    # The JSON is a list of band objects. Each band contains an "issues" list.
    for band in bands_data:
        # ── ITERATE OVER ISSUES WITHIN EACH BAND ─────────────────────────────────
        for issue_data in band.get("issues", []):
            # Use the correct key "issue_manifest_url" from the nested issue object
            issue_manifest = issue_data["issue_manifest_url"]

            # Look up the CSV row that matches this issue's manifest URL
            csv_row = csv_issues.get(issue_manifest, {})

            # ── CREATE ISSUE ENTRY ────────────────────────────────────────────────
            # One Issue object is inserted per entry in the "issues" list.
            # Properties come from the CSV (via the manifest key) and the JSON.
            # A deterministic UUID is generated from the manifest URL so that
            # re-running the script does not create duplicate entries.
            issue_uuid = generate_uuid5(issue_manifest)
            issue_props = {
                "issue_number":     csv_row.get("issue_number",     int(issue_data.get("issue_number", 0) or 0)),
                "publication_year": csv_row.get("publication_year", int(issue_data.get("year", 0) or 0)),
                "pdf_path":         csv_row.get("pdf_path",         ""),  # full path = DATA_FOLDER + filename
                "pages":            csv_row.get("pages",            0),
            }
            issues_collection.data.insert(
                properties=issue_props,
                uuid=issue_uuid,
            )
            # ── LINK ISSUE TO PERIODICAL ────────────────────────────────────────────
            # After all articles for this issue are inserted, add a reference from
            # the Issue object to each Article object via the "hasArticle" property.
            periodical_collection.data.reference_add(
                from_uuid=periodical_uuid,
                from_property="hasIssue",
                to=issue_uuid,
            )
            # ── CREATE ARTICLE ENTRIES ────────────────────────────────────────────
            # For each article listed under "articles" in the issue, one Article
            # object is created. Articles are inserted in batches of 200 for
            # efficiency. The batcher automatically flushes when the batch_size is
            # reached and tracks errors via batch.number_errors during the import.
            article_uuids = []

            with articles_collection.batch.fixed_size(batch_size=200) as batch:
                for article in issue_data.get("articles", []):
                    # Split the "pages" field (e.g. "1-2") into start_page / end_page
                    start_page, end_page = parse_page_range(article.get("pages", ""))
                    if int(issue_data.get("issue_number")) == 0 and start_page and end_page:
                        start_page += 2
                        end_page += 2
                    # Generate a deterministic UUID from the article's manifest URL
                    article_uuid = generate_uuid5(article["manifest_url"])
                    article_uuids.append(article_uuid)

                    batch.add_object(
                        properties={
                            "title":        article.get("title", ""),
                            "manifest":     article.get("manifest_url", ""),
                            "author":       article.get("author", ""),
                            "start_page":   start_page,
                            "end_page":     end_page,
                        },
                        uuid=article_uuid,
                    )

                    # Stop early if too many errors accumulate
                    if batch.number_errors > 10:
                        print("Batch import stopped due to excessive errors.")
                        break

            # Report any failed article imports
            failed = articles_collection.batch.failed_objects
            if failed:
                print(f"Failed article imports for issue {issue_manifest}: {len(failed)}")
                for f_obj in failed[:3]:
                    print(f_obj)

            # ── LINK ARTICLES TO ISSUE ────────────────────────────────────────────
            # After all articles for this issue are inserted, add a reference from
            # the Issue object to each Article object via the "hasArticle" property.
            for article_uuid in article_uuids:
                issues_collection.data.reference_add(
                    from_uuid=issue_uuid,
                    from_property="hasArticle",
                    to=article_uuid,
                )
    client.close()