#!/usr/bin/env python3
"""Draw a schematic map of Man City's completed 2026/27 Premier League matches.

Run: python _1_SM_Man_City.py
Requires matplotlib and numpy. The included CSV is the fixed, verified snapshot;
this script never silently fetches or includes future fixtures.
"""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Circle, Polygon, Rectangle
import numpy as np

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CSV = DATA / "man_city_epl_2026_27_asof_2026-11-26.csv"
AS_OF = date(2026, 11, 26)

# Schematic positions remain close to each club's real home ground. The extra
# separation around Manchester and London keeps markers and labels readable.
CLUBS = {
    "Man City":       (-2.20, 53.48, "MAN CITY", 1.00, (0.05, 0.20)),
    "Man United":     (-2.43, 53.33, "MAN UNITED", .66, (-0.13, -0.26)),
    "Liverpool":      (-3.13, 53.40, "LIVERPOOL", .78, (-0.13, -0.22)),
    "Sunderland":     (-1.39, 54.91, "SUNDERLAND", .59, (0.11, 0.03)),
    "Nottm Forest":   (-1.13, 52.94, "NOTTM FOREST", .57, (0.12, 0.11)),
    "Aston Villa":    (-1.88, 52.51, "ASTON VILLA", .63, (-0.13, -0.17)),
    "Coventry":       (-1.48, 52.40, "COVENTRY", .52, (0.12, -0.16)),
    "Ipswich":        ( 1.14, 52.05, "IPSWICH", .51, (0.10, 0.03)),
    "Fulham":         (-0.35, 51.57, "FULHAM", .54, (-0.27, -0.06)),
    "Crystal Palace": (-0.02, 51.29, "CRYSTAL PALACE", .54, (0.13, -0.13)),
    "Brighton":       (-0.14, 50.80, "BRIGHTON", .57, (0.11, -0.09)),
    "Bournemouth":    (-1.88, 50.73, "BOURNEMOUTH", .55, (0.12, -0.10)),
}

# Remaining 2026/27 Premier League clubs. These small nodes are intentionally
# unlabelled and have no routes until City completes a league fixture with them.
UNPLAYED = {
    "Arsenal": (-0.01, 51.66),
    "Brentford": (-0.47, 51.42),
    "Chelsea": (-0.28, 51.62),
    "Everton": (-3.08, 53.58),
    "Hull": (-0.37, 53.75),
    "Leeds": (-1.57, 53.78),
    "Newcastle": (-1.62, 55.04),
    "Tottenham": (0.19, 51.63),
}

# Stage 07 shifts three stations slightly to keep the new route grid clear.
SCHEMATIC_07 = {"Nottm Forest": (-1.32,52.94)}
UNPLAYED_07 = {**UNPLAYED, "Arsenal": (.06,51.66),
               "Chelsea": (-0.27,51.46),
               "Everton": (-3.08,53.66)}

# Compact station-label offsets for the octilinear final. Earlier stage
# exports retain their original positions so the design history is visible.
LABEL_07 = {
    "Man City": (.06,.21), "Man United": (-.025,-.105),
    "Liverpool": (-.035,.105), "Sunderland": (.10,.025),
    "Nottm Forest": (.085,.025), "Aston Villa": (-.08,-.145),
    "Coventry": (.075,-.08), "Ipswich": (.08,.01),
    "Fulham": (-.115,-.055), "Crystal Palace": (.085,-.055),
    "Brighton": (.085,-.065), "Bournemouth": (.105,-.08),
}

COLORS = {"W": "#159b66", "L": "#e34e51", "D": "#818d9b"}
INK = "#101a2d"
CYAN = "#12add3"
SEA = "#e4f7fb"
HALO = "#f9ffff"

def xy(lon: float, lat: float) -> tuple[float, float]:
    # Longitude is compressed to reflect its shorter distance at UK latitude.
    return ((lon + 6.4) * .63, lat - 49.7)

def club_xy(name: str, stage: int = 1) -> np.ndarray:
    loc = SCHEMATIC_07.get(name,CLUBS[name][:2]) if stage >= 7 else CLUBS[name][:2]
    return np.array(xy(*loc), dtype=float)

