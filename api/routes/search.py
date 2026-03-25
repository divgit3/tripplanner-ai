from fastapi import APIRouter, HTTPException
from api.schemas import SearchRequest, SearchResponse, SearchDebugResponse
from search.semantic_search import semantic_search

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/search", response_model=SearchResponse)
def search_places(request: SearchRequest):
    try:
        response = semantic_search(
            query=request.query,
            city=request.city or "Tampa",
            top_k=request.top_k,
            debug=False,
        )
        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/search/debug", response_model=SearchDebugResponse)
def search_places_debug(request: SearchRequest):
    try:
        response = semantic_search(
            query=request.query,
            city=request.city or "Tampa",
            top_k=request.top_k,
            debug=True,
        )
        return response
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug search failed: {str(e)}")