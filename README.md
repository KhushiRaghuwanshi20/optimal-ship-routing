   # Meridian: Optimal Ship Routing System

   Finds the shortest safe maritime route across the Arabian Sea using a
   custom A* search, avoiding coastline and storm zones.

   **Live demo:** (add your Streamlit link here)

   ## Features
   - Custom A* implementation (heapq priority queue, haversine heuristic)
   - Hard constraints (land, no-go zones) and soft constraints (risk-weighted storm cost)
   - Interactive Leaflet map via Folium with route, storm and detour comparison
   - Streamlit UI with live recomputation

   ## Tech stack
   Python, A* algorithm, Folium (Leaflet), Streamlit

   ## Run locally
   pip install -r requirements.txt
   streamlit run app.py

   ## How it works
   1. The sea is discretised into a 0.2° grid; each cell is free, blocked or risk-weighted.
   2. A* minimises f(n) = g(n) + h(n), where g is the risk-weighted distance travelled
      and h is the haversine distance to the goal (admissible, so the route is optimal).
   3. The route is drawn over a Leaflet map and compared with the no-storm route.

   ## Limitations
   Simplified coastline and simulated storm data; not live weather or AIS data.