def load_matches() -> list[dict]:
    with CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows, "The match snapshot is empty."
    seen = set()
    for row in rows:
        assert row["competition"] == "Premier League"
        assert date.fromisoformat(row["date"]) <= AS_OF
        assert "Man City" in (row["home"], row["away"])
        key = (row["date"], row["home"], row["away"])
        assert key not in seen, f"Duplicate match: {key}"
        seen.add(key)
        row["home_goals"] = int(row["home_goals"])
        row["away_goals"] = int(row["away_goals"])
        row["opponent"] = row["away"] if row["home"] == "Man City" else row["home"]
        assert row["opponent"] in CLUBS and row["opponent"] in ROUTE
        row["venue"] = "HOME" if row["home"] == "Man City" else "AWAY"
        city = row["home_goals"] if row["venue"] == "HOME" else row["away_goals"]
        other = row["away_goals"] if row["venue"] == "HOME" else row["home_goals"]
        row["result"] = "W" if city > other else "L" if city < other else "D"
    return rows

def polygons_from_geojson(name: str):
    feature = json.loads((DATA / f"{name}.geojson").read_text(encoding="utf-8"))["features"][0]
    geom = feature["geometry"]
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in polys:
        yield np.array([xy(lon, lat) for lon, lat in poly[0]])

def draw_land(ax, stage: int):
    if stage >= 6:
        uk = json.loads((DATA / "uk-countries.geojson").read_text(encoding="utf-8"))
        country_colors = {
            "England": CYAN, "Wales": "#46bfd9",
            "Scotland": "#7acfe0", "Northern Ireland": "#70c8dc",
        }
        for feature in uk["features"]:
            name = feature["properties"]["shapeName"]
            geom = feature["geometry"]
            polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
            for poly in polys:
                coords = np.array([xy(lon,lat) for lon,lat in poly[0]])
                ax.add_patch(Polygon(coords, closed=True, facecolor=country_colors[name],
                                     edgecolor="white", linewidth=2.2,
                                     joinstyle="round", zorder=0))
        for coords in polygons_from_geojson("IRL"):
            ax.add_patch(Polygon(coords, closed=True, facecolor="#aedce7",
                                 edgecolor="white", linewidth=2.2, zorder=-1))
        ax.text(*xy(-4.47,52.34), "WALES", color="#216b83", fontsize=15,
                weight="bold", alpha=.72, zorder=1)
        ax.text(*xy(-4.75,55.13), "SCOTLAND", color="#216b83", fontsize=13,
                weight="bold", alpha=.70, zorder=1)
        return
    for country in ("GBR", "IRL"):
        for coords in polygons_from_geojson(country):
            ax.add_patch(Polygon(
                coords, closed=True, facecolor=CYAN if stage >= 4 else "#bde8ef",
                edgecolor="white", linewidth=2.6 if stage >= 4 else 1.3,
                joinstyle="round", zorder=0))

def v(points):
    return [np.array(xy(*p), dtype=float) for p in points]

# Rail corridors were laid out by hand in schematic space. Long shared sections
# use a common centerline; each route receives a fixed, deterministic offset.
CORRIDORS = {
    "north": v([(-2.20,53.48),(-2.04,53.90),(-1.67,54.27),(-1.53,54.61)]),
    "west": v([(-2.20,53.48),(-2.58,53.61),(-2.85,53.59)]),
    "midlands": v([(-2.20,53.48),(-2.36,53.18),(-2.16,52.91),(-2.05,52.70)]),
    "southeast": v([(-2.20,53.48),(-1.88,53.22),(-1.43,52.99),(-1.07,52.62),(-.70,52.24),(-.46,51.88)]),
    "southwest": v([(-2.20,53.48),(-2.63,53.07),(-2.66,52.50),(-2.34,52.05),(-2.31,51.52)]),
}

ROUTE = {
    "Sunderland": ("north", .00, 4),
    "Liverpool": ("west", -.015, 3),
    "Man United": ("west", .055, 2),
    "Nottm Forest": ("midlands", .065, 3),
    "Aston Villa": ("midlands", -.030, 4),
    "Coventry": ("midlands", .015, 4),
    "Ipswich": ("southeast", .095, 5),
    "Fulham": ("southeast", -.025, 6),
    "Crystal Palace": ("southeast", .025, 6),
    "Brighton": ("southeast", -.085, 6),
    "Bournemouth": ("southwest", 0, 5),
}

