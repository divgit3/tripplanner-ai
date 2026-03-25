from fastapi import APIRouter
from pydantic import BaseModel
from services.planner_service import build_itinerary
from services.rag_service import semantic_search

router = APIRouter(prefix="/plan", tags=["planner"])


class PlannerRequest(BaseModel):
    city: str
    query: str
    num_days: int = 1
    pace: str = "balanced"
    top_k: int = 8


@router.post("/itinerary")
def plan_itinerary(req: PlannerRequest):
    search_output = semantic_search(
        query=req.query,
        city=req.city,
        top_k=req.top_k
    )

    results = search_output.get("results", [])

    days = build_itinerary(
        results=results,
        num_days=req.num_days,
        pace=req.pace
    )

    return {
        "city": req.city,
        "query": req.query,
        "num_days": req.num_days,
        "pace": req.pace,
        "days": days
    }