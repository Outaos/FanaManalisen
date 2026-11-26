# Rule-based map experiment (v2)

`_1_SM_Man_City_v2.py` is a separate experiment. It imports only club positions,
the verified match snapshot, and colors from `_1_SM_Man_City.py`; it does not
change or reuse that script's hand-set route geometry.

## Rules

1. **Map topology.** Read the country's GeoJSON polygons. Identify edges that
   belong to two neighbors. Split polygon rings into coast and shared-border
   runs, then simplify each run at the same tolerance. Reversed shared runs
   retain the same vertices. Fill each polygon without a stroke; deduplicate
   the simplified edges and draw each coastline/border segment once. This
   avoids the gaps caused by simplifying England and Scotland independently.
2. **Hub and sectors.** Project all club positions, then assign opponents to
   compass sectors from the chosen hub. The source club and its opponents are
   inputs to `build_routes(hub, positions, rows)`.
3. **Shared corridors.** Each sector gets one octilinear spine determined by
   its median destination and its closest/farthest extent. Opponents are
   ordered into equally spaced parallel lanes by destination position.
   Routes follow the spine until the nearest sensible branch point; small
   0°/45°/90° connectors finish at each club.
4. **Crossings.** A lane-swap search minimizes intersections across the whole
   route graph. `crossings()` reports any remaining intersections outside the
   hub circle. The algorithm does not yet guarantee a planar layout.
5. **Stations, hub fan, and labels.** `declutter_nodes()` gives overlapping
   stations a bounded, deterministic push while keeping the hub fixed. A short
   cubic easing and gradual line-width increase bring tracks out from under
   the hub station. White casings start farther away. Label candidates are
   scored against station circles and other label boxes rather than assigned
   per club.
6. **Cornwall.** The legend sits below the mapped land instead of covering
   southwestern England, so Cornwall remains visible.

## Reproduce and check

```sh
python _1_SM_Man_City_v2.py --check
python _1_SM_Man_City_v2.py --demo-arsenal
```

The first command writes `outputs/10_v2_rule_based_man_city.png` and checks
the shared borders and route crossings. The optional second command also
writes `outputs/10_v2_arsenal_cluster_test.png`. Arsenal's seven gray lines
are **neutral layout probes, not Arsenal match results**.

The current checks find zero crossings for City's 11 completed matches and
the seven-route Arsenal cluster. A diagnostic with **all 19 neutral Arsenal
opponents** still produces 18 crossing pairs. Thus the engine is reusable for
another hub and a dense cluster, while a complete second-club network still
needs better branch selection and local-node decluttering. For another
country, supply positions and match rows to `build_routes`, and a compatible
administrative GeoJSON to `topological_countries`; the renderer's fills,
annotations, and frame would need that country's settings.