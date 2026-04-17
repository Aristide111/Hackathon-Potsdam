import weaviate
from weaviate.classes.init import Auth
import uuid
from weaviate.classes.query import Filter, QueryReference
import os, json, csv
from dotenv import load_dotenv

# Load the environmental variable 
load_dotenv()
WSW_FOLDER = os.environ['WSW_FOLDER']
# Connect to Weaviate

with weaviate.connect_to_local() as client:
    issue_folder_list = [
    name for name in os.listdir(WSW_FOLDER)
    if os.path.isdir(os.path.join(WSW_FOLDER, name))
    ]
    issues = client.collections.use("Issue")
    articles_collection = client.collections.get("Article")
    pages_collection = client.collections.get("Page")
    for issue_folder in issue_folder_list:
        issue_year = issue_folder.split("_")[0]
        issue_n = issue_folder.split("_")[1]
        folder_path = os.path.join(WSW_FOLDER,issue_folder)
        page_list = [
        name for name in os.listdir(folder_path)
        if os.path.isfile(os.path.join(folder_path, name))
        ]
        # get information on the articles in the issue to match pages to articles
        response = issues.query.fetch_objects(
        filters=(
            Filter.by_property("publication_year").equal(issue_year)
            & Filter.by_property("issue_number").equal(issue_n)
        ),
        return_references=[
            QueryReference(
                link_on="hasArticle",
                return_properties=["start_page", "end_page"],
            )
        ],
        )
        # create a list of articles consisting of ids for linking and starting and ending pages
        articles = []
        for issue in response.objects:
            if issue.references and "hasArticle" in issue.references:
                for article in issue.references["hasArticle"].objects:
                    article_dict = article.properties
                    article_dict.update({"article_uuid":str(article.uuid)})
                    if article_dict["start_page"]:
                        articles.append(article_dict)
        # create entries for pages 
        pages = {}
        for page in page_list:
            page_uuid = str(uuid.uuid4())
            page_n = int(page.split("_")[1].split(".")[0])
            txt_path = os.path.join(WSW_FOLDER,issue_folder,page)
            print(page_n)
            page_props = {
            "page_number": page_n,
            "text_path": txt_path
            }
            pages_collection.data.insert(
            properties=page_props,
            uuid=page_uuid,
            )
            pages.update({page_n : page_uuid})
        # add references from articles to pages    
        for article in articles:
                article_uuid = article["article_uuid"]
                # ADD ERROR HANDLING FOR MISMATCH IN PAGES
                for page_n in range(article["start_page"],article["end_page"]):
                    page_uuid = pages[page_n]
                    articles_collection.data.reference_add(
                        from_uuid=article_uuid,
                        from_property="hasPage",
                        to=page_uuid,
                    )
                    print(f"linked page {page_n} from {issue_folder} to article {article_uuid}")    