def unit_normal(a, b):
    d = b - a
    norm = np.linalg.norm(d)
    if norm < 1e-9:
        return np.array([0.0, 1.0])
    d /= norm
    return np.array([-d[1], d[0]])

def offset_polyline(points, amount):
    p = np.array(points, dtype=float)
    normals = []
    for i in range(len(p)):
        a, b = p[max(0,i-1)], p[min(len(p)-1,i+1)]
        normals.append(unit_normal(a,b))
    return p + amount * np.array(normals)

def simplify_branch(start, end):
    """One or two 45-degree/orthogonal turns, with no mechanical zigzag."""
    sx, sy = start; ex, ey = end
    dx, dy = ex-sx, ey-sy
    if abs(dx) < .13 or abs(dy) < .13:
        return [end]
    # Go diagonally for the smaller coordinate change, then straight.
    step = min(abs(dx), abs(dy)) * .60
    knee = np.array([sx + math.copysign(step,dx), sy + math.copysign(step,dy)])
    if abs(dx) > abs(dy):
        knee2 = np.array([ex, knee[1]])
    else:
        knee2 = np.array([knee[0], ey])
    return [knee, knee2, end]

def exact_offset(points, amount):
    """Offset an octilinear rail with mitered bends, retaining exact angles."""
    p = np.asarray(points, dtype=float)
    normals = [unit_normal(a,b) for a,b in zip(p,p[1:])]
    result = [p[0] + amount*normals[0]]
    for i in range(1,len(p)-1):
        a,b = p[i-1:i+1]
        c = p[i+1]
        d1,d2 = b-a,c-b
        # Intersect the two offset segment lines at their common bend.
        q1 = b + amount*normals[i-1]
        q2 = b + amount*normals[i]
        det = d1[0]*d2[1] - d1[1]*d2[0]
        if abs(det) < 1e-10:
            result.append(q1)
        else:
            delta = q2-q1
            t = (delta[0]*d2[1]-delta[1]*d2[0])/det
            result.append(q1+t*d1)
    result.append(p[-1]+amount*normals[-1])
    result[0] = p[0]
    return np.array(result)

def route_points_stage7(opponent):
    """Hand-set octilinear trunk lines; near clubs share most of their route."""
    o = club_xy("Man City",7)
    d = club_xy(opponent,7)
    se = [o,(2.84,3.78),(3.34,3.28),(3.93,2.69)]
    mid = [o,(2.64,3.48),(2.91,3.21)]
    if opponent == "Sunderland":
        return np.array([o,(2.646,4.18),(3.156,4.69),d])
    if opponent == "Man United":
        return np.array([o,(2.60,3.826),(d[0],3.826),d])
    if opponent == "Liverpool":
        return np.array([o,(2.55,3.876),(d[0],3.876),d])
    if opponent == "Bournemouth":
        return np.array([o,(2.57,3.704),(2.57,2.10),(2.85,1.82),(2.85,d[1]),d])
    if opponent == "Nottm Forest":
        return np.vstack([exact_offset(se[:3],-.11),d])
    if opponent == "Ipswich":
        rail = exact_offset(se,.11)
        q = rail[-1]
        # Keep the same 45-degree heading, then finish horizontally.
        knee = np.array([q[0]+q[1]-d[1],d[1]])
        return np.vstack([rail,knee,d])
    if opponent in ("Fulham","Crystal Palace","Brighton"):
        lane = {"Fulham":-.055,"Crystal Palace":.055,"Brighton":0}[opponent]
        rail = exact_offset(se+[(3.93,d[1])],lane)
        return np.vstack([rail,d])
    if opponent == "Aston Villa":
        rail = exact_offset(mid+[(2.91,d[1])],-.035)
        return np.vstack([rail,d])
    if opponent == "Coventry":
        rail = exact_offset(mid+[(2.91,2.95)],.035)
        q = rail[-1]
        knee = np.array([q[0]+.15,q[1]-.15])
        return np.vstack([rail,knee,(knee[0],d[1]),d])
    raise KeyError(opponent)

