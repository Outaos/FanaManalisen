# Manchester City · EPL results subway map

Static schematic map of Manchester City's completed **2026–27 Premier League** matches, verified **26 November 2026**. It uses City's perspective: green = win, red = loss, gray = draw. Each completed match has one line. In the current stage 09 map, **H** and **A** beside opponent stations mean City played at home or away. Small unlabeled stations show clubs City has not played in the league yet; these have no route.

## Reproduce

From this folder, with Python 3.10+:

```sh
pip install -r requirements.txt
python _1_SM_Man_City.py
```

The script reads the fixed [match snapshot](data/man_city_epl_2026_27_asof_2026-11-26.csv) and the included country outlines, then writes nine PNGs to `outputs/`. It does not fetch live results. To update the map, verify new Premier League match reports, add rows to the CSV, update the cutoff in the script, and review the route layout for each new opponent.

## Exports

1. `01_geographic_straight_routes.png` — direct geographic connections.
2. `02_schematic_corridors.png` — simplified route bends and common corridors.
3. `03_parallel_tracks.png` — route offsets and club labels.
4. `04_stations_and_result_legend.png` — white station nodes and result legend.
5. `05_final_polished_map.png` — initial polished map, before the latest feedback.
6. `06_revised_final_map.png` — England/Wales/Scotland borders, unplayed stations, parallel starts, and home/away arrows.
7. `07_octilinear_shared_corridors.png` — smaller, closer labels, H/A indicators, straight 0°/45°/90° route segments, and longer parallel southeast corridors.
8. `08_southbound_three_track_corridor.png` — Villa, Bournemouth, and Coventry follow three parallel tracks nearly to Villa; Bournemouth continues south between the two branch routes.
9. **`09_close_parallel_simplified_coast.png`** — current recommended export: the three southbound tracks are closer together, and Great Britain's coastline and the Wales/Scotland borders are simplified further.

## V2 experiment

The original `_1_SM_Man_City.py` remains intact. The separate
`_1_SM_Man_City_v2.py` tests calculated corridor, lane, branch, label, and
shared-border rules. Its City output is `10_v2_rule_based_man_city.png`;
`--demo-arsenal` writes a neutral seven-route Arsenal layout test, not Arsenal
results. `--demo-arsenal-all` runs a 19-route neutral stress test. See
[V2_DESIGN.md](V2_DESIGN.md) for the rules, checks, and remaining station
clearance limits. Run `python _1_SM_Man_City_v2.py --check` for the audit.

The drawn lines are **diagrammatic**, not road, rail, or travel routes. Stadium markers remain near their real locations but are separated slightly where needed. In stages 07–09, the southeast routes share a diagonal trunk past the Nottingham area; the Fulham, Palace, and Brighton tracks stay parallel almost to Fulham. In stages 08–09, Villa, Bournemouth, and Coventry share the southbound trunk nearly to Villa, where the outer lanes branch and Bournemouth carries on between them. Stage 09 reduces the southbound lane spacing to match the southeast bundle and simplifies the coastline and internal borders at the map's display scale. Westbound routes leave City in adjacent lanes. Long segments are horizontal, vertical, or 45° diagonals; only tiny station connectors use other angles. White casings separate adjacent tracks. The outline of Ireland in stages 1–5 comes from [johan/world.geo.json](https://github.com/johan/world.geo.json), derived from Natural Earth public-domain data. The revised map's [UK country boundaries](data/uk-countries.geojson) are from [GeoDataViewer's UK Countries Boundaries](https://geodataviewer.com/datasets/boundaries/uk-countries-boundaries/) (CC BY 4.0; original administrative boundaries: ©EuroGeographics ©UN-FAO ©Turkstat, via Eurostat GISCO).

## V3: complete 2025/26 season, eight clubs

`_1_SM_Man_City_v3.py` applies the v2 rule-based routing to Man City, Man
United, Arsenal, Chelsea, Tottenham, Liverpool, Everton, and West Ham. Each
club has separate home and away maps in `outputs/epl_2026/`, for 16 PNGs total.
Each map has 19 result lines. Green means a win for the named club, red a loss,
and gray a draw. Tracks have muted colors and **no white casing or outline**.
The club grounds stay near their geographic locations, with small displacements
for legibility. A home map connects the selected club to its 19 opponents as
a schematic comparison; it does not depict travel from those opponents.
For western hubs where v2's shared southeast trunk creates more than two
crossings, v3 uses a deterministic two-bend radial fan that preserves route
separation. A short Chelsea-to-Tottenham connector has a south-side bend to
clear the Sunderland corridor. These club-specific adjustments keep all
16 route networks free of off-hub line crossings in the geometry audit.

```sh
python _1_SM_Man_City_v3.py
python _1_SM_Man_City_v3.py --club Arsenal
```

The fixed [2025/26 match CSV](data/epl_2025_26_results.csv) contains all 380
league fixtures, with one home and one away meeting for each ordered pair of
the 20 clubs. It is a five-column normalization of
[Football-Data.co.uk's freely published E0 season file](https://football-data.co.uk/mmz4281/2526/E0.csv),
downloaded 26 November 2026. The script validates the complete fixture matrix
before drawing and never fetches results at runtime. The v2 script remains
unchanged.

## Data check

The [Manchester City results page](https://live.mancity.com/results) lists scores across competitions, so every included row has an individual City match-report URL marked Premier League. The 16 August Arsenal result was the **Community Shield**, and the 28 October Brighton result was a **cup match**; neither appears in the CSV. The snapshot contains **11 league matches: 7 wins, 1 draw, 3 losses**.

## Visual notes

The attached SimpleTrain stills informed the saturated land color, pale sea, white outlined city nodes, strong labels, angled bends, and parallel route bundles. The most crowded section is the southeast fan toward London. Routes there are simplified and spread for legibility; their positions should not be interpreted as geographically exact. The unplayed nodes use the [Premier League's 2026/27 club list](https://www.premierleague.com/en/news/4365156); they are unlabeled to keep the map readable. Geometry checks found no stage 09 route crossings outside the City hub and no unrelated station within 0.065 map units of a route.
