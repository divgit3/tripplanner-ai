import os
from typing import Optional, List
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "places_tampa"

client = QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT,
    api_key=QDRANT_API_KEY,
)


def recreate_collection(vector_size: int):
    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=vector_size,
            distance=Distance.COSINE,
        ),
    )


def upsert_points(points: list[PointStruct]):
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=points,
    )


def search_points(
    query_vector: list[float],
    limit: int = 5,
    categories: Optional[List[str]] = None,
):
    query_filter = None

    if categories:
        query_filter = Filter(
            should=[
                FieldCondition(
                    key="category",
                    match=MatchValue(value=category),
                )
                for category in categories
            ]
        )

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
    )
    return response.points