def route_points_stage8(opponent):
    """Keep stage 07, except for one southbound three-track corridor."""
    if opponent not in ("Aston Villa", "Coventry", "Bournemouth"):
        return route_points_stage7(opponent)
    o = club_xy("Man City",8)
    d = club_xy(opponent,8)
    # Villa is the west lane, Bournemouth the middle through lane, Coventry
    # the east lane. All three follow the same bends almost to Villa.
    south = [o,(2.64,3.48),(2.93,3.19),(2.93,2.81)]
    if opponent == "Aston Villa":
        rail = exact_offset(south,-.08)
        return np.vstack([rail,d])
    if opponent == "Coventry":
        rail = exact_offset(south,.08)
        q = rail[-1]
        knee = np.array([d[0],q[1]-(d[0]-q[0])])
        return np.vstack([rail,knee,d])
    rail = exact_offset(south,0)
    return np.vstack([rail,(rail[-1][0],d[1]),d])

def route_points(opponent: str, stage: int, venue: str | None = None):
    if stage >= 8:
        return route_points_stage8(opponent)
    if stage >= 7:
        return route_points_stage7(opponent)
    origin, dest = club_xy("Man City"), club_xy(opponent)
    if stage == 1:
        return np.array([origin, dest])
    corridor, amount, count = ROUTE[opponent]
    if stage >= 5:
        # Final routing order follows the relative positions of destinations.
        # Forest leaves the eastern fan early; the London tracks stay ordered.
        final_routes = {
            "Nottm Forest": ("southeast", .20, 3),
            "Aston Villa": ("midlands", -.055, 4),
            "Coventry": ("midlands", .055, 4),
            "Ipswich": ("southeast", .28, 5),
            "Fulham": ("southeast", -.13, 6),
            "Crystal Palace": ("southeast", .07, 6),
            "Brighton": ("southeast", -.035, 6),
        }
        corridor, amount, count = final_routes.get(opponent, (corridor,amount,count))
    if stage >= 3 and venue in ("HOME", "AWAY"):
        # Each opponent's base offset is the centre of a reserved home/away
        # pair. The completed match occupies one of its adjacent lane slots.
        amount += .012 if venue == "HOME" else -.012
    base = np.array(CORRIDORS[corridor][:count])
    if stage == 2:
        amount = 0
    elif stage == 3:
        amount *= .55
    # Keep the shared departure at the City node and spread the tracks
    # gradually, allowing a meaningful rail fan rather than overlapping starts.
    base = offset_polyline(base, amount)
    base[0] = origin
    if stage >= 6:
        # A short, tightly spaced departure bundle gives every route in a
        # sector the same heading before its first split. Both new points
        # lie within or just outside the City station, so they read as tracks.
        rank = {
            "Fulham": -2, "Brighton": -1, "Crystal Palace": 0,
            "Nottm Forest": 1, "Ipswich": 2,
            "Aston Villa": -1, "Coventry": 1,
            "Liverpool": -1, "Man United": 1,
        }.get(opponent, 0)
        direction = CORRIDORS[corridor][1] - origin
        direction /= np.linalg.norm(direction)
        normal = np.array([-direction[1], direction[0]])
        lane = rank * .042
        portal = origin + direction * .11 + normal * lane
        lead = origin + direction * .31 + normal * lane
        base = np.vstack([origin, portal, lead, base[1:]])
    elif len(base) > 1:
        base[1] = base[1] * .85 + origin * .15
    branch = simplify_branch(base[-1], dest)
    return np.vstack([base, branch])

def draw_route(ax, points, color, stage, venue):
    if stage == 6:
        points = rounded_route(points)
    x, y = points[:,0], points[:,1]
    width = 3.6 if stage < 4 else 4.4
    if stage >= 4:
        ax.plot(x,y,color=HALO,linewidth=width+2.7,solid_capstyle="round",
                solid_joinstyle="round",zorder=2)
    ax.plot(x,y,color=color,linewidth=width,solid_capstyle="round",
            solid_joinstyle="round",zorder=3)
    if stage == 6 and len(points) > 1:
        # Small arrow next to the opponent station: City home = toward City,
        # City away = toward opponent. Colour still records City's result.
        a, b = points[-2], points[-1]
        d = b-a
        d /= np.linalg.norm(d)
        if venue == "HOME":
            start, end = b-d*.12, b-d*.28
        else:
            start, end = b-d*.29, b-d*.12
        ax.annotate("", xy=end, xytext=start,
                    arrowprops=dict(arrowstyle="-|>", mutation_scale=13,
                                    lw=1.2, color=INK), zorder=7)

