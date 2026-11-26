#!/usr/bin/env python3
"""Rule-based EPL subway map experiment. The original script is untouched.

Club/result data come from _1_SM_Man_City.py. This file owns the reusable
topology, sector, lane, octilinear connector, label, and rendering rules.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import json
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, Rectangle
from matplotlib.collections import LineCollection
import matplotlib.patheffects as pe
import _1_SM_Man_City as data

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'
OUT.mkdir(exist_ok=True)
SEA='#e4f7fb'; INK='#101a2d'; HALO='#f9ffff'
COLORS=data.COLORS

def xy(lon,lat): return np.array(data.xy(lon,lat),float)
def norm(v):
    n=np.linalg.norm(v)
    return v/n if n>1e-10 else v

def rdp(line,tol):
    line=np.asarray(line,float)
    if len(line)<3: return line
    a,b=line[0],line[-1]; d=b-a; den=np.dot(d,d)
    t=np.clip(((line[1:-1]-a)@d)/den,0,1) if den>1e-12 else np.zeros(len(line)-2)
    dist=np.linalg.norm(line[1:-1]-(a+t[:,None]*d),axis=1)
    k=int(np.argmax(dist))+1
    if dist[k-1]<=tol: return line[[0,-1]]
    return np.vstack([rdp(line[:k+1],tol)[:-1],rdp(line[k:],tol)])

def ring_edges(ring):
    pts=[tuple(p) for p in ring]
    if pts[0]==pts[-1]: pts=pts[:-1]
    return pts

def edge_key(a,b): return tuple(sorted((a,b)))

def topological_countries(tol=.045,geojson_path=None):
    """Simplify each shared border as one run in both adjacent polygons."""
    path=Path(geojson_path) if geojson_path else ROOT/'data/uk-countries.geojson'
    geo=json.loads(path.read_text(encoding='utf-8'))
    rings=[]; owners=defaultdict(set)
    for feature in geo['features']:
        name=feature['properties']['shapeName']
        geom=feature['geometry']
        polys=geom['coordinates'] if geom['type']=='MultiPolygon' else [geom['coordinates']]
        for poly in polys:
            pts=ring_edges(poly[0]); rings.append((name,pts))
            for a,b in zip(pts,pts[1:]+pts[:1]): owners[edge_key(a,b)].add(name)
    result=[]
    for name,pts in rings:
        n=len(pts)
        if n<4: continue
        shared=[len(owners[edge_key(pts[i],pts[(i+1)%n])])>1 for i in range(n)]
        # Rotate to a coast/border transition; both countries then simplify
        # the shared run with identical endpoints (reversed order is safe).
        cuts=[i for i in range(n) if shared[i]!=shared[i-1]]
        start=cuts[0] if cuts else 0
        seq=pts[start:]+pts[:start]; flags=shared[start:]+shared[:start]
        seq.append(seq[0]); out=[]; i=0
        while i<n:
            j=i+1
            while j<n and flags[j]==flags[i]: j+=1
            part=rdp([xy(*p) for p in seq[i:j+1]],tol)
            out.extend(part[:-1]); i=j
        arr=np.array(out)
        if len(arr)>=3: result.append((name,arr))
    return result

def draw_geography(ax):
    fills={'England':'#12add3','Wales':'#46bfd9','Scotland':'#7acfe0',
           'Northern Ireland':'#70c8dc'}
    polys=topological_countries()
    # Country fill polygons have no individual stroke. Deduplicate their
    # simplified edges, then draw each coastline/shared border exactly once.
    unique={}
    for name,p in polys:
        ax.add_patch(Polygon(p,closed=True,facecolor=fills[name],edgecolor='none',zorder=0))
        for a,b in zip(p,np.roll(p,-1,axis=0)):
            ka=tuple(np.round(a,7)); kb=tuple(np.round(b,7))
            unique[edge_key(ka,kb)]=np.array([a,b])
    ax.add_collection(LineCollection(list(unique.values()),colors='white',
                                    linewidths=2.2,capstyle='round',zorder=1))
    ax.text(*xy(-4.65,55.1),'SCOTLAND',fontsize=13,weight='bold',color='#216b83',alpha=.75)
    ax.text(*xy(-4.5,52.35),'WALES',fontsize=14,weight='bold',color='#216b83',alpha=.75)

def sector(origin,p):
    dx,dy=p-origin
    if dy>0 and dy>abs(dx)*.4:
        if dx<-.5*dy: return 'NW'
        if dx>.5*dy: return 'NE'
        return 'N'
    if dx<0 and (abs(dy)<abs(dx)*.45 or
                 (np.linalg.norm(p-origin)<.3 and abs(dy)<abs(dx)*1.2)):
        return 'W'
    if dy<0 and abs(dx)<abs(dy)*.48: return 'S'
    if dx>0 and dy<0: return 'SE'
    if dx<0 and dy<0: return 'SW'
    return 'E' if dx>=0 else 'NW'

def offset_rail(points,amount):
    p=np.asarray(points,float)
    normals=[]
    for a,b in zip(p,p[1:]):
        d=norm(b-a); normals.append(np.array([-d[1],d[0]]))
    out=[p[0]]
    for i in range(1,len(p)-1):
        d1=p[i]-p[i-1]; d2=p[i+1]-p[i]
        q1=p[i]+amount*normals[i-1]; q2=p[i]+amount*normals[i]
        det=np.linalg.det(np.array([d1,-d2]).T)
        t=np.linalg.det(np.array([q2-q1,-d2]).T)/det if abs(det)>1e-10 else 0
        out.append(q1+t*d1)
    out.append(p[-1]+amount*normals[-1])
    return np.array(out)

def nearest_spine(spine,dest,sector_name):
    best=(float('inf'),None,None)
    for i,(a,b) in enumerate(zip(spine,spine[1:])):
        v=b-a; t=np.clip(np.dot(dest-a,v)/np.dot(v,v),0,1)
        q=a+t*v; score=np.linalg.norm(dest-q)
        if score<best[0]: best=(score,i,q)
    _,i,q=best
    if sector_name in ('SE','NE','SW','NW') and i==len(spine)-2 and abs(dest[0]-q[0])>.4:
        i=len(spine)-3; q=spine[-2]
    return np.vstack([spine[:i+1],q])

def connect_octilinear(start,end):
    dx,dy=end-start
    if abs(dx)<.035 or abs(dy)<.035: return [end]
    k=min(abs(dx),abs(dy))
    knee=start+np.array([math.copysign(k,dx),math.copysign(k,dy)])
    return [knee,end] if np.linalg.norm(knee-end)>.02 else [end]

def crossings(routes,hub):
    """Count proper route intersections outside the station's hub circle."""
    names=list(routes); result=[]
    for i,a in enumerate(names):
        for b in names[i+1:]:
            p,q=routes[a],routes[b]
            for x,y in zip(p,p[1:]):
                for u,v in zip(q,q[1:]):
                    d=y-x; e=v-u
                    det=d[0]*e[1]-d[1]*e[0]
                    if abs(det)<1e-9: continue
                    r=u-x
                    t=(r[0]*e[1]-r[1]*e[0])/det
                    s=(r[0]*d[1]-r[1]*d[0])/det
                    if 1e-5<t<1-1e-5 and 1e-5<s<1-1e-5 and np.linalg.norm(x+t*d-hub)>.22:
                        result.append((a,b))
    return result

