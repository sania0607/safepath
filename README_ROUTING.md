# SafePath - AI-Powered Safe Routing

SafePath uses geospatial data (street lights, police stations, transport hubs, nightlife venues) to compute safety scores for locations and find the safest routes between two points using OpenStreetMap road networks.

## Features

- **Safety Scoring**: Rule-based model that scores locations based on proximity to safety features (street lights, police stations) and risk factors (nightlife density)
- **Safest Route Calculation**: Uses OSMnx to download real road networks and compute routes that maximize safety while minimizing distance
- **Flask API**: REST API for integrating safe routing into web/mobile apps
- **GeoJSON Support**: Works with GeoJSON feature data and returns routes as GeoJSON LineStrings

## Project Structure

```
Safepath/
├── data.py                     # Pipeline to process GeoJSON and create feature CSV
├── merged_feature_data.csv     # Generated feature data (3779 analysis points)
├── safety_model.py             # Safety scoring model
├── routing.py                  # k-NN graph routing (lightweight, no OSM)
├── osmnx_routing.py           # OSM road network routing (realistic)
├── api.py                      # Flask REST API
├── app.py                      # Main Flask web app
├── requirements.txt            # Python dependencies
└── *.geojson                   # Input GeoJSON datasets
```

## Installation

### Prerequisites
- Python 3.11+ (3.13 works but 3.11 is more stable for geospatial packages)
- Windows: Miniconda (recommended) or pip

### Option A: Using pip (Windows)
```powershell
# Install dependencies
python -m pip install -r requirements.txt

# Note: OSMnx may fail on Windows with pip. If so, use conda (Option B).
```

### Option B: Using Conda (Recommended for Windows)
```powershell
# Create a conda environment with geospatial packages
conda create -n safepath python=3.11 geopandas osmnx scipy networkx -c conda-forge -y

# Activate the environment
conda activate safepath

# Install remaining packages
pip install -r requirements.txt
```

## Quick Start

### 1. Generate Feature Data
Process the GeoJSON files to create `merged_feature_data.csv`:
```powershell
python data.py
```
This creates a CSV with proximity features (distance to nearest street light, police station, etc.) for 3779 analysis points.

### 2. Test Safety Model
```powershell
python safety_model.py
```
Output: `Computed safety scores for 3779 points`

### 3. Test Routing (Small Demo)
```powershell
python osmnx_routing.py
```
This downloads a small OSM road network (~2-4km area) and computes a sample safest path. First run takes 30-60 seconds to download; subsequent runs use cached data.

**Expected output:**
```
Downloading OSM graph for small demo area (center: 28.xxxx, 77.xxxx)...
Graph downloaded: 1234 nodes, 3456 edges
Annotating graph with safety scores...
Computing safest route from (...) to (...)...
Safest path has 42 nodes
First 3 waypoints: [(77.xxx, 28.xxx), ...]
```

### 4. Run Flask API
```powershell
python api.py
```
The API will start on `http://localhost:5000`.

#### API Endpoints

**Health Check**
```bash
GET http://localhost:5000/health
```

**Get Safest Route**
```bash
POST http://localhost:5000/api/safest-route
Content-Type: application/json

{
  "origin": {"lon": 77.290, "lat": 28.622},
  "destination": {"lon": 77.220, "lat": 28.630}
}
```

Response:
```json
{
  "status": "success",
  "route": {
    "type": "LineString",
    "coordinates": [[77.290, 28.622], [77.289, 28.623], ...]
  },
  "waypoints": [[77.290, 28.622], ...],
  "num_nodes": 42
}
```

**Get Safety Score for Location**
```bash
POST http://localhost:5000/api/safety-score
Content-Type: application/json

{
  "lon": 77.290,
  "lat": 28.622
}
```

Response:
```json
{
  "status": "success",
  "lon": 77.290,
  "lat": 28.622,
  "safety_score": 0.73
}
```

## How It Works

