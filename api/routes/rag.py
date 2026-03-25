from fastapi import APIRouter, HTTPException
from api.schemas import RagAskRequest, RagAskResponse, RetrievedPlace
from services.rag_service import run_rag
import traceback

router = APIRouter()


@router.post("/rag/ask", response_model=RagAskResponse)
def rag_ask(req: RagAskRequest):
    try:
        result = run_rag(req.city, req.query, req.top_k)

        return RagAskResponse(
            city=result["city"],
            query=result["query"],
            answer=result["answer"],
            retrieved_places=[RetrievedPlace(**p) for p in result["retrieved_places"]],
            grounded=True,
        )

    except Exception as e:
        print("\n[RAG ROUTE ERROR]")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))