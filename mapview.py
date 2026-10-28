"""
mapview.py - builds the interactive Leaflet map (through Folium).
Kept separate from app.py so the map code can be tested without Streamlit.
"""
import math

import folium
from folium.plugins import AntPath

NAVY, TEAL, CORAL, GREY = "#0B2545", "#0E7C86", "#E4572E", "#8A93A6"

# Free basemaps that need no API key. The first one is shown by default;
# the others can be switched from the layer button on the map.
ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services"
BASEMAPS = [
    ("Street map", f"{ESRI}/World_Street_Map/MapServer/tile/{{z}}/{{y}}/{{x}}",
     "Tiles &copy; Esri"),
    ("Satellite", f"{ESRI}/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}",
     "Tiles &copy; Esri"),
]


def _merc_y(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _fit_zoom(lat_min, lat_max, lon_min, lon_max, width=950, height=600):
    """Largest whole zoom level at which the bounds fit in the map view.
    (Done in Python because fit_bounds can fire before the map has a size.)"""
    lon_span = max(lon_max - lon_min, 0.5)
    y_span = max(_merc_y(lat_max) - _merc_y(lat_min), 0.01)
    z_lon = math.log2(width * 360 / (256 * lon_span))
    z_lat = math.log2(height * 2 * math.pi / (256 * y_span))
    return max(3, min(9, math.floor(min(z_lon, z_lat) - 0.3)))


def _pin(label, color):
    """A custom HTML marker: coloured dot + floating label.
    Inline styles are required because the map renders inside an iframe,
    so the page's CSS does not reach it."""
    html = (
        '<div style="display:flex;align-items:center;gap:8px;'
        'transform:translate(-10px,-10px);white-space:nowrap">'
        f'<div style="width:20px;height:20px;border-radius:50%;background:{color};'
        'border:3px solid #fff;box-shadow:0 2px 8px rgba(0,0,0,.35)"></div>'
        '<div style="font:600 12px Inter,system-ui,sans-serif;color:#0B2545;'
        'background:#fff;padding:4px 10px;border-radius:999px;'
        f'box-shadow:0 2px 10px rgba(0,0,0,.2)">{label}</div></div>'
    )
    return folium.DivIcon(icon_size=(0, 0), icon_anchor=(0, 0), html=html)


def build_map(route, baseline, storm, start_name, goal_name):
    path = route["path"]
    pts = list(path)

    if storm:
        r_deg = storm["radius_nm"] / 60.0
        pts += [(storm["lat"] - r_deg, storm["lon"] - r_deg),
                (storm["lat"] + r_deg, storm["lon"] + r_deg)]

    lat_min, lat_max = min(p[0] for p in pts), max(p[0] for p in pts)
    lon_min, lon_max = min(p[1] for p in pts), max(p[1] for p in pts)
    centre = ((lat_min + lat_max) / 2, (lon_min + lon_max) / 2)
    zoom = _fit_zoom(lat_min, lat_max, lon_min, lon_max)

    m = folium.Map(location=centre, zoom_start=zoom, tiles=None,
                   control_scale=True, prefer_canvas=True,
                   min_zoom=3, max_zoom=12)

    for i, (name, url, attr) in enumerate(BASEMAPS):
        folium.TileLayer(tiles=url, attr=attr, name=name, show=(i == 0)).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(m)

    if storm:
        folium.Circle([storm["lat"], storm["lon"]],
                      radius=storm["radius_nm"] * 1852, color=CORAL,
                      weight=2, dash_array="4 6", fill=True, fill_color=CORAL,
                      fill_opacity=0.18,
                      tooltip="Storm zone (no-go)" if storm["block"]
                      else f"Storm zone (x{storm['penalty']:.1f} risk cost)"
                      ).add_to(m)
        folium.Marker([storm["lat"], storm["lon"]], icon=folium.DivIcon(
            icon_size=(0, 0), icon_anchor=(0, 0),
            html='<div style="transform:translate(-50px,-10px);width:100px;'
                 'text-align:center;font:700 11px Inter,system-ui,sans-serif;'
                 f'letter-spacing:.12em;color:{CORAL}">STORM</div>')).add_to(m)

        # dashed grey line = what the ship would sail with no storm
        folium.PolyLine(baseline["path"], color=GREY, weight=3, opacity=0.9,
                        dash_array="6 8",
                        tooltip="Direct route (no storm)").add_to(m)

    # white "casing" under the route makes it pop against the map tiles
    folium.PolyLine(path, color="#FFFFFF", weight=10, opacity=0.95).add_to(m)
    AntPath(path, color=TEAL, pulse_color="#FFFFFF", weight=5, delay=900,
            dash_array=[14, 26], opacity=1,
            tooltip=f"Optimal route - {route['distance_nm']:.0f} nm").add_to(m)

    folium.Marker(path[0], icon=_pin(start_name, "#1B9E5A")).add_to(m)
    folium.Marker(path[-1], icon=_pin(goal_name, NAVY)).add_to(m)

    folium.LayerControl(position="topright", collapsed=True).add_to(m)
    return m