### Safety Scoring
The `SafetyModel` computes a normalized safety score (0-1) for each analysis point using:
- **Positive factors** (closer = safer):
  - Distance to nearest street light
  - Count of nearby street lights
  - Distance to nearest police station
  - Count of nearby police stations
  - Distance to nearest transport station
- **Negative factors** (more = less safe at night):
  - Count of nearby nightlife venues (bars, nightclubs)

Weights are configurable in `safety_model.py`.

### Routing
1. **Download Road Network**: OSMnx fetches drivable roads from OpenStreetMap for the specified bounding box
2. **Annotate Edges**: Each road segment gets a safety score (sampled at midpoint) and a cost = `length_meters / (safety_score + epsilon)`
3. **Shortest Path**: Dijkstra's algorithm finds the path that minimizes total safety cost (balancing distance and safety)

### Performance Notes
- **First OSM download**: 30-120 seconds depending on area size and internet speed
- **Cached graphs**: Subsequent runs reuse downloaded graphs (instant)
- **API caching**: The Flask API caches the graph in memory and reuses it if the requested bbox is covered

## Usage in Your App

### JavaScript/Frontend Example
```javascript
async function getSafestRoute(originLon, originLat, destLon, destLat) {
  const response = await fetch('http://localhost:5000/api/safest-route', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: { lon: originLon, lat: originLat },
      destination: { lon: destLon, lat: destLat }
    })
  });
  const data = await response.json();
  
  if (data.status === 'success') {
    // data.route.coordinates is an array of [lon, lat] waypoints
    // Display on a map (Leaflet, Mapbox, Google Maps, etc.)
    return data.route.coordinates;
  } else {
    console.error('Route error:', data.message);
  }
}
```

### Display on Leaflet Map
```javascript
const route = await getSafestRoute(77.290, 28.622, 77.220, 28.630);
const polyline = L.polyline(route.map(c => [c[1], c[0]]), {
  color: 'green',
  weight: 4
}).addTo(map);
```

## Configuration

### Adjust Safety Weights
Edit `safety_model.py`:
```python
weights = {
    "streetlight": 1.0,   # increase to prioritize well-lit areas
    "police": 1.5,        # increase to stay near police presence
    "station": 0.5,
    "nightlife": -0.7     # make more negative to avoid nightlife areas
}
```

### Change Download Area
For production, pre-download and cache a larger graph:
```python
from osmnx_routing import build_graph_for_bbox, annotate_graph_with_safety
from safety_model import SafetyModel
import pickle

# Download full area (one time)
sm = SafetyModel()
sm.compute_scores()
G = build_graph_for_bbox(north=28.9, south=28.4, east=77.5, west=76.5)
G = annotate_graph_with_safety(G, sm)

# Save to disk
with open('road_graph.pkl', 'wb') as f:
    pickle.dump(G, f)
```

Then in `api.py`, load the cached graph instead of downloading on-demand.

## Troubleshooting

### OSMnx Install Fails (Windows)
Use conda:
```powershell
conda install -c conda-forge osmnx
```

### "No route found" Error
- The origin/destination may be outside the downloaded graph bounds
- Increase the `bbox` in the API request or pre-download a larger graph
- Check that coordinates are valid (lon, lat order)

### Slow Graph Download
- Reduce the bounding box size
- Use the smaller demo in `osmnx_routing.py` (0.02° padding)
- After first download, graphs are cached by OSMnx

### Module Import Errors
```powershell
# Ensure all packages are installed
pip install -r requirements.txt

# Or use conda
conda install -c conda-forge --file requirements.txt
```

## Next Steps

- [ ] Add supervised ML model if crime/incident data becomes available
- [ ] Implement time-of-day safety adjustments (day vs night weights)
- [ ] Add user-reported incident integration
- [ ] Cache full road graph for production deployment
- [ ] Add unit tests for safety scoring and routing logic

## License
See `LICENSE` file.

## Credits
- **OSMnx**: Geoff Boeing (OpenStreetMap road network toolkit)
- **GeoPandas**: Geospatial data processing
- **NetworkX**: Graph algorithms
- **Flask**: Web API framework