def build_routes(hub,positions,rows):
    o=positions[hub]; groups=defaultdict(list)
    for row in rows: groups[sector(o,positions[row['opponent']])].append(row)
    routes={}; templates={}; lanes={}; group_names={}
    for direction,items in groups.items():
        dests=np.array([positions[r['opponent']] for r in items])
        if direction in ('SE','NE','SW','NW'):
            sx=1 if 'E' in direction else -1
            sy=1 if 'N' in direction else -1
            x=float(np.median(dests[:,0])); elbow=np.array([o[0]+sx*.18,o[1]])
            spine=np.array([o,elbow,(x,o[1]+sy*abs(x-elbow[0])),
                            (x,max(dests[:,1]) if sy>0 else min(dests[:,1]))])
            ordered=sorted(items,key=lambda r:positions[r['opponent']][0],reverse=sx<0)
        elif direction=='S':
            x=float(np.median(dests[:,0])+.08); y=o[1]-.30
            spine=np.array([o,(o[0],y),(x,y-(x-o[0])),(x,min(dests[:,1]))])
            ordered=sorted(items,key=lambda r:(positions[r['opponent']][0],-positions[r['opponent']][1]))
        elif direction=='N':
            x=float(np.median(dests[:,0])); y=o[1]+.25
            spine=np.array([o,(o[0],y),(x,y+abs(x-o[0])),(x,max(dests[:,1]))])
            ordered=sorted(items,key=lambda r:positions[r['opponent']][0])
        elif direction=='W':
            x=float(min(dests[:,0])); spine=np.array([o,(o[0]-.10,o[1]+.10),(x,o[1]+.10)])
            ordered=sorted(items,key=lambda r:-positions[r['opponent']][1])
        else:
            ordered=sorted(items,key=lambda r:positions[r['opponent']][0])
            for row in ordered:
                d=positions[row['opponent']]; dx=d[0]-o[0]
                pts=np.array([o,d])
                routes[row['opponent']]=pts
            continue
        n=len(ordered)
        group_names[direction]=[r['opponent'] for r in ordered]
        for rank,row in enumerate(ordered):
            d=positions[row['opponent']]
            lane=(rank-(n-1)/2)*.055
            if direction=='W':
                center=np.array([o,spine[1],(d[0],spine[-1][1])])
            else:
                center=nearest_spine(spine,d,direction)
            templates[row['opponent']]=(center,d)
            lanes[row['opponent']]=lane
            rail=offset_rail(center,lane)
            routes[row['opponent']]=np.vstack([rail,*connect_octilinear(rail[-1],d)])
    # Discrete lane swaps are a general crossing-reduction rule. No club
    # identity is hard-coded: each trial is scored on the whole route graph.
    score=len(crossings(routes,o))
    for _ in range(5):
        best=None
        for names in group_names.values():
            for i,a in enumerate(names):
                for b in names[i+1:]:
                    ca,da=templates[a]; cb,db=templates[b]
                    la,lb=lanes[a],lanes[b]
                    pa,pb=routes[a],routes[b]
                    qa=offset_rail(ca,lb); qb=offset_rail(cb,la)
                    routes[a]=np.vstack([qa,*connect_octilinear(qa[-1],da)])
                    routes[b]=np.vstack([qb,*connect_octilinear(qb[-1],db)])
                    trial=len(crossings(routes,o))
                    routes[a],routes[b]=pa,pb
                    if trial<score and (best is None or trial<best[0]):
                        best=(trial,a,b)
        if best is None: break
        score,a,b=best
        lanes[a],lanes[b]=lanes[b],lanes[a]
        for name in (a,b):
            c,d=templates[name]; rail=offset_rail(c,lanes[name])
            routes[name]=np.vstack([rail,*connect_octilinear(rail[-1],d)])
    return routes

