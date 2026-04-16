import weaviate
from weaviate.classes.config import Property, DataType, ReferenceProperty, Configure

with weaviate.connect_to_local() as client:
    client.collections.delete_all()