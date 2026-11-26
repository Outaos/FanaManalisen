# Manchester City · EPL results subway map

Static schematic map of Manchester City's completed **2026–27 Premier League** matches, verified **26 November 2026**. It uses City's perspective: green = win, red = loss, gray = draw. Each opponent has one line for the one league meeting played so far. Each opponent's route reserves adjacent home and away lane positions; the completed match occupies its corresponding slot. Small **H** and **A** tags indicate whether City played at home or away. Unplayed fixtures and matches in other competitions are excluded.

## Reproduce

From this folder, with Python 3.10+:

```sh
pip install -r requirements.txt
python _1_SM_Man_City.py
```

The script reads the fixed [match snapshot](data/man_city_epl_2026_27_asof_2026-11-26.csv) and the included rough country outlines, then writes five PNGs to `outputs/`. It does not fetch live results. To update the map, verify new Premier League match reports, add rows to the CSV, update the cutoff in the script, and review the route layout for each new opponent.

## Exports

1. `01_geographic_straight_routes.png` — direct geographic connections.
2. `02_schematic_corridors.png` — simplified route bends and common corridors.
3. `03_parallel_tracks.png` — route offsets and club labels.
4. `04_stations_and_result_legend.png` — white station nodes and result legend.
5. `05_final_polished_map.png` — revised lane order and branch positions.

The drawn lines are **diagrammatic**, not road, rail, or travel routes. Stadium markers remain near their real locations but are separated slightly where needed. White line casings improve separation at junctions. The simplified GB/IE outlines come from [johan/world.geo.json](https://github.com/johan/world.geo.json), derived from Natural Earth public-domain data.

## Data check

The [Manchester City results page](https://live.mancity.com/results) lists scores across competitions, so every included row has an individual City match-report URL marked Premier League. The 16 August Arsenal result was the **Community Shield**, and the 28 October Brighton result was a **cup match**; neither appears in the CSV. The snapshot contains **11 league matches: 7 wins, 1 draw, 3 losses**.

## Visual notes

The attached SimpleTrain stills informed the saturated land color, pale sea, white outlined city nodes, strong labels, angled bends, and parallel route bundles. The most crowded section is the southeast fan toward London. Routes there are simplified and spread for legibility; their positions should not be interpreted as geographically exact. Only completed league opponents have nodes, so Arsenal, Leeds, Chelsea, Newcastle and other yet-to-play clubs are intentionally absent.

