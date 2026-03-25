import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
import html
import math

API_BASE_URL = "http://127.0.0.1:8001"
SEARCH_ENDPOINT = f"{API_BASE_URL}/search"

def build_fallback_summary(stop: dict) -> str:
    name = stop.get("name", "This place")
    category = (stop.get("category") or "place").lower()
    raw_slot = ((stop.get("slot") or stop.get("time_block") or "")).lower()

    slot_phrase_map = {
        "morning": "a good morning stop",
        "afternoon": "a nice afternoon stop",
        "evening": "a pleasant evening stop",
        "night": "an evening-friendly stop",
    }
    slot_phrase = slot_phrase_map.get(raw_slot, "a flexible stop")

    if category == "park":
        return f"{name} is {slot_phrase} if you want an outdoor break in your itinerary."
    elif category == "museum":
        return f"{name} is {slot_phrase} for adding culture and sightseeing to your trip."
    elif category in ["zoo", "aquarium"]:
        return f"{name} is {slot_phrase} for a family-friendly outing."
    elif category in ["beach", "waterfront", "pier"]:
        return f"{name} is {slot_phrase} if you want scenic waterfront views."
    else:
        return f"{name} is {slot_phrase} to include in your trip plan."



def render_stop_card(stop: dict, idx: int):
    name = stop.get("name", "Unknown place")
    if ";" in name:
        parts = [p.strip() for p in name.split(";")]
        name = parts[0] if parts else name

    raw_slot = ((stop.get("slot") or stop.get("time_block") or "")).lower()
    category_raw = (stop.get("category") or "place")
    duration = stop.get("estimated_duration_minutes")

    icon_map = {
        "morning": "🌅 Morning",
        "afternoon": "☀️ Afternoon",
        "evening": "🌇 Evening",
        "night": "🌙 Night",
    }
    slot_label = icon_map.get(raw_slot, "📍 Flexible")

    summary = stop.get("summary") or stop.get("wikipedia_summary") or ""
    summary = summary.strip() if isinstance(summary, str) else ""

    # if not summary:
    #     summary = build_fallback_summary(stop)

    if len(summary) > 180:
        summary = summary[:180].rstrip() + "..."

    duration_text = f"{duration} mins" if duration else "Flexible duration"
    category_text = category_raw.title()

    CATEGORY_ICON = {
        "museum": "🏛️",
        "park": "🌳",
        "zoo": "🦁",
        "beach": "🏖️"
    }

    caticon = CATEGORY_ICON.get(category_raw.lower(), "📍")

    with st.container(border=True):
        st.markdown(f"### {idx}. {caticon} {name}")
        st.markdown(f"**{slot_label} • {duration_text} **")
        if summary:
            st.write(summary)



