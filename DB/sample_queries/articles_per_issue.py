import weaviate
from weaviate.classes.query import Filter, QueryReference

with weaviate.connect_to_local() as client:
    issues = client.collections.use("Issue")

    response = issues.query.fetch_objects(
        filters=(
            Filter.by_property("publication_year").equal(1979)
            & Filter.by_property("issue_number").equal(1)
        ),
        return_references=[
            QueryReference(
                link_on="hasArticle",
                return_properties=["title", "author", "topic", "WEC_category", "start_page", "end_page", "manifest"],
            )
        ],
    )

    for issue in response.objects:
        print(f"Issue: {issue.properties}")
        if issue.references and "hasArticle" in issue.references:
            for article in issue.references["hasArticle"].objects:
                print(f"  Article: {article.properties}")