def smooth_departure(points,hub):
    if len(points)<2: return points
    q=points[1]; d=q-hub
    # A short cubic easing is shared by every sector. It begins under the
    # hub marker, so tracks emerge continuously before reaching full width.
    angle=round(math.atan2(d[1],d[0])/(math.pi/4))*(math.pi/4)
    start_heading=np.array([math.cos(angle),math.sin(angle)])
    end_heading=norm(points[2]-q) if len(points)>2 else norm(d)
    c1=hub+start_heading*.075; c2=q-end_heading*.075
    t=np.linspace(0,1,9)[:,None]
    curve=(1-t)**3*hub+3*(1-t)**2*t*c1+3*(1-t)*t*t*c2+t**3*q
    return np.vstack([curve,points[2:]])

def draw_track(ax,points,color,hub,layer):
    pts=smooth_departure(points,hub)
    # Casings begin beyond the dense hub fan. Track width grows smoothly
    # from inside the station to the regular parallel-lane width.
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))]
    cut=int(np.searchsorted(distance,.30))
    if layer=='casing':
        ax.plot(pts[cut:,0],pts[cut:,1],color=HALO,lw=6.8,solid_joinstyle='round',zorder=2)
        return
    ax.plot(pts[cut:,0],pts[cut:,1],color=color,lw=4.2,solid_joinstyle='round',zorder=3)
    for i in range(cut):
        lw=1.6+2.6*min(1,distance[i]/.30)
        ax.plot(pts[i:i+2,0],pts[i:i+2,1],color=color,lw=lw,
                solid_capstyle='round',zorder=4)

