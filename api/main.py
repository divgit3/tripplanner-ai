from fastapi import FastAPI
from api.routes.search import router as search_router
from api.routes.rag import router as rag_router
from api.routes import planner

app = FastAPI(
    title="TripPlanner AI API",
    version="0.1.0"
)

app.include_router(search_router)
app.include_router(rag_router)
app.include_router(planner.router)