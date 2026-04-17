import weaviate
from weaviate.classes.config import Property, DataType, ReferenceProperty, Configure

with weaviate.connect_to_local() as client:

    # Bottom level: Paragraph
    client.collections.create(
        name="Sentence",
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="sentence_number", data_type=DataType.INT),
        ],
    )
    client.collections.create(
        name="Caption",
        properties=[
            Property(name="caption_text", data_type=DataType.TEXT),
            Property(name="bbox_x1", data_type=DataType.INT),
            Property(name="bbox_x2", data_type=DataType.INT),
            Property(name="bbox_y1", data_type=DataType.INT),
            Property(name="bbox_y2", data_type=DataType.INT),
        ]
    )
    # Image
    client.collections.create(
        name="Image",
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="tag", data_type=DataType.TEXT),
            Property(name="topic", data_type=DataType.TEXT),
            Property(name="image_path", data_type=DataType.TEXT),
            Property(name="bbox_x1", data_type=DataType.INT),
            Property(name="bbox_x2", data_type=DataType.INT),
            Property(name="bbox_y1", data_type=DataType.INT),
            Property(name="bbox_y2", data_type=DataType.INT),
            Property(name="image_height", data_type=DataType.INT),
            Property(name="image_width", data_type=DataType.INT),
            Property(name="dpi", data_type=DataType.INT),
        ],
        references=[
            ReferenceProperty(name="hasCaption", target_collection="Caption"),
        ]
    )

    # Page references Paragraph and Image
    client.collections.create(
        name="Page",
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="page_number", data_type=DataType.INT),
            Property(name="image_path", data_type=DataType.TEXT),
            Property(name="text_path", data_type=DataType.TEXT),
            Property(name="page_height", data_type=DataType.INT),
            Property(name="page_width", data_type=DataType.INT),

        ],
        references=[
            ReferenceProperty(name="hasImage", target_collection="Image"),
            ReferenceProperty(name="hasSentence", target_collection="Sentence"),
        ],
    )
    # Table of Contents
    client.collections.create(
        name="Content",
        properties=[
            Property(name="page_number", data_type=DataType.INT),
        ],
        references=[
            ReferenceProperty(name="isPage", target_collection="Page"),
        ],
    )

    # Covers
    client.collections.create(
        name="Cover",
        properties=[
            Property(name="page_number", data_type=DataType.INT),
        ],
        references=[
            ReferenceProperty(name="isPage", target_collection="Page"),
        ], 
    )
    
    # Article references Page
    client.collections.create(
        name="Article",
        vector_config=Configure.Vectors.self_provided(),
        properties=[
            Property(name="title", data_type=DataType.TEXT),
            Property(name="manifest", data_type=DataType.TEXT),
            Property(name="author", data_type=DataType.TEXT),
            Property(name="start_page", data_type=DataType.INT),
            Property(name="end_page", data_type=DataType.INT),
            Property(name="topic", data_type=DataType.TEXT),
            Property(name="WEC_category", data_type=DataType.TEXT),
        ],
        references=[
            ReferenceProperty(name="hasPage", target_collection="Page"),
        ],
    )

    # Issue references Article
    client.collections.create(
        name="Issue",
        properties=[
            Property(name="issue_number", data_type=DataType.INT),
            Property(name="publication_year", data_type=DataType.INT),
            Property(name="pdf_path", data_type=DataType.TEXT),
            Property(name="pages", data_type=DataType.INT),
        ],
        references=[
            ReferenceProperty(name="hasArticle", target_collection="Article"),
            ReferenceProperty(name="hasPage", target_collection="Page"),
            ReferenceProperty(name="hasCover", target_collection="Cover"),
            ReferenceProperty(name="hasContent", target_collection="Content"),
        ],
    )

    # Periodical references Issue
    client.collections.create(
        name="Periodical",
        properties=[
            Property(name="title", data_type=DataType.TEXT),
            Property(name="publisher", data_type=DataType.TEXT),
            Property(name="access_url", data_type=DataType.TEXT),
        ],
        references=[
            ReferenceProperty(name="hasIssue", target_collection="Issue"),
        ],
    )