from pydantic import BaseModel


class SearchRequest(BaseModel):
    city: str
    query: str
    top_n: int = 5