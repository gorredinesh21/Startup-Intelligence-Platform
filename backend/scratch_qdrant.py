import os
from qdrant_client import QdrantClient

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "qdrant_local_db"))
client = QdrantClient(path=db_path)

print("QdrantClient type:", type(client))
print("Available attributes/methods:")
for attr in dir(client):
    if not attr.startswith("_"):
        print(f" - {attr}")
