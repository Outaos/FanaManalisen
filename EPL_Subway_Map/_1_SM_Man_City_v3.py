#!/usr/bin/env python3
"""Render 2025/26 Premier League home and away subway maps for selected clubs.

The route geometry builds on the rule-based v2 experiment. This script keeps
the full-season input fixed and does not modify v2 or fetch data at runtime.

Run: python _1_SM_Man_City_v3.py
     python _1_SM_Man_City_v3.py --club Arsenal
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, Polygon, Rectangle
import matplotlib.patheffects as pe
import numpy as np

import _1_SM_Man_City as base
import _1_SM_Man_City_v2 as route

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'data' / 'epl_2025_26_results.csv'
OUT = ROOT / 'outputs' / 'epl_2026'
CLUBS_OF_INTEREST = ('Man City', 'Man United', 'Arsenal', 'Chelsea',
                     'Tottenham', 'Liverpool', 'Everton', 'West Ham')
SEASON_CLUBS = ('Arsenal', 'Aston Villa', 'Bournemouth', 'Brentford',
                'Brighton', 'Burnley', 'Chelsea', 'Crystal Palace',
                'Everton', 'Fulham', 'Leeds', 'Liverpool', 'Man City',
                'Man United', 'Newcastle', 'Nottm Forest', 'Sunderland',
                'Tottenham', 'West Ham', 'Wolves')
COLORS = {'W': '#437d61', 'D': '#78828a', 'L': '#aa6463'}
SEA = '#e9f2f2'
INK = '#17303a'
MUTED_INK = '#526971'

# Ground locations in lon/lat, with only small schematic displacement.
# The older v2 coordinates are retained for shared clubs. London stations
# are spread further by declutter_nodes below, never beyond its .12-unit cap.
EXTRA_GROUNDS = {
    'Burnley': (-2.23018, 53.788799),
    'Wolves': (-2.13061, 52.590401),
    'West Ham': (-0.016587, 51.5383),
}


def positions_for_season() -> dict[str, np.ndarray]:
    positions = {n: base.club_xy(n, 9) for n in SEASON_CLUBS if n in base.CLUBS}
    positions.update({n: route.xy(*base.UNPLAYED_07[n])
                      for n in SEASON_CLUBS if n in base.UNPLAYED_07})
    positions.update({n: route.xy(*v) for n, v in EXTRA_GROUNDS.items()})
    assert set(positions) == set(SEASON_CLUBS), set(SEASON_CLUBS) - set(positions)
    return positions


def load_season() -> list[dict]:
    with SOURCE.open(newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 380, f'Expected 380 fixtures, found {len(rows)}'
    pairs = set()
    for row in rows:
        h, a = row['home'], row['away']
        assert h in SEASON_CLUBS and a in SEASON_CLUBS and h != a
        assert row['date'].startswith(('2025-', '2026-'))
        assert (h, a) not in pairs, (h, a)
        pairs.add((h, a))
        row['home_goals'] = int(row['home_goals'])
        row['away_goals'] = int(row['away_goals'])
    assert pairs == {(h, a) for h in SEASON_CLUBS for a in SEASON_CLUBS if h != a}
    return rows


def club_matches(season: list[dict], club: str, venue: str) -> list[dict]:
    matches = []
    for match in season:
        if venue == 'HOME' and match['home'] == club:
            opponent = match['away']
            own, against = match['home_goals'], match['away_goals']
        elif venue == 'AWAY' and match['away'] == club:
            opponent = match['home']
            own, against = match['away_goals'], match['home_goals']
        else:
            continue
        matches.append({'opponent': opponent,
                        'result': 'W' if own > against else 'L' if own < against else 'D',
                        'date': match['date'], 'venue': venue})
    assert len(matches) == 19 and len({m['opponent'] for m in matches}) == 19
    return matches


def draw_geography(ax) -> None:
    fills = {'England': '#9ec9cb', 'Wales': '#8ebfc2',
             'Scotland': '#b4d3d3', 'Northern Ireland': '#a8ced0'}
    unique = {}
    for name, polygon in route.topological_countries():
        ax.add_patch(Polygon(polygon, closed=True, facecolor=fills[name],
                             edgecolor='none', zorder=0))
        for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
            ka, kb = tuple(np.round(a, 7)), tuple(np.round(b, 7))
            unique[route.edge_key(ka, kb)] = np.array([a, b])
    ax.add_collection(LineCollection(list(unique.values()), colors='#f5f9f8',
                                    linewidths=2.1, capstyle='round', zorder=1))
    ax.text(*route.xy(-4.65, 55.1), 'SCOTLAND', fontsize=12, weight='bold',
            color='#5d8589', alpha=.82)
    ax.text(*route.xy(-4.5, 52.35), 'WALES', fontsize=13, weight='bold',
            color='#4e8085', alpha=.82)


def draw_track(ax, points: np.ndarray, color: str, hub: np.ndarray) -> None:
    """Draw one solid colored rail, with no white casing or outline."""
    pts = route.smooth_departure(points, hub)
    distance = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    cut = min(len(pts) - 1, int(np.searchsorted(distance, .30)))
    ax.plot(pts[cut:, 0], pts[cut:, 1], color=color, lw=3.7,
            solid_capstyle='round', solid_joinstyle='round', zorder=3)
    for i in range(cut):
        width = 1.3 + 2.4 * min(1, distance[i] / .30)
        ax.plot(pts[i:i + 2, 0], pts[i:i + 2, 1], color=color, lw=width,
                solid_capstyle='round', zorder=3)


def draw_stations(ax, hub: str, positions: dict[str, np.ndarray]) -> None:
    """Label all stations, using fixed fan positions for dense London nodes."""
    london = {'Arsenal', 'Chelsea', 'Tottenham', 'West Ham',
              'Crystal Palace', 'Fulham', 'Brentford'}
    for name, point in positions.items():
        radius = .10 if name == hub else .037
        ax.add_patch(Circle(point, radius, facecolor='#f8faf9', edgecolor=INK,
                            lw=2, zorder=8))

    # The two London label columns are anchored to a schematic city center.
    # The small leader lines preserve the correspondence to the actual nodes.
    london_labels = {
        'Arsenal': (4.00, 2.29, 'left'),
        'Tottenham': (4.26, 2.08, 'left'),
        'Fulham': (3.72, 1.98, 'right'),
        'Chelsea': (3.72, 1.82, 'right'),
        'Brentford': (3.72, 1.64, 'right'),
        'West Ham': (4.28, 1.78, 'left'),
        'Crystal Palace': (4.28, 1.58, 'left'),
    }
    for name in london:
        x, y, align = london_labels[name]
        p = positions[name]
        end = np.array([x - .025 if align == 'left' else x + .025, y])
        if np.linalg.norm(p - end) > .10:
            ax.plot([p[0], end[0]], [p[1], end[1]], color='#5d777a',
                    lw=.9, alpha=.8, zorder=7)
        ax.text(x, y, name.upper(), ha=align, va='center',
                fontsize=11.5 if name == hub else 9.2, weight='bold',
                color=INK, zorder=10,
                path_effects=[pe.withStroke(linewidth=1, foreground=SEA)])

    # Use v2's shortest clear candidate idea for the less dense stations.
    placed = []
    for name in sorted(set(positions) - london,
                       key=lambda n: (n != hub, -np.linalg.norm(positions[n] - positions[hub]))):
        p = positions[name]
        size = 11.5 if name == hub else 9.2
        width = len(name) * (.052 if name == hub else .044)
        candidates = [(dx, dy) for dx in (-.08, .08, -.13, .13)
                      for dy in (.13, -.11, .02, -.19)]
        if name == hub:
            candidates = [(.055, .205)] + candidates
        def bbox(delta):
            q = p + delta
            return (q[0] if delta[0] > 0 else q[0] - width,
                    q[0] + width if delta[0] > 0 else q[0],
                    q[1] - .052, q[1] + .052)
        def score(delta):
            b = bbox(delta)
            penalty = np.linalg.norm(delta)
            for other, r in positions.items():
                if other == name:
                    continue
                cx = np.clip(r[0], b[0], b[1])
                cy = np.clip(r[1], b[2], b[3])
                if np.linalg.norm(r - [cx, cy]) < (.105 if other == hub else .046):
                    penalty += 30
            for v in placed:
                overlap = max(0, min(b[1], v[1]) - max(b[0], v[0])) * max(0, min(b[3], v[3]) - max(b[2], v[2]))
                penalty += overlap * 800
            return penalty
        delta = min(candidates, key=score)
        q = p + delta
        placed.append(bbox(delta))
        ax.text(q[0], q[1], name.upper(), ha='left' if delta[0] > 0 else 'right',
                va='center', fontsize=size, weight='bold', color=INK,
                zorder=10, path_effects=[pe.withStroke(linewidth=1, foreground=SEA)])


def crossing_free_fan(hub: str, positions: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Fallback for west-side hubs that overload v2's southeast sector.

    Start with a noncrossing radial arrangement. Try small two-bend deviations
    from each line, selecting the candidate with fewest station intrusions
    while retaining zero line crossings. This is deterministic for a club.
    """
    center = positions[hub]
    rails = {n: np.array([center, point]) for n, point in positions.items() if n != hub}
    ordered = sorted(rails, key=lambda n: -np.linalg.norm(positions[n] - center))
    for name in ordered:
        destination = positions[name]
        delta = destination - center
        normal = np.array([-delta[1], delta[0]]) / np.linalg.norm(delta)
        best = None
        for bend in (.12, -.12, .10, -.10, .08, -.08, .06, -.06,
                     .04, -.04, .02, -.02, 0):
            candidate = np.array([center, center + .28 * delta + bend * normal,
                                  center + .72 * delta + bend * normal, destination])
            rails[name] = candidate
            crossings = len(route.crossings(rails, center))
            intrusions = len(route.station_intrusions(rails, positions, hub))
            score = crossings * 1000 + intrusions * 10 - abs(bend)
            if best is None or score < best[0]:
                best = (score, candidate)
        rails[name] = best[1]
    return rails


