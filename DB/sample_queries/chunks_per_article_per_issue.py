import weaviate
from weaviate.classes.query import Filter, QueryReference

with weaviate.connect_to_local() as client:
    issues = client.collections.use("Issue")

    # Step 1: Fetch the issue with its articles and pages
    response = issues.query.fetch_objects(
        filters=(
            Filter.by_property("publication_year").equal(1979)
            & Filter.by_property("issue_number").equal(1)
        ),
        return_references=[
            QueryReference(
                link_on="hasArticle",
                return_properties=["title", "author", "topic", "start_page", "end_page"],
            )
        ],
    )

    result = {}

    for issue in response.objects:
        if not issue.references or "hasArticle" not in issue.references:
            continue

        for article in issue.references["hasArticle"].objects:
            article_title = article.properties.get("title", str(article.uuid))
            result[article_title] = []

            # Step 2: For each article, fetch its pages with paragraphs
            articles_col = client.collections.use("Article")
            article_detail = articles_col.query.fetch_objects(
                filters=Filter.by_id().equal(article.uuid),
                return_references=[
                    QueryReference(
                        link_on="hasPage",
                        return_properties=["page_number"],
                    )
                ],
            )

            for art in article_detail.objects:
                if not art.references or "hasPage" not in art.references:
                    continue

                for page in art.references["hasPage"].objects:
                    # Step 3: For each page, fetch its paragraphs
                    pages_col = client.collections.use("Page")
                    page_detail = pages_col.query.fetch_objects(
                        filters=Filter.by_id().equal(page.uuid),
                        return_references=[
                            QueryReference(
                                link_on="hasParagraph",
                                return_properties=["text", "paragraph_number"],
                            )
                        ],
                    )

                    for pg in page_detail.objects:
                        if not pg.references or "hasParagraph" not in pg.references:
                            continue
                        for para in pg.references["hasParagraph"].objects:
                            result[article_title].append(para.properties)

    # result is now a dict: { article_title: [paragraph_properties, ...] }
    import json
    print(json.dumps(result, indent=2, default=str))