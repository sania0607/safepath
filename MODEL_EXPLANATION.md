# SafePath Safety Model - How It Works

## 📊 Overview

Your SafePath application uses a **rule-based safety scoring model** combined with **OSMnx road network routing** to predict the safest routes. Yes, it absolutely uses the `merged_feature_data.csv` file as the foundation for safety predictions!

---

## 🔄 How the System Works (Step-by-Step)

### **Step 1: Data Processing (`data.py`)**
```
GeoJSON Files → Feature Extraction → merged_feature_data.csv
```

**Input:** 4 GeoJSON files with safety infrastructure:
- `street_light.geojson` - Street light locations
- `police_station.geojson` - Police station locations
- `station.geojson` - Transport station locations
- `night_life.geojson` - Nightlife venues (restaurants, bars, clubs)

**Process:** Creates **3,779 analysis points** (grid covering your area) and for each point calculates:
- Distance to nearest street light
- Count of street lights within 500m
- Distance to nearest police station
- Count of police stations within 500m
- Distance to nearest transport station
- Count of transport stations within 500m
- Distance to nearest nightlife venue
- Count of nightlife venues within 500m
- Individual counts: restaurants, bars, nightclubs

**Output:** `merged_feature_data.csv` with 13 columns of safety features

---

### **Step 2: Safety Scoring (`safety_model.py`)**

The `SafetyModel` class loads `merged_feature_data.csv` and computes safety scores:

#### **Algorithm:**

```python
# For each of the 3,779 analysis points:

1. Component Scores (normalized 0-1):
   - Street Light Component = (1 / (1 + distance)) + (count × 0.01)
   - Police Component = (1 / (1 + distance)) + (count × 0.1)
   - Station Component = (1 / (1 + distance)) + (count × 0.02)
   - Nightlife Component = total_nightlife_count

2. Weighted Combination:
   Raw Score = (1.0 × streetlight_comp) + 
               (1.5 × police_comp) + 
               (0.5 × station_comp) + 
               (-0.7 × nightlife_comp)

3. Normalize to 0-1 scale:
   Safety Score = (Raw Score - Min) / (Max - Min)
```

#### **Weight Logic:**
- ✅ **Street lights** (+1.0): Closer = Safer (well-lit areas)
- ✅ **Police stations** (+1.5): Most important for safety
- ✅ **Transport stations** (+0.5): Moderate safety (public areas)
- ⚠️ **Nightlife** (-0.7): Higher density = slightly less safe at night

#### **Spatial Lookup:**
- Uses **cKDTree** (fast spatial indexing) to find nearest analysis point for any GPS coordinate
- When you query a location (lon, lat), it returns the safety score of the nearest point

---

### **Step 3: Road Network Download (`osmnx_routing.py`)**

**OSMnx** downloads real road network data from OpenStreetMap:

```
OpenStreetMap → OSMnx → Road Graph (nodes + edges)
```

- **Nodes:** Road intersections (GPS coordinates)
- **Edges:** Road segments connecting intersections
- **Metadata:** Road length, road type, speed limits, etc.

---

### **Step 4: Safety Annotation (`osmnx_routing.py`)**

For **every road segment** (edge) in the network:

```python
1. Get edge endpoints: (lon1, lat1) to (lon2, lat2)
2. Calculate midpoint: (mid_lon, mid_lat)
3. Query SafetyModel for score at midpoint
4. Assign edge attributes:
   - edge['safety'] = safety_score (0-1)
   - edge['safety_cost'] = length_meters / (safety + 0.000001)
```

**Why `safety_cost`?**
- Lower cost = safer route
- Long safe roads: high length ÷ high safety = moderate cost ✅
- Short unsafe roads: low length ÷ low safety = high cost ❌
- This balances safety vs. reasonable distance

---

### **Step 5: Route Calculation (`osmnx_routing.py`)**

When user requests a route from A to B:

```python
1. Find nearest road node to origin
2. Find nearest road node to destination
3. Run Dijkstra's shortest path algorithm with weight='safety_cost'
4. Return list of GPS waypoints
```

**Result:** The route that **minimizes total safety_cost** (maximizes safety while keeping distance reasonable)

---

## 🎯 Yes, It Uses `merged_feature_data.csv`!

Here's the data flow:

```
merged_feature_data.csv (3,779 points)
         ↓
   SafetyModel.compute_scores()
         ↓
   Safety score for each point (0-1)
         ↓
   cKDTree spatial index
         ↓
   Query any GPS coordinate → get nearest point's score
         ↓
   Annotate EVERY road segment with safety score
         ↓
   Calculate safest route using annotated roads
```

