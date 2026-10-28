"""
app.py - Streamlit front-end ("Meridian").
Run:  streamlit run app.py
"""
import streamlit as st
from streamlit_folium import st_folium

from mapview import build_map
from router import OceanGrid, astar

st.set_page_config(page_title="Meridian | Optimal Ship Routing", page_icon="⚓",
                   layout="wide", initial_sidebar_state="collapsed")

PORTS = {
    "Mumbai": (18.9, 72.4),
    "Goa": (15.4, 73.4),
    "Mangalore": (12.9, 74.4),
    "Kochi": (9.9, 75.9),
    "Mid Arabian Sea": (15.0, 65.0),
    "Southern Arabian Sea": (6.0, 70.0),
}

# ---------------------------------------------------------------- styling --
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap');

html, body, [data-testid="stAppViewContainer"] { background:#F5F2EA; font-family:'Inter',sans-serif; }
[data-testid="stHeader"], #MainMenu, footer, [data-testid="stToolbar"] { display:none !important; }
.block-container { padding:2rem 3rem 2rem 3rem; max-width:1500px; }

/* hero */
.eyebrow { font:600 12px 'Inter'; letter-spacing:.22em; color:#0E7C86; text-transform:uppercase; }
.hero h1 { font:700 3.1rem/1.05 'Fraunces',serif; color:#0B2545; margin:.35rem 0 .6rem 0; letter-spacing:-.02em; }
.hero h1 em { color:#0E7C86; font-style:italic; }
.hero p { color:#4A5A72; max-width:640px; font-size:1.02rem; margin:0 0 1.4rem 0; }
.chips span { display:inline-block; font:500 12px 'Inter'; color:#0B2545; background:#fff;
  border:1px solid #E3DED0; padding:5px 12px; border-radius:999px; margin-right:8px; }

/* control panel */
.st-key-controls { background:#fff; border:1px solid #E7E2D4; border-radius:20px; padding:1.4rem 1.4rem 1rem 1.4rem;
  box-shadow:0 10px 30px rgba(11,37,69,.06); }
.panel-title { font:600 11px 'Inter'; letter-spacing:.18em; text-transform:uppercase; color:#8A93A6; margin:.2rem 0 .6rem 0; }
.st-key-controls label p { font-weight:500; color:#0B2545; }
hr.soft { border:none; border-top:1px dashed #E3DED0; margin:1rem 0; }

/* metric cards */
.cards { display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:14px; }
.card { background:#fff; border:1px solid #E7E2D4; border-radius:16px; padding:14px 18px;
  box-shadow:0 6px 18px rgba(11,37,69,.05); }
.card .k { font:600 10.5px 'Inter'; letter-spacing:.16em; text-transform:uppercase; color:#8A93A6; }
.card .v { font:700 1.85rem/1.15 'Fraunces',serif; color:#0B2545; margin-top:4px; }
.card .v small { font:500 .85rem 'Inter'; color:#6B7A90; margin-left:4px; }
.card.warn .v { color:#E4572E; }
.card.ok .v { color:#1B9E5A; }

/* map card */
.st-key-mapcard { border-radius:20px; overflow:hidden; border:1px solid #E7E2D4;
  box-shadow:0 14px 40px rgba(11,37,69,.10); background:#fff; }
.st-key-mapcard iframe { border-radius:20px; display:block; }
.legend { display:flex; gap:20px; font:500 12.5px 'Inter'; color:#4A5A72; margin:12px 4px 0 4px; flex-wrap:wrap; }
.legend i { display:inline-block; width:22px; height:0; border-top:4px solid; vertical-align:middle; margin-right:7px; }
.note { color:#8A93A6; font-size:12px; margin-top:10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="eyebrow">Maritime pathfinding</div>
  <h1>Chart the <em>safest</em> passage.</h1>
  <p>A custom A* search plots the shortest safe route across the Arabian Sea, keeping clear of the coast
  and steering around hazardous weather in real time.</p>
  <div class="chips"><span>A* search</span><span>Haversine distance</span><span>Leaflet map</span><span>Risk-weighted cost</span></div>
</div>
""", unsafe_allow_html=True)


# ----------------------------------------------------------------- logic --
@st.cache_data(show_spinner=False)
def plan(start, goal, storm):
    """storm is a hashable tuple (lat, lon, radius_nm, block, penalty) or None."""
    storms = []
    if storm:
        lat, lon, rad, block, pen = storm
        storms = [dict(lat=lat, lon=lon, radius_nm=rad, block=block, penalty=pen)]
    try:
        route = astar(OceanGrid(storms=storms), PORTS[start], PORTS[goal])
        base = astar(OceanGrid(), PORTS[start], PORTS[goal])   # same trip, no storm
    except ValueError:
        return None, None
    return route, base


def fmt_hours(h):
    return f"{int(h // 24)} d {int(h % 24)} h" if h >= 24 else f"{h:.1f} h"


# ---------------------------------------------------------------- layout --
left, right = st.columns([1, 2.7], gap="large")

with left:
    with st.container(key="controls"):
        st.markdown('<div class="panel-title">Voyage</div>', unsafe_allow_html=True)
        start = st.selectbox("Departure", list(PORTS), index=0)
        goal = st.selectbox("Destination", list(PORTS), index=3)
        speed = st.slider("Cruising speed (knots)", 5, 30, 14)

        st.markdown('<hr class="soft"><div class="panel-title">Weather hazard</div>',
                    unsafe_allow_html=True)
        use_storm = st.toggle("Storm system", value=True)
        storm = None
        if use_storm:
            s_lat = st.slider("Latitude", 5.0, 21.0, 13.0, 0.5)
            s_lon = st.slider("Longitude", 60.0, 80.0, 73.0, 0.5)
            s_rad = st.slider("Radius (nm)", 30, 400, 150, 10)
            mode = st.radio("Treat storm as", ["High-risk water", "No-go zone"], horizontal=True)
            s_pen = st.slider("Risk multiplier", 1.5, 10.0, 4.0, 0.5,
                              disabled=(mode == "No-go zone"))
            storm = (s_lat, s_lon, s_rad, mode == "No-go zone", s_pen)

with right:
    if start == goal:
        st.info("Pick two different locations to plan a voyage.")
    else:
        route, base = plan(start, goal, storm)
        if route is None:
            st.warning("The departure or destination is inside a blocked zone. "
                       "Move the storm or choose another location.")
        else:
            detour = route["distance_nm"] - base["distance_nm"]
            pct = 100 * detour / base["distance_nm"] if base["distance_nm"] else 0
            if storm and detour > 1:
                detour_card = f'<div class="card warn"><div class="k">Storm detour</div><div class="v">+{detour:.0f}<small>nm · +{pct:.0f}%</small></div></div>'
            else:
                detour_card = '<div class="card ok"><div class="k">Storm detour</div><div class="v">None<small>direct track</small></div></div>'

            st.markdown(f"""
            <div class="cards">
              <div class="card"><div class="k">Distance</div><div class="v">{route['distance_nm']:.0f}<small>nm</small></div></div>
              <div class="card"><div class="k">Transit time</div><div class="v">{fmt_hours(route['distance_nm']/speed)}</div></div>
              {detour_card}
              <div class="card"><div class="k">Nodes explored</div><div class="v">{route['expanded']:,}</div></div>
            </div>""", unsafe_allow_html=True)

            storm_dict = None
            if storm:
                storm_dict = dict(lat=storm[0], lon=storm[1], radius_nm=storm[2],
                                  block=storm[3], penalty=storm[4])
            with st.container(key="mapcard"):
                st_folium(build_map(route, base, storm_dict, start, goal),
                          height=600, use_container_width=True,
                          returned_objects=[], key="map")

            st.markdown("""
            <div class="legend">
              <span><i style="border-color:#0E7C86"></i>Optimal route</span>
              <span><i style="border-color:#8A93A6;border-top-style:dashed"></i>Direct route (no storm)</span>
              <span><i style="border-color:#E4572E;border-top-style:dashed"></i>Storm zone</span>
            </div>
            <div class="note">Prototype: simplified coastline and simulated storm data, not live weather or AIS.</div>
            """, unsafe_allow_html=True)
