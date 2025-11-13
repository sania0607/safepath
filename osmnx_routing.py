"""OSMnx-based safest routing utilities.

This module uses OSMnx to build a drivable road graph for a bounding box or
around a point, maps safety scores from `safety_model.SafetyModel` onto edges,
and computes the safest route between two (lon, lat) coordinates.

Notes:
- This requires `osmnx` and its native dependencies. On Windows it's easiest
  to install via conda (conda-forge). See README or the project's
  instructions for details.
"""
from typing import Tuple, List

import networkx as nx
import pandas as pd

import osmnx as ox

from safety_model import SafetyModel, haversine_meters


def build_graph_for_bbox(north: float, south: float, east: float, west: float, network_type: str = "drive"):
    """Download an OSMnx graph for the bbox and return it (projected to UTM).

    The returned graph has edge 'length' attributes in meters (OSMnx default).
    """
    # Different osmnx versions expose slightly different APIs for downloading
    # graphs. To be robust, try graph_from_point (widely available) using the
    # bbox center and a radius that covers the bbox. Fall back to graph_from_bbox
    # with keyword args if the point-based API is unavailable.
    import math

    center_lon = (east + west) / 2.0
    center_lat = (north + south) / 2.0

    # approximate radius (meters) as max haversine distance from center to bbox corners
    corner1 = (west, north)
    corner2 = (east, south)
    r1 = haversine_meters(center_lon, center_lat, corner1[0], corner1[1])
    r2 = haversine_meters(center_lon, center_lat, corner2[0], corner2[1])
    radius_m = int(math.ceil(max(r1, r2))) + 50

    try:
        # ox.graph_from_point expects a center (lat, lon) tuple in many versions
        G = ox.graph_from_point((center_lat, center_lon), dist=radius_m, network_type=network_type)
        return G
    except Exception:
        try:
            G = ox.graph_from_bbox(north=north, south=south, east=east, west=west, network_type=network_type)
            return G
        except Exception:
            raise


def annotate_graph_with_safety(G: nx.MultiDiGraph, sm: SafetyModel, eps: float = 1e-6) -> nx.MultiDiGraph:
    """Assign safety score and safety-weighted cost to each edge.

    For each edge, sample the midpoint in lon/lat (unproject), query the
    SafetyModel for a safety score, then set edge['safety'] and
    edge['safety_cost'] = length_meters / (safety + eps).
    """
    # Work with an unprojected (lat/lon) point for querying safety_model which
    # expects lon/lat. We'll convert node coordinates back to lon/lat using
    # the graph's node attributes (x,y are projected coords). Use ox.project_graph
    # earlier so lengths are in meters; we need to inverse-project nodes to lon/lat.
    # ox.project_graph stores 'x' and 'y' in the node attributes; we can use
    # ox.projection.project_geometry/inverse_project_graph — but a simpler
    # approach: create a graph in lat/lon first then compute lengths via
    # ox.add_edge_lengths after projection. To keep this single function safe,
    # we will attempt to get lat/lon from node attribute 'x'/'y' via
    # ox.projection.transform_geometry if available.

    # For each edge, compute midpoint in lon/lat using node x/y (lon/lat for latlon graphs)
    for u, v, key, data in G.edges(keys=True, data=True):
        # Node coordinates
        lon_u = G.nodes[u].get("x")
        lat_u = G.nodes[u].get("y")
        lon_v = G.nodes[v].get("x")
        lat_v = G.nodes[v].get("y")

        if None in (lon_u, lat_u, lon_v, lat_v):
            # If coordinates missing, set neutral safety and small cost
            score = 0.5
            length_m = data.get("length", 1.0)
        else:
            mid_lon = (lon_u + lon_v) / 2.0
            mid_lat = (lat_u + lat_v) / 2.0
            score = sm.score_location(mid_lon, mid_lat)
            length_m = haversine_meters(lon_u, lat_u, lon_v, lat_v)

        data["safety"] = float(score)
        data["safety_cost"] = float(length_m / (score + eps))

    return G


def safest_route_on_graph(G: nx.MultiDiGraph, origin: Tuple[float, float], destination: Tuple[float, float]) -> List[Tuple[float, float]]:
    """Compute safest route on an OSMnx graph between two lon/lat points.

    origin and destination are (lon, lat). Returns a list of (lon, lat) nodes.
    """
    # Find nearest node (graph should be in lat/lon for nearest_nodes)
    # Use ox.distance.nearest_nodes which expects graph in lat/lon and x=lon,y=lat
    try:
        orig_node = ox.distance.nearest_nodes(G, origin[0], origin[1])
        dest_node = ox.distance.nearest_nodes(G, destination[0], destination[1])
    except Exception:
        # Fallback: attempt older API
        orig_node = ox.nearest_nodes(G, origin[0], origin[1])
        dest_node = ox.nearest_nodes(G, destination[0], destination[1])

    try:
        path = nx.shortest_path(G, source=orig_node, target=dest_node, weight="safety_cost")
    except nx.NetworkXNoPath:
        return []

    # Return list of lon/lat coordinates for path
    coords = []
    for n in path:
        node = G.nodes[n]
        lon = node.get("x") if node.get("x") is not None else node.get("lon")
        lat = node.get("y") if node.get("y") is not None else node.get("lat")
        coords.append((float(lon), float(lat)))
    return coords


if __name__ == "__main__":
    # Demo: build graph for a SMALL area around the center of merged_feature_data.csv
    # to avoid long download times. For production, cache the full graph.
    sm = SafetyModel("merged_feature_data.csv")
    sm.compute_scores()
    df = pd.read_csv("merged_feature_data.csv")
    
    # Use a smaller bbox: just 0.02 degrees (~2km) around the center
    center_lat = (df.latitude.max() + df.latitude.min()) / 2.0
    center_lon = (df.longitude.max() + df.longitude.min()) / 2.0
    padding = 0.02
    north = center_lat + padding
    south = center_lat - padding
    east = center_lon + padding
    west = center_lon - padding

    print(f"Downloading OSM graph for small demo area (center: {center_lat:.4f}, {center_lon:.4f})...")
    print("(This downloads ~2-4km area. For full coverage, increase padding or use cached graph.)")
    G = build_graph_for_bbox(north, south, east, west)
    print(f"Graph downloaded: {len(G.nodes)} nodes, {len(G.edges)} edges")
    print("Annotating graph with safety scores...")
    G = annotate_graph_with_safety(G, sm)
    
    # demo origin/destination within the downloaded area
    # Pick two points near the center
    start = (center_lon - 0.01, center_lat - 0.01)
    end = (center_lon + 0.01, center_lat + 0.01)
    
    print(f"Computing safest route from {start} to {end}...")
    path = safest_route_on_graph(G, start, end)
    print(f"Safest path has {len(path)} nodes")
    if path:
        print("First 3 waypoints:", path[:3])
