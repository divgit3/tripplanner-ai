from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class Place(BaseModel):
    source: str
    source_id: str
    name: str
    city: str

    lat: float
    lon: float

    category: Optional[str] = None
    subcategories: List[str] = Field(default_factory=list)

    address: Optional[str] = None
    website: Optional[str] = None
    phone: Optional[str] = None

    wikipedia_title: Optional[str] = None
    wikipedia_summary: Optional[str] = None

    yelp_rating: Optional[float] = None
    yelp_review_count: Optional[int] = None
    yelp_review_summary: Optional[str] = None

    tags: Dict[str, str] = Field(default_factory=dict)