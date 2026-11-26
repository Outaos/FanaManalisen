# Manchester City · EPL results subway map

Static schematic map of Manchester City's completed **2026–27 Premier League** matches, verified **26 November 2026**. It uses City's perspective: green = win, red = loss, gray = draw. Each completed match has one line. In the revised final map, a small arrow near the opponent station points **toward that club for a City away game**, or **toward City for a City home game**. Small unlabeled stations show clubs City has not played in the league yet; these have no route.

## Reproduce

From this folder, with Python 3.10+:

```sh
pip install -r requirements.txt
python _1_SM_Man_City.py
```

The script reads the fixed [match snapshot](data/man_city_epl_2026_27_asof_2026-11-26.csv) and the included country outlines, then writes six PNGs to `outputs/`. It does not fetch live results. To update the map, verify new Premier League match reports, add rows to the CSV, update the cutoff in the script, and review the route layout for each new opponent.

## Exports

1. `01_geographic_straight_routes.png` — direct geographic connections.
2. `02_schematic_corridors.png` — simplified route bends and common corridors.
3. `03_parallel_tracks.png` — route offsets and club labels.
4. `04_stations_and_result_legend.png` — white station nodes and result legend.
5. `05_final_polished_map.png` — initial polished map, before the latest feedback.
6. **`06_revised_final_map.png`** — visible England/Wales/Scotland borders, tightly parallel sector departures, unplayed club stations, and home/away arrows. This is the recommended current export.

The drawn lines are **diagrammatic**, not road, rail, or travel routes. Stadium markers remain near their real locations but are separated slightly where needed. Routes in the same sector leave Manchester as parallel tracks and branch later, with gently rounded turns. White casings separate adjacent tracks. The outline of Ireland in stages 1–5 comes from [johan/world.geo.json](https://github.com/johan/world.geo.json), derived from Natural Earth public-domain data. The revised map's [UK country boundaries](data/uk-countries.geojson) are from [GeoDataViewer's UK Countries Boundaries](https://geodataviewer.com/datasets/boundaries/uk-countries-boundaries/) (CC BY 4.0; original administrative boundaries: ©EuroGeographics ©UN-FAO ©Turkstat, via Eurostat GISCO).

## Data check

The [Manchester City results page](https://live.mancity.com/results) lists scores across competitions, so every included row has an individual City match-report URL marked Premier League. The 16 August Arsenal result was the **Community Shield**, and the 28 October Brighton result was a **cup match**; neither appears in the CSV. The snapshot contains **11 league matches: 7 wins, 1 draw, 3 losses**.

## Visual notes

The attached SimpleTrain stills informed the saturated land color, pale sea, white outlined city nodes, strong labels, angled bends, and parallel route bundles. The most crowded section is the southeast fan toward London. Routes there are simplified and spread for legibility; their positions should not be interpreted as geographically exact. The unplayed nodes use the [Premier League's 2026/27 club list](https://www.premierleague.com/en/news/4365156); they are unlabeled to keep the map readable. A segment intersection check found no crossings outside the City hub in the revised render.