def draw_labels(ax,hub,positions,rows):
    names=list(positions)
    played={r['opponent']:r for r in rows}
    # Candidate bounding boxes are scored against every station and label.
    placed=[]
    for name in sorted(names,key=lambda n:(n!=hub,n not in played,-np.linalg.norm(positions[n]-positions[hub]))):
        p=positions[name]
        if name!=hub and name not in played:
            ax.add_patch(Circle(p,.024,facecolor=HALO,edgecolor='#526478',lw=1.2,zorder=8))
            continue
        radius=.10 if name==hub else .037
        ax.add_patch(Circle(p,radius,facecolor='white',edgecolor=INK,lw=2,zorder=8))
        size=12 if name==hub else 9.4
        width=len(name)*(.048 if name==hub else .039)
        def box(q,align):
            return (q[0] if align=='left' else q[0]-width,
                    q[0]+width if align=='left' else q[0],q[1]-.047,q[1]+.047)
        if name==hub:
            q=p+(.055,.205); align='left'
        else:
            candidates=[(-.075,.125),(-.075,-.105),(.075,.125),(.075,-.105),
                        (-.075,.015),(.075,.015),(-.12,-.16),(.12,-.16)]
            def cost(delta):
                q=p+delta; align='left' if delta[0]>=0 else 'right'; b=box(q,align)
                penalty=np.linalg.norm(delta)
                for other,r in positions.items():
                    if other==name: continue
                    cx=np.clip(r[0],b[0],b[1]); cy=np.clip(r[1],b[2],b[3])
                    if np.linalg.norm(r-[cx,cy])<(.105 if other==hub else .046): penalty+=20
                for v in placed:
                    overlap=max(0,min(b[1],v[1])-max(b[0],v[0]))*max(0,min(b[3],v[3])-max(b[2],v[2]))
                    penalty+=overlap*500
                return penalty
            delta=min(candidates,key=cost); q=p+delta
            align='left' if delta[0]>=0 else 'right'
        placed.append(box(q,align))
        ax.text(q[0],q[1],name.upper(),ha=align,
                va='center',fontsize=size,weight='bold',color=INK,zorder=10,
                path_effects=[pe.withStroke(linewidth=1.25,foreground=HALO)])
        if name in played and played[name]['venue']:
            marker=[p+v for v in ((.085,.08),(-.085,.08),(.085,-.09),(-.085,-.09))]
            q=min(marker,key=lambda q:sum(10 for other,r in positions.items()
                                        if other!=name and np.linalg.norm(q-r)<(.12 if other==hub else .055)))
            ax.text(q[0],q[1],played[name]['venue'][0],fontsize=8,
                    weight='bold',color='#304357',zorder=10)

