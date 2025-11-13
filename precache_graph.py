"""Pre-cache the road graph to speed up first route request.

Run this once to download and cache the road network for your area.
Subsequent route requests will be instant.
"""
import pandas as pd
from safety_model import SafetyModel
from osmnx_routing import build_graph_for_bbox, annotate_graph_with_safety
import pickle
import os

def precache_graph():
    """Download and cache the road graph for the data area."""
    print("=" * 60)
    print("SafePath - Pre-cache Road Graph")
    print("=" * 60)
    
    # Load data to get bbox
    print("\n1. Loading feature data...")
    df = pd.read_csv("merged_feature_data.csv")
    
    # Use a reasonable bbox around the data center
    center_lat = (df.latitude.max() + df.latitude.min()) / 2.0
    center_lon = (df.longitude.max() + df.longitude.min()) / 2.0
    
    # Small area for faster download (~4km x 4km)
    padding = 0.02
    north = center_lat + padding
    south = center_lat - padding
    east = center_lon + padding
    west = center_lon - padding
    
    print(f"   Center: {center_lat:.4f}, {center_lon:.4f}")
    print(f"   Bbox: N={north:.4f}, S={south:.4f}, E={east:.4f}, W={west:.4f}")
    
    # Initialize safety model
    print("\n2. Loading safety model...")
    sm = SafetyModel("merged_feature_data.csv")
    sm.compute_scores()
    print(f"   ✓ Loaded {len(sm.scores)} safety scores")
    
    # Download graph
    print("\n3. Downloading road network from OpenStreetMap...")
    print("   (This will take 30-60 seconds on first run)")
    G = build_graph_for_bbox(north, south, east, west)
    print(f"   ✓ Downloaded {len(G.nodes)} nodes, {len(G.edges)} edges")
    
    # Annotate with safety
    print("\n4. Annotating graph with safety scores...")
    G = annotate_graph_with_safety(G, sm)
    print("   ✓ Graph annotated")
    
    # Save to cache
    cache_file = "cached_road_graph.pkl"
    print(f"\n5. Saving to cache file: {cache_file}")
    with open(cache_file, 'wb') as f:
        pickle.dump({
            'graph': G,
            'bounds': (north, south, east, west),
            'center': (center_lat, center_lon)
        }, f)
    
    file_size = os.path.getsize(cache_file) / (1024 * 1024)  # MB
    print(f"   ✓ Saved ({file_size:.1f} MB)")
    
    print("\n" + "=" * 60)
    print("✓ Pre-caching complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. The cached graph will be automatically loaded by app.py")
    print("  2. Subsequent route requests will be instant (no download)")
    print("  3. Run 'python app.py' to start the server")
    print()

if __name__ == '__main__':
    precache_graph()