def rounded_route(points, radius=.042):
    """Soften each schematic turn without changing route endpoints."""
    points = np.asarray(points)
    out = [points[0]]
    for i in range(1, len(points)-1):
        a,b,c = points[i-1:i+2]
        u, w = a-b, c-b
        lu, lw = np.linalg.norm(u), np.linalg.norm(w)
        if min(lu,lw) < 1e-5:
            continue
        r = min(radius, lu*.28, lw*.28)
        p = b + u/lu*r
        q = b + w/lw*r
        out.append(p)
        for t in np.linspace(.2,.8,4):
            out.append((1-t)**2*p + 2*t*(1-t)*b + t*t*q)
        out.append(q)
    out.append(points[-1])
    return np.array(out)

def draw_nodes(ax, stage: int, rows):
    names = list(CLUBS)
    if stage < 4:
        names = ["Man City"] + [n for n in names if n != "Man City"]
    for name in names:
        lon, lat, label, scale, delta = CLUBS[name]
        p = club_xy(name,stage)
        radius = (.055 if stage < 4 else .060) * scale
        if name == "Man City": radius *= 1.65
        ax.add_patch(Circle(p,radius,facecolor="white",edgecolor=INK,
                            linewidth=2 if stage >= 4 else 1.3,zorder=8))
        if stage >= 3:
            ox,oy=LABEL_07[name] if stage>=7 else delta
            ha = "left" if ox >= 0 else "right"
            ax.text(p[0]+ox,p[1]+oy,label,ha=ha,va="center",
                    fontsize=7.5 if stage < 5 else 12.0 if stage < 7 or name=="Man City" else 9.5,
                    fontweight="bold",color=INK,zorder=10,
                    path_effects=[pe.withStroke(linewidth=1.3,foreground=HALO)] if stage>=5 else [])
    if stage >= 6:
        played = {r["opponent"] for r in rows}
        unplayed = UNPLAYED_07 if stage >= 7 else UNPLAYED
        for name,(lon,lat) in unplayed.items():
            if name in played:
                continue
            ax.add_patch(Circle(xy(lon,lat), .024, facecolor=HALO,
                                edgecolor="#526478", linewidth=1.25,
                                zorder=8))

def decorate(ax, rows, stage):
    if stage >= 6:
        ax.add_patch(Rectangle((.28,6.08),4.87,.87,
                               facecolor=SEA,edgecolor="none",zorder=11))
        ax.add_patch(Rectangle((.28,.05),4.87,.70,
                               facecolor=SEA,edgecolor="none",zorder=11))
    title_x = .42 if stage >= 6 else 1.08 if stage >= 5 else .10
    title_y = 6.82 if stage >= 6 else 5.86 if stage >= 5 else 6.87
    ax.text(title_x,title_y,"MAN CITY",fontsize=32 if stage>=5 else 25,
            weight="heavy",color=INK,va="top",zorder=12)
    ax.text(title_x+.02,title_y-.36,"THE 2026/27 RESULTS NETWORK",fontsize=13 if stage>=5 else 10.8,
            weight="bold",color="#415266",zorder=12)
    ax.text(title_x+.02,title_y-.60,"PREMIER LEAGUE  ·  THROUGH 26 NOV 2026",fontsize=10 if stage>=5 else 8.5,
            color="#536477",zorder=12)
    if stage>=4:
        y=.50 if stage >= 6 else .52
        legend = [(.39,"W","WIN"),(1.77,"D","DRAW"),(3.14,"L","LOSS")] if stage>=6 else [(1.12,"W","WIN"),(2.46,"D","DRAW"),(3.77,"L","LOSS")] if stage>=5 else [(.28,"W","WIN"),(1.38,"D","DRAW"),(2.50,"L","LOSS")]
        for x,code,word in legend:
            ax.plot([x,x+.28],[y,y],color=COLORS[code],lw=4.5,zorder=11)
            ax.text(x+.36,y,word,va="center",fontsize=11 if stage>=5 else 9,weight="bold",color=INK,zorder=11)
        caption = ("H / A beside each club = City home / away  ·  small dots = unplayed"
                   if stage >= 7 else
                   "Arrow toward club = City away  ·  arrow toward City = City home  ·  small dots = unplayed"
                   if stage == 6 else "H / A beside each club = City home / away")
        ax.text(.39 if stage>=6 else 1.12 if stage>=5 else .28,.26,caption,
                fontsize=8.5 if stage>=6 else 9.5 if stage>=5 else 8.3,color="#526478",zorder=11)
    else:
        ax.text(.12,.31,f"{len(rows)} completed matches  ·  stage {stage}/5",
                fontsize=9,color=INK,zorder=11)