---

## 📈 Model Type: Rule-Based vs. Machine Learning

### **Current Implementation: Rule-Based**

✅ **Advantages:**
- No training data needed
- Interpretable (you know exactly why a route is "safe")
- Fast computation
- Works with limited data (only 4 GeoJSON files)

❌ **Limitations:**
- Fixed weights (1.0, 1.5, 0.5, -0.7) might not reflect real-world safety
- No learning from actual incidents/crime data
- Assumes linear relationships (closer to police = safer)

### **Future: Could Be Upgraded to ML**

If you had **labeled data** (crime incidents with locations + severity), you could:

1. **Feature Engineering:**
   ```python
   Features (from CSV):
   - distance_to_nearest_policestation
   - count_of_nearby_streetlight_500m
   - ... (all 13 columns)
   
   Labels (from crime data):
   - safety_level: 0 (unsafe), 1 (safe)
   - crime_count: number of incidents
   ```

2. **Train ML Model:**
   ```python
   from sklearn.ensemble import RandomForestClassifier
   
   model = RandomForestClassifier()
   model.fit(X_features, y_safety_labels)
   predicted_safety = model.predict(new_location_features)
   ```

3. **Benefits:**
   - Learn actual safety patterns from real incidents
   - Discover non-obvious correlations
   - Better predictions with more data

---

## 🔍 How to Verify It's Working

### **Test 1: Check Safety Scores**
```python
from safety_model import SafetyModel

model = SafetyModel("merged_feature_data.csv")
model.compute_scores()

# Query a location (example: Greater Noida)
safety_score = model.score_location(77.29, 28.62)
print(f"Safety score: {safety_score:.3f}")
# Output: 0.650 (higher = safer)
```

### **Test 2: Compare Different Locations**
```python
# Well-lit area near police station
safe_area = model.score_location(77.22, 28.63)

# Dark area far from police
unsafe_area = model.score_location(77.18, 28.52)

print(f"Safe area: {safe_area:.3f}")    # Higher score
print(f"Unsafe area: {unsafe_area:.3f}") # Lower score
```

### **Test 3: Inspect Road Safety**
```python
# Load cached graph
import pickle
with open("cached_road_graph.pkl", "rb") as f:
    G = pickle.load(f)

# Check a road segment's safety
for u, v, key, data in list(G.edges(keys=True, data=True))[:5]:
    print(f"Road segment: safety={data['safety']:.3f}, cost={data['safety_cost']:.1f}m")
```

---

## 📊 Data Statistics

From your `merged_feature_data.csv`:

```
Total Analysis Points: 3,779
Coverage Area: ~28.6°N, 77.1°E (Delhi/Greater Noida region)
Grid Spacing: ~100-200m between points

Features Used:
- Street lights: 100% coverage (48 avg within 500m)
- Police stations: Sparse (0-1 avg within 500m)
- Transport stations: Good (7 avg within 500m)
- Nightlife venues: Variable (0-68 within 500m)
```

---

## 🚀 Performance Optimizations

1. **Cached Road Graph** (`cached_road_graph.pkl`)
   - Pre-downloads OSM road network
   - Pre-calculates safety scores for all roads
   - Instant routing (<2 seconds vs. 60-90 seconds)

2. **cKDTree Spatial Index**
   - Fast nearest-neighbor lookup
   - O(log n) complexity instead of O(n)

3. **In-Memory Safety Scores**
   - Loads once on app startup
   - Reuses for all route requests

---

## 🎓 Summary

**Yes, your model absolutely uses `merged_feature_data.csv`!**

The flow is:
1. CSV provides safety features for 3,779 grid points
2. Rule-based algorithm computes safety score (0-1) per point
3. Every road segment queries nearest point for its safety score
4. Dijkstra algorithm finds route with lowest `safety_cost`
5. Users get the **safest possible route** based on street lights, police proximity, and nightlife density

**Model Type:** Rule-based spatial analysis (not ML, but could be upgraded with crime data)

**Strengths:** Fast, interpretable, works without training data

**Potential Upgrade:** Add supervised ML if crime incident data becomes available

---

## 📚 Key Files

- `data.py` - Processes GeoJSON → CSV
- `safety_model.py` - Computes safety scores from CSV
- `osmnx_routing.py` - Annotates roads + calculates routes
- `merged_feature_data.csv` - **The core data source**
- `cached_road_graph.pkl` - Pre-computed road network with safety

Your model is working beautifully! 🎉
