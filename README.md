# TripPlanner-AI

**AI-powered travel planning with semantic attraction search, day-wise itinerary generation, and interactive map visualization.**

TripPlanner-AI helps users discover attractions in a city based on travel intent, then generates a structured itinerary across one or more days. Instead of relying only on keyword matching, it uses semantic search and vector embeddings to retrieve places that better match what the user is actually looking for.

## Features

- Semantic attraction search by city and travel intent
- Intent-aware recommendations using embeddings and vector search
- Day-wise itinerary generation based on trip duration and pace
- Interactive map visualization of suggested stops and routes
- Multi-day trip planning with grouped results
- FastAPI backend for search and itinerary endpoints
- Streamlit frontend for interactive exploration

## Current Scope (V1)

This version focuses on a working end-to-end prototype that demonstrates:

- attraction discovery from processed place data
- semantic search over travel-related queries
- itinerary generation for 1-day to multi-day trips
- map-based trip visualization
- modular backend and service-based architecture

## Example Queries

- art and culture attraction
- family-friendly place with animals
- historic museum with architecture
- quiet outdoor nature walk
- scenic waterfront attractions
- short tourist visit downtown

## Tech Stack

- **Frontend:** Streamlit, PyDeck
- **Backend:** FastAPI
- **Language:** Python
- **Embeddings:** OpenAI Embeddings
- **Vector Store:** Qdrant
- **Data Sources (current):** OpenStreetMap, Wikipedia-enriched place metadata

## Architecture Overview

The application follows a modular layered design:

1. **Data ingestion** collects city/place data.
2. **Data processing and enrichment** cleans and enriches places with useful metadata.
3. **Embedding pipeline** converts place descriptions into vector embeddings.
4. **Semantic retrieval** uses Qdrant to return places relevant to user intent.
5. **Planner service** organizes results into a day-wise itinerary based on duration and pace.
6. **UI layer** displays recommendations and route maps interactively.

## Project Structure

```text
tripplanner-ai/
├── api/
│   ├── main.py
│   ├── schemas.py
│   └── routes/
│       ├── planner.py
│       ├── rag.py
│       └── search.py
├── data/
│   ├── clients/
│   ├── processors/
│   ├── schemas/
│   ├── raw/
│   └── processed/
├── pipelines/
│   ├── build_embeddings.py
│   └── enrich_wikipedia.py
├── retrieval/
├── search/
│   ├── query_interpreter.py
│   └── semantic_search.py
├── services/
│   ├── embedding_service.py
│   ├── llm_service.py
│   ├── planner_service.py
│   ├── qdrant_service.py
│   ├── rag_service.py
│   └── wikipedia_service.py
├── tests/
├── ui/
│   └── app.py
└── utils/
