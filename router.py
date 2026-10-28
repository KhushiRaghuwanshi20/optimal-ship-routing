"""
router.py - core logic: ocean grid + custom A* search (no external libraries).
"""
import heapq
import itertools
import math

EARTH_RADIUS_NM = 3440.065  # Earth radius in nautical miles

# Simplified west coast of India: (latitude, longitude) of the coastline.
# Anything EAST of this line (and north of 8N) is treated as land.
COAST = [(8.0, 77.5), (9.9, 76.2), (12.9, 74.8), (15.5, 73.8),
         (18.0, 73.0), (19.0, 72.8), (21.0, 72.6)]


def haversine_nm(a, b):
    """Great-circle distance in nautical miles between two (lat, lon) points."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = (math.sin((lat2 - lat1) / 2) ** 2
         + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_NM * math.asin(math.sqrt(h))


def coast_lon(lat):
    """Linearly interpolate the coastline longitude at a given latitude."""
    if lat <= COAST[0][0]:
        return COAST[0][1]
    for (la1, lo1), (la2, lo2) in zip(COAST, COAST[1:]):
        if la1 <= lat <= la2:
            return lo1 + (lo2 - lo1) * (lat - la1) / (la2 - la1)
    return COAST[-1][1]


def is_land(lat, lon, margin=0.15):
    """Land test with a safety margin (degrees) so ships keep off the coast."""
    return lat >= 8.0 and lon > coast_lon(lat) - margin


class OceanGrid:
    """Discretises the sea into cells. Each cell is blocked (land / no-go
    storm) or has a cost multiplier (>=1) for risky water."""

    def __init__(self, lat_min=5, lat_max=21, lon_min=60, lon_max=80,
                 res=0.2, storms=None):
        self.lat_min, self.lon_min, self.res = lat_min, lon_min, res
        self.rows = int(round((lat_max - lat_min) / res)) + 1
        self.cols = int(round((lon_max - lon_min) / res)) + 1
        self.blocked = [[False] * self.cols for _ in range(self.rows)]
        self.mult = [[1.0] * self.cols for _ in range(self.rows)]
        for i in range(self.rows):
            for j in range(self.cols):
                p = self.to_latlon((i, j))
                if is_land(*p):
                    self.blocked[i][j] = True
                    continue
                for s in (storms or []):
                    if haversine_nm(p, (s["lat"], s["lon"])) <= s["radius_nm"]:
                        if s["block"]:
                            self.blocked[i][j] = True
                        else:
                            self.mult[i][j] = max(self.mult[i][j], s["penalty"])

    def to_cell(self, lat, lon):
        return (round((lat - self.lat_min) / self.res),
                round((lon - self.lon_min) / self.res))

    def to_latlon(self, cell):
        return (self.lat_min + cell[0] * self.res,
                self.lon_min + cell[1] * self.res)

    def is_blocked(self, cell):
        i, j = cell
        if not (0 <= i < self.rows and 0 <= j < self.cols):
            return True
        return self.blocked[i][j]


MOVES = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


def astar(grid, start, goal):
    """A* on the grid. f(n) = g(n) + h(n)
       g = risk-weighted distance travelled so far (nm)
       h = straight-line (haversine) distance to goal (admissible, since
           real cost can never be less than the straight line because
           multipliers are >= 1)."""
    s, g = grid.to_cell(*start), grid.to_cell(*goal)
    if grid.is_blocked(s) or grid.is_blocked(g):
        raise ValueError("Start or goal is on land / inside a blocked zone.")

    goal_pt = grid.to_latlon(g)
    counter = itertools.count()          # tie-breaker for the heap
    open_heap = [(haversine_nm(grid.to_latlon(s), goal_pt), next(counter), s)]
    g_score, parent, closed = {s: 0.0}, {s: None}, set()
    expanded = 0

    while open_heap:
        _, _, cur = heapq.heappop(open_heap)
        if cur in closed:
            continue
        closed.add(cur)
        expanded += 1

        if cur == g:                     # goal reached -> rebuild path
            cells = []
            while cur is not None:
                cells.append(cur)
                cur = parent[cur]
            cells.reverse()
            path = [grid.to_latlon(c) for c in cells]
            dist = sum(haversine_nm(a, b) for a, b in zip(path, path[1:]))
            return {"path": path, "distance_nm": dist,
                    "cost": g_score[g], "expanded": expanded}

        for di, dj in MOVES:
            nb = (cur[0] + di, cur[1] + dj)
            if grid.is_blocked(nb):
                continue
            # no cutting corners across land on diagonal moves
            if di and dj and (grid.is_blocked((cur[0] + di, cur[1]))
                              or grid.is_blocked((cur[0], cur[1] + dj))):
                continue
            step = haversine_nm(grid.to_latlon(cur), grid.to_latlon(nb))
            step *= (grid.mult[cur[0]][cur[1]] + grid.mult[nb[0]][nb[1]]) / 2
            new_g = g_score[cur] + step
            if nb not in g_score or new_g < g_score[nb]:
                g_score[nb] = new_g
                parent[nb] = cur
                f = new_g + haversine_nm(grid.to_latlon(nb), goal_pt)
                heapq.heappush(open_heap, (f, next(counter), nb))
    return None  # no route exists