def label_home_away(ax, rows, stage):
    if stage < 4 or stage == 6: return
    by_name = {r["opponent"]:r for r in rows}
    for name,r in by_name.items():
        p = club_xy(name,stage)
        if stage >= 7:
            dx,dy = {
                "Man United":(.08,-.055), "Liverpool":(.08,-.055),
                "Sunderland":(.085,-.09), "Nottm Forest":(.08,-.09),
                "Aston Villa":(-.085,.085), "Coventry":(.08,.085),
                "Ipswich":(-.03,.105), "Fulham":(-.085,.085),
                "Crystal Palace":(.08,.085), "Brighton":(.08,.085),
                "Bournemouth":(.08,.085),
            }[name]
            if stage >= 8 and name == "Bournemouth":
                dx,dy = -.095,.075
            ax.text(p[0]+dx,p[1]+dy,r["venue"][0],ha="center",va="center",
                    fontsize=8.2,weight="bold",color="#304357",zorder=10,
                    path_effects=[pe.withStroke(linewidth=1.0,foreground=HALO)])
            continue
        # small compact match tab, offset to keep it distinct from club label
        dx = .09 if CLUBS[name][4][0] >= 0 else -.09
        dy = -.12 if CLUBS[name][4][1] >= 0 else .11
        ax.text(p[0]+dx,p[1]+dy,r["venue"][0],
                ha="center",va="center",fontsize=9 if stage>=5 else 6.4,weight="bold",
                color="#466073",zorder=10)

def render(rows, stage):
    fig,ax=plt.subplots(figsize=(10.8,15.2),dpi=150)
    fig.patch.set_facecolor(SEA)
    ax.set_facecolor(SEA)
    if stage >= 6:
        ax.set_xlim(.28,5.15); ax.set_ylim(.05,6.95)
    elif stage >= 5:
        ax.set_xlim(1.03,5.15); ax.set_ylim(.05,5.95)
    else:
        ax.set_xlim(-.05,5.15); ax.set_ylim(.05,7.05)
    ax.set_aspect("equal")
    ax.axis("off")
    draw_land(ax,stage)
    # Draw corridors from north to south; the outlines maintain visual
    # separation even when tracks meet the same station.
    for row in rows:
        points=route_points(row["opponent"],stage,row["venue"])
        draw_route(ax,points,COLORS[row["result"]],stage,row["venue"])
    draw_nodes(ax,stage,rows)
    label_home_away(ax,rows,stage)
    decorate(ax,rows,stage)
    names={
      1:"01_geographic_straight_routes",
      2:"02_schematic_corridors",
      3:"03_parallel_tracks",
      4:"04_stations_and_result_legend",
      5:"05_final_polished_map",
      6:"06_revised_final_map",
      7:"07_octilinear_shared_corridors",
      8:"08_southbound_three_track_corridor",
    }
    path=OUT/(names[stage]+".png")
    fig.savefig(path,dpi=150,facecolor=fig.get_facecolor(),bbox_inches="tight",pad_inches=.10)
    plt.close(fig)
    return path

def main():
    rows=load_matches()
    print(f"Snapshot: {len(rows)} EPL matches; {dict(Counter(r['result'] for r in rows))}")
    for stage in range(1,9):
        print(render(rows,stage))

if __name__=="__main__":
    main()