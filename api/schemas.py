from typing import List, Optional
from pydantic import BaseModel, Field


class PlannerRequest(BaseModel):
    city: str
    query: str
    num_days: int = 1
    pace: str = "moderate"
    top_k: int = 12


class ItineraryStop(BaseModel):
    name: str
    category: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    why_visit: Optional[str] = None
    time_block: Optional[str] = None


class ItineraryDay(BaseModel):
    day: int
    theme: Optional[str] = None
    stops: List[ItineraryStop]


class PlannerResponse(BaseModel):
    city: str
    query: str
    num_days: int
    pace: str
    itinerary: List[ItineraryDay]



class ItineraryRequest(BaseModel):
    city: str
    query: str
    duration: str = Field(default="1_day")
    pace: str = Field(default="balanced")
    top_k: int = Field(default=8, ge=3, le=20)



class ItineraryResponse(BaseModel):
    title: str
    city: str
    theme: str
    duration: str
    pace: str
    stops: List[ItineraryStop]
    tips: List[str]



class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    city: Optional[str] = "Tampa"
    top_k: int = Field(default=10, ge=1, le=50)



class SearchResultItem(BaseModel):
    name: str
    category: Optional[str] = None
    score: float
    address: Optional[str] = None
    city: Optional[str] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    categories: List[str]
    intents: List[str]
    results: List[SearchResultItem]


class DebugCounts(BaseModel):
    raw_results: int
    deduped_results: int
    returned_results: int


class SearchDebugResponse(BaseModel):
    query: str
    city: str
    categories: List[str]
    intents: List[str]
    counts: DebugCounts
    results: List[SearchResultItem]



class RagAskRequest(BaseModel):
    city: str
    query: str
    top_k: int = 5


class RetrievedPlace(BaseModel):
    name: str
    category: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    wikipedia_summary: Optional[str] = None
    yelp_review_summary: Optional[str] = None
    score: Optional[float] = None
    source: Optional[str] = None
    source_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None


class RagAskResponse(BaseModel):
    city: str
    query: str
    answer: str
    retrieved_places: List[RetrievedPlace]
    grounded: bool = True