def calculate_bearing(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = (
        math.cos(lat1) * math.sin(lat2)
        - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    )

    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def get_dynamic_zoom(df_map):
    lat_range = df_map["latitude"].max() - df_map["latitude"].min()
    lon_range = df_map["longitude"].max() - df_map["longitude"].min()
    max_range = max(lat_range, lon_range)

    if max_range < 0.02:
        return 13.5
    elif max_range < 0.05:
        return 12.5
    elif max_range < 0.1:
        return 11.5
    elif max_range < 0.2:
        return 10.5
    else:
        return 9.5


def call_search_api(query: str, city: str):
    payload = {
        "query": query,
        "city": city,
    }   
    response = requests.post(SEARCH_ENDPOINT, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()


def call_rag_api(query: str, city: str, top_k: int = 5):
    payload = {
        "city": city,
        "query": query,
        "top_k": top_k,
    }
    response = requests.post(
        f"{API_BASE_URL}/rag/ask",
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    return response.json()



def plan_itinerary(city: str, query: str, num_days: int, pace: str, top_k: int = 8):
    payload = {
        "city": city,
        "query": query,
        "num_days": num_days,
        "pace": pace,
        "top_k": top_k,
    }

    response = requests.post(
        f"{API_BASE_URL}/plan/itinerary",
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def generate_explanation(place: dict, query: str, categories: list, intents: list):
    name = place.get("name", "")
    score = place.get("score", 0)

    explanation = f"{name} is recommended because it matches your query"

    if intents:
        explanation += f" related to {', '.join(intents)}"

    if categories:
        explanation += f" and belongs to the {', '.join(categories)} category"

    if score is not None:
        explanation += f". It has a relevance score of {round(float(score), 2)}."
    else:
        explanation += "."

    return explanation


def render_result_card(place: dict, idx: int, query: str, categories: list, intents: list):
    name = place.get("name", "Unknown")
    category = place.get("category", "N/A")
    score = place.get("score")
    address = place.get("address", "N/A")
    city = place.get("city", "")
    source = place.get("source", "N/A")
    lat = place.get("lat")
    lon = place.get("lon")

    explanation = generate_explanation(place, query, categories, intents)

    with st.container(border=True):
        st.markdown(f"### {idx}. {name}")

        c1, c2, c3 = st.columns([1, 1, 2])

        with c1:
            st.write(f"**Category:** {category}")

        with c2:
            if score is not None:
                try:
                    st.write(f"**Score:** {float(score):.4f}")
                except Exception:
                    st.write(f"**Score:** {score}")
            else:
                st.write("**Score:** N/A")

        with c3:
            st.write(f"**Source:** {source}")

        st.write(f"**Address:** {address}")

        if city:
            st.write(f"**City:** {city}")

        if lat is not None and lon is not None:
            st.caption(f"📍 ({lat}, {lon})")

        st.info(f"💡 {explanation}")


def render_search_map(results: list[dict]):
    map_rows = []

    for place in results:
        lat = place.get("lat")
        lon = place.get("lon")

        if lat is not None and lon is not None:
            map_rows.append(
                {
                    "name": place.get("name", "Unknown"),
                    "category": place.get("category", "N/A"),
                    "score": place.get("score", 0),
                    "lat": lat,
                    "lon": lon,
                    "icon_data": {
                        "url": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
                        "width": 64,
                        "height": 64,
                        "anchorY": 64,
                    },
                }
            )

    if not map_rows:
        st.info("No mappable coordinates available for these results.")
        return

    df = pd.DataFrame(map_rows)

    center_lat = df["lat"].mean()
    center_lon = df["lon"].mean()

    icon_layer = pdk.Layer(
        "IconLayer",
        data=df,
        get_icon="icon_data",
        get_size=3,
        size_scale=4,
        get_position="[lon, lat]",
        pickable=True,
    )

    tooltip = {
        "html": "<b>{name}</b><br/>{category}<br/>Score: {score}",
        "style": {"backgroundColor": "steelblue", "color": "white"},
    }

    deck = pdk.Deck(
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=11,
            pitch=0,
        ),
        layers=[icon_layer],
        tooltip=tooltip,
    )

    st.pydeck_chart(deck)


def render_itinerary_map(days: list[dict], map_mode: str = "Overall Trip"):
    map_rows = []

    for day in days:
        day_num = day.get("day")

        for i, stop in enumerate(day.get("stops", []), start=1):
            lat = stop.get("lat")
            lon = stop.get("lon")

            if lat is not None and lon is not None:
                map_rows.append(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "day": day_num,
                        "stop_order": i,
                        "name": stop.get("name", "Unknown"),
                        "category": stop.get("category", "place"),
                        "slot": stop.get("slot", ""),
                        "label": f"Day {day_num} - Stop {i}: {stop.get('name', 'Unknown')}",
                        "icon": {
                            "url": "https://cdn-icons-png.flaticon.com/512/684/684908.png",
                            "width": 64,
                            "height": 64,
                            "anchorY": 64,
                        },
                    }
                )

    if not map_rows:
        st.info("No mappable itinerary stops available.")
        return

    df_map = pd.DataFrame(map_rows)

    st.markdown("### Map")

    day_colors = {
        1: [0, 200, 255],
        2: [255, 140, 0],
        3: [50, 205, 50],
        4: [255, 99, 132],
        5: [186, 85, 211],
        6: [255, 215, 0],
        7: [255, 255, 255],
    }

    paths = []

    for day_num in sorted(df_map["day"].dropna().unique()):
        day_df = df_map[df_map["day"] == day_num].sort_values("stop_order")
        coords = day_df[["longitude", "latitude"]].values.tolist()

        if len(coords) >= 2:
            paths.append(
                {
                    "day": int(day_num),
                    "path": coords,
                    "color": day_colors.get(int(day_num), [0, 200, 255]),
                }
            )

    path_layer = pdk.Layer(
        "PathLayer",
        data=paths,
        get_path="path",
        get_color="color",
        get_width=5,
        width_min_pixels=2,
        pickable=False,
    )

    icon_layer = pdk.Layer(
        "IconLayer",
        data=df_map,
        get_icon="icon",
        get_size=4,
        size_scale=8,
        get_position="[longitude, latitude]",
        pickable=True,
    )

    text_layer = pdk.Layer(
        "TextLayer",
        data=df_map,
        get_position="[longitude, latitude]",
        get_text="stop_order",
        get_size=14,
        get_color=[255, 255, 255],
        get_text_anchor="'middle'",
        get_alignment_baseline="'center'",
        get_pixel_offset=[0, -18],
    )

    tooltip = {
        "html": "<b>{label}</b>",
        "style": {"backgroundColor": "#1f2937", "color": "white"},
    }

    zoom_level = get_dynamic_zoom(df_map)

    view_state = pdk.ViewState(
        latitude=df_map["latitude"].mean(),
        longitude=df_map["longitude"].mean(),
        zoom=zoom_level,
        pitch=0,
    )

    layers = [icon_layer, text_layer]
    if paths:
        layers.insert(0, path_layer)

    st.pydeck_chart(
        pdk.Deck(
            layers=layers,
            initial_view_state=view_state,
            tooltip=tooltip,
        )
    )

    if map_mode == "Overall Trip":
        st.caption("Showing all itinerary stops across all days.")
    else:
        st.caption(f"Showing itinerary map for {map_mode}.")

    with st.expander("View detailed map stops"):
        df_labels = (
            df_map[["day", "stop_order", "name", "category", "slot", "label"]]
            .sort_values(["day", "stop_order"])
            .reset_index(drop=True)
        )
        st.dataframe(df_labels, use_container_width=True, hide_index=True)



def main():
    st.set_page_config(
        page_title="TripPlanner-AI",
        page_icon="🧭",
        layout="wide",
    )

    st.title("🧭 TripPlanner-AI")
    st.caption("AI-powered attraction discovery, Q&A, and itinerary generation")

    if "query_input" not in st.session_state:
        st.session_state.query_input = "art and culture attraction"
    if "city_input" not in st.session_state:
        st.session_state.city_input = "Tampa"
    if "pace" not in st.session_state:
        st.session_state.pace = "balanced"
    if "search_results" not in st.session_state:
        st.session_state.search_results = None
    if "ask_ai_answer" not in st.session_state:
        st.session_state.ask_ai_answer = None
    if "itinerary" not in st.session_state:
        st.session_state.itinerary = None

    def set_query(q: str):
        st.session_state.query_input = q

    with st.sidebar:
        st.header("Search")

        city = st.text_input("City", key="city_input")
        query = st.text_area("What are you looking for?", key="query_input", height=100)

        st.markdown("**Try examples**")
        col1, col2 = st.columns(2)

        with col1:
            st.button(
                "Art & culture",
                on_click=set_query,
                args=("art and culture attraction",),
            )
            st.button(
                "Family friendly",
                on_click=set_query,
                args=("family friendly attractions",),
            )

        with col2:
            st.button(
                "Scenic waterfront",
                on_click=set_query,
                args=("scenic waterfront attractions",),
            )
            st.button(
                "Relaxing weekend",
                on_click=set_query,
                args=("relaxing weekend places",),
            )

        st.markdown("---")
        st.markdown("### Trip Planning")

        num_days = st.slider("Number of days", min_value=1, max_value=7, value=1)

        st.selectbox(
            "Pace",
            options=["relaxed", "balanced", "packed"],
            key="pace",
        )

        search_button = st.button("🔎 Search Attractions", use_container_width=True)
        ask_button = st.button("💬 Ask AI", use_container_width=True)
        plan_button = st.button("🗓️ Generate Itinerary", use_container_width=True)

    if search_button:
        with st.spinner("Searching attractions..."):
            try:
                results = call_search_api(
                    query=st.session_state.query_input,
                    city=st.session_state.city_input,
                )
                st.session_state.search_results = results
                st.session_state.ask_ai_answer = None
                st.session_state.itinerary = None
            except Exception as e:
                st.error(f"Failed to search attractions: {e}")
                st.session_state.search_results = None

    if ask_button:
        with st.spinner("Asking AI..."):
            try:
                ai_result = call_rag_api(
                    query=st.session_state.query_input,
                    city=st.session_state.city_input,
                    top_k=5,
                )
                st.session_state.ask_ai_answer = ai_result
            except Exception as e:
                st.error(f"Failed to get AI answer: {e}")
                st.session_state.ask_ai_answer = None

    if plan_button:
        with st.spinner("Generating itinerary..."):
            try:
                itinerary_result = plan_itinerary(
                    city=st.session_state.city_input,
                    query=st.session_state.query_input,
                    num_days=num_days,
                    pace=st.session_state.pace,
                    top_k=20,
                )
                st.session_state.itinerary = itinerary_result
                st.session_state.ask_ai_answer = None
            except Exception as e:
                st.error(f"Failed to generate itinerary: {e}")
                st.session_state.itinerary = None

    if st.session_state.search_results:
        results_payload = st.session_state.search_results

        st.markdown("---")
        st.subheader("🔎 Search Results")

        counts = results_payload.get("counts", {})
        if counts:
            c1, c2, c3 = st.columns(3)
            c1.metric("Raw Results", counts.get("raw_results", 0))
            c2.metric("Deduped Results", counts.get("deduped_results", 0))
            c3.metric("Returned Results", counts.get("returned_results", 0))

        inferred_categories = results_payload.get("categories", [])
        inferred_intents = results_payload.get("intents", [])

        meta_cols = st.columns(2)
        with meta_cols[0]:
            if inferred_categories:
                st.write("**Inferred categories:**", ", ".join(inferred_categories))
        with meta_cols[1]:
            if inferred_intents:
                st.write("**Inferred intents:**", ", ".join(inferred_intents))

        results = results_payload.get("results", [])

        if results:
            for i, place in enumerate(results, start=1):
                render_result_card(
                    place=place,
                    idx=i,
                    query=st.session_state.query_input,
                    categories=inferred_categories,
                    intents=inferred_intents,
                )

            st.markdown("### Map")
            render_search_map(results)
        else:
            st.info("No attractions found for this query.")

    if st.session_state.ask_ai_answer:
        st.markdown("---")
        st.subheader("💬 Ask AI")

        ai_payload = st.session_state.ask_ai_answer

        if isinstance(ai_payload, dict):
            answer = (
                ai_payload.get("answer")
                or ai_payload.get("response")
                or ai_payload.get("output")
                or ai_payload.get("text")
            )

            if answer:
                st.write(answer)
            else:
                st.json(ai_payload)
        else:
            st.write(ai_payload)

    if st.session_state.itinerary:
        result = st.session_state.itinerary

        st.markdown("---")
        st.subheader("🧭 Suggested Itinerary")

        if "days" in result:
            city_text = result.get("city", "")
            query_text = result.get("query", "")
            pace_text = result.get("pace", "")
            num_days_text = result.get("num_days", "")

            caption_parts = [
                part
                for part in [
                    city_text,
                    f"{num_days_text} day(s)" if num_days_text != "" else "",
                    pace_text,
                    query_text,
                ]
                if part
            ]
            if caption_parts:
                st.caption(" • ".join(caption_parts))

            TIME_BLOCK_ORDER = {
                "morning": 1,
                "afternoon": 2,
                "evening": 3,
                "night": 4,
            }

            for day in result["days"]:
                day_num = day.get("day")
                stops = day.get("stops", [])

                st.markdown(f"### Day {day_num}")

                if not stops:
                    st.caption("No stops available for this day.")
                    continue

                stops = sorted(
                    stops,
                    key=lambda x: TIME_BLOCK_ORDER.get(
                        ((x.get("slot") or x.get("time_block") or "")).lower(),
                        99,
                    ),
                )

                for i, stop in enumerate(stops, start=1):
                    render_stop_card(stop, i)

            st.markdown("### Trip Map")
            day_options = ["Overall Trip"] + [f"Day {day['day']}" for day in result["days"]]
            selected_day = st.selectbox("View map for", day_options, key="map_day_selector")

            if selected_day == "Overall Trip":
                days_for_map = result["days"]
            else:
                selected_day_num = int(selected_day.split(" ")[1])
                days_for_map = [day for day in result["days"] if day["day"] == selected_day_num]

            render_itinerary_map(days_for_map, map_mode=selected_day)
        else:
            st.json(result)


if __name__ == "__main__":
    main()