def render(hub='Man City',demo=False):
    positions={n:data.club_xy(n,9) for n in data.CLUBS}
    positions.update({n:xy(*v) for n,v in data.UNPLAYED_07.items()})
    demo_targets=('Man City','Man United','Liverpool','Everton',
                  'Aston Villa','Coventry','Nottm Forest')
    rows=data.load_matches() if not demo else [dict(opponent=n,result='D',venue='')
                                           for n in demo_targets]
    routes=build_routes(hub,positions,rows)
    fig,ax=plt.subplots(figsize=(10.8,16.0),dpi=150)
    fig.patch.set_facecolor(SEA);ax.set_facecolor(SEA)
    ax.set_xlim(.1,5.15);ax.set_ylim(-.55,6.95);ax.set_aspect('equal');ax.axis('off')
    draw_geography(ax)
    for layer in ('casing','colour'):
        for row in rows:
            draw_track(ax,routes[row['opponent']],COLORS[row['result']],positions[hub],layer)
    draw_labels(ax,hub,positions,rows)
    ax.add_patch(Rectangle((.1,6.08),5.05,.87,color=SEA,zorder=11))
    ax.add_patch(Rectangle((.1,-.55),5.05,.43,color=SEA,zorder=11))
    ax.text(.23,6.8,hub.upper(),fontsize=30,weight='heavy',color=INK,zorder=12)
    ax.text(.25,6.43,'2026/27 PREMIER LEAGUE RESULTS NETWORK' if not demo else
            'LAYOUT STRESS TEST · NEUTRAL ROUTES',fontsize=12,weight='bold',color='#425367',zorder=12)
    ax.text(.25,6.2,'VERIFIED THROUGH 26 NOV 2026' if not demo else
            'NO ARSENAL RESULTS ARE IMPLIED',fontsize=9.5,color='#526478',zorder=12)
    if demo:
        ax.plot([.25,.55],[-.28,-.28],color=COLORS['D'],lw=4.3,zorder=12)
        ax.text(.62,-.28,'NEUTRAL ROUTE · LAYOUT TEST ONLY',va='center',fontsize=10.3,
                weight='bold',color=INK,zorder=12)
    else:
        for x,code,label in [(.25,'W','WIN'),(1.63,'D','DRAW'),(3.02,'L','LOSS')]:
            ax.plot([x,x+.28],[-.28,-.28],color=COLORS[code],lw=4.3,zorder=12)
            ax.text(x+.35,-.28,label,va='center',fontsize=10.3,weight='bold',color=INK,zorder=12)
    footer=('Neutral routes test the layout; they are not match results' if demo else
            'H / A = City home / away  ·  small dots = unplayed')
    ax.text(.25,-.45,footer,fontsize=8.5,color='#526478',zorder=12)
    target=OUT/('10_v2_rule_based_man_city.png' if not demo else '10_v2_arsenal_cluster_test.png')
    fig.savefig(target,dpi=150,bbox_inches='tight',pad_inches=.1,facecolor=SEA)
    plt.close(fig)
    return target,routes

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo-arsenal',action='store_true',
                        help='draw a neutral seven-route cluster test, not results')
    parser.add_argument('--check',action='store_true',
                        help='check City and Arsenal routes and shared borders')
    args=parser.parse_args()
    if args.check:
        countries=topological_countries()
        edges=defaultdict(set)
        for name,p in countries:
            for a,b in zip(p,np.roll(p,-1,axis=0)):
                edges[edge_key(tuple(np.round(a,7)),tuple(np.round(b,7)))].add(name)
        assert sum(v=={'England','Scotland'} for v in edges.values())>0
        assert sum(v=={'England','Wales'} for v in edges.values())>0
        positions={n:data.club_xy(n,9) for n in data.CLUBS}
        positions.update({n:xy(*v) for n,v in data.UNPLAYED_07.items()})
        city=build_routes('Man City',positions,data.load_matches())
        cluster=('Man City','Man United','Liverpool','Everton',
                 'Aston Villa','Coventry','Nottm Forest')
        arsenal=build_routes('Arsenal',positions,[{'opponent':n} for n in cluster])
        assert not crossings(city,positions['Man City'])
        assert not crossings(arsenal,positions['Arsenal'])
        print('Shared border edges:',sum(len(v)>1 for v in edges.values()))
        print('City: 11 routes, 0 crossings; Arsenal cluster: 7 routes, 0 crossings')
    print(render()[0])
    if args.demo_arsenal:
        print(render('Arsenal',demo=True)[0])