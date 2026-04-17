import weaviate

with weaviate.connect_to_local() as client:
    issues = client.collections.use("Issue")

    response = issues.query.fetch_objects()

    for issue in response.objects:
        print(issue.properties)