def render(club: str, venue: str, season: list[dict]) -> tuple[Path, dict]:
    matches = club_matches(season, club, venue)
    positions = route.declutter_nodes(positions_for_season(), club,
                                     {m['opponent'] for m in matches})
    if club in ('Liverpool', 'Everton'):
        rails = crossing_free_fan(club, positions)
    else:
        rails = route.build_routes(club, positions, matches)
        if len(route.crossings(rails, positions[club])) > 2:
            rails = crossing_free_fan(club, positions)
    if club == 'Chelsea' and any(set(pair) == {'Sunderland', 'Tottenham'}
                                 for pair in route.crossings(rails, positions[club])):
        # This short London spur passes under the Sunderland corridor in the
        # generic solver. A small south-side bend keeps the two rails apart.
        center, destination = positions[club], positions['Tottenham']
        delta = destination - center
        normal = np.array([-delta[1], delta[0]]) / np.linalg.norm(delta)
        rails['Tottenham'] = np.array([center, center + .55 * delta - .08 * normal,
                                      destination])
    fig, ax = plt.subplots(figsize=(10.8, 16), dpi=150)
    fig.patch.set_facecolor(SEA)
    ax.set_facecolor(SEA)
    ax.set_xlim(.1, 5.15)
    ax.set_ylim(-.55, 6.95)
    ax.set_aspect('equal')
    ax.axis('off')
    draw_geography(ax)
    for match in matches:
        draw_track(ax, rails[match['opponent']], COLORS[match['result']], positions[club])
    draw_stations(ax, club, positions)
    ax.add_patch(Rectangle((.1, 6.08), 5.05, .87, color=SEA, zorder=11))
    ax.add_patch(Rectangle((.1, -.55), 5.05, .43, color=SEA, zorder=11))
    ax.text(.23, 6.78, club.upper(), fontsize=29, weight='heavy', color=INK, zorder=12)
    ax.text(.25, 6.43, f'{venue} RESULTS  |  PREMIER LEAGUE 2025/26',
            fontsize=12.2, weight='bold', color=MUTED_INK, zorder=12)
    tally = Counter(m['result'] for m in matches)
    ax.text(.25, 6.2, f"19 MATCHES  |  {tally['W']} WINS  ·  {tally['D']} DRAWS  ·  {tally['L']} LOSSES",
            fontsize=9.5, color=MUTED_INK, zorder=12)
    for x, code, label in ((.25, 'W', 'WIN'), (1.63, 'D', 'DRAW'), (3.02, 'L', 'LOSS')):
        ax.plot([x, x + .28], [-.28, -.28], color=COLORS[code], lw=4, zorder=12)
        ax.text(x + .35, -.28, label, va='center', fontsize=10.3,
                weight='bold', color=INK, zorder=12)
    ax.text(.25, -.45, 'One line per match  ·  schematic routing  ·  source: football-data.co.uk',
            fontsize=8.4, color=MUTED_INK, zorder=12)
    OUT.mkdir(parents=True, exist_ok=True)
    filename = club.lower().replace(' ', '_') + '_' + venue.lower() + '_2025_26.png'
    target = OUT / filename
    fig.savefig(target, dpi=150, bbox_inches='tight', pad_inches=.1, facecolor=SEA)
    plt.close(fig)
    metrics = {'club': club, 'venue': venue, 'W': tally['W'], 'D': tally['D'],
               'L': tally['L'], 'crossings': len(route.crossings(rails, positions[club])),
               'station_intrusions': len(route.station_intrusions(rails, positions, club))}
    return target, metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--club', choices=CLUBS_OF_INTEREST,
                        help='render only one club (both venues)')
    args = parser.parse_args()
    season = load_season()
    for club in (args.club,) if args.club else CLUBS_OF_INTEREST:
        for venue in ('HOME', 'AWAY'):
            target, metrics = render(club, venue, season)
            print(f'{target.name}: {metrics}', flush=True)


if __name__ == '__main__':
    main()
