import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import os
import math
from scipy.spatial import cKDTree

# --- Configuration ---
# File names of the uploaded GeoJSON datasets
STREET_LIGHT_FILE = "street_light.geojson"
NIGHT_LIFE_FILE = "night_life.geojson"
STATION_FILE = "station.geojson"
POLICE_STATION_FILE = "police_station.geojson"
OUTPUT_CSV_FILE = "merged_feature_data.csv"

# Define the central geographical area of interest (e.g., Delhi coordinates)
# This will be used to filter out irrelevant data points outside the main region.
# Based on the coordinates observed in the data (around 77.x longitude, 28.x latitude)
CENTRAL_LONGITUDE_MIN = 76.5
CENTRAL_LONGITUDE_MAX = 77.5
CENTRAL_LATITUDE_MIN = 28.4
CENTRAL_LATITUDE_MAX = 28.9

def load_and_clean_data(filepath, category_name):
    """Loads GeoJSON, filters based on coordinates, and extracts core features."""
    try:
        # 1. Load the data using geopandas
        gdf = gpd.read_file(filepath)

        # 2. Extract Coordinates (Longitude, Latitude)
        # Coordinates are stored as (Longitude, Latitude) in GeoJSON
        gdf['longitude'] = gdf.geometry.x
        gdf['latitude'] = gdf.geometry.y

        # 3. Filter out irrelevant data points outside the defined geographical box
        print(f"Initial {category_name} record count: {len(gdf)}")
        gdf = gdf[
            (gdf['longitude'] >= CENTRAL_LONGITUDE_MIN) &
            (gdf['longitude'] <= CENTRAL_LONGITUDE_MAX) &
            (gdf['latitude'] >= CENTRAL_LATITUDE_MIN) &
            (gdf['latitude'] <= CENTRAL_LATITUDE_MAX)
        ].copy() # Use .copy() to avoid SettingWithCopyWarning
        print(f"Filtered {category_name} record count: {len(gdf)}")


        # 4. Select and Rename relevant columns for standardization
        # We also create a unique identifier combining the source file and original ID
        cols_to_keep = ['longitude', 'latitude']

        # Some GeoJSON files (and thus GeoDataFrames) store feature attributes
        # as a nested 'properties' dict per row. Others unpack properties into
        # top-level columns. Normalize both cases by creating a 'props'
        # Series of dicts we can safely query.
        if 'properties' in gdf.columns and gdf['properties'].apply(lambda x: isinstance(x, dict)).any():
            props = gdf['properties']
        else:
            # Build a dict of remaining columns per row (excluding geometry and coords)
            exclude = set(['geometry', 'longitude', 'latitude'])
            prop_cols = [c for c in gdf.columns if c not in exclude]
            # If there are no property-like columns, create empty dicts
            if not prop_cols:
                props = pd.Series([{} for _ in range(len(gdf))], index=gdf.index)
            else:
                props = gdf[prop_cols].apply(lambda row: {k: v for k, v in row.items() if pd.notna(v)}, axis=1)

        # Add relevant domain-specific features
        if category_name == 'StreetLight':
            gdf['street_light_type'] = props.apply(
                lambda p: (p.get('lamp_type') or p.get('lamp:type') or 'unknown').upper() if isinstance(p, dict) else 'UNKNOWN'
            )
            cols_to_keep.append('street_light_type')

        elif category_name == 'NightLife':
            gdf['nightlife_amenity'] = props.apply(
                lambda p: p.get('amenity', 'restaurant') if isinstance(p, dict) else 'restaurant'
            ).astype(str).str.lower()
            gdf['nightlife_name'] = props.apply(lambda p: p.get('name', '') if isinstance(p, dict) else '')
            cols_to_keep.extend(['nightlife_amenity', 'nightlife_name'])

        elif category_name == 'PoliceStation':
            gdf['police_station_name'] = props.apply(lambda p: p.get('name', 'Police Post') if isinstance(p, dict) else 'Police Post')
            cols_to_keep.append('police_station_name')

        elif category_name == 'Station':
            gdf['station_type'] = props.apply(
                lambda p: (p.get('public_transport') or p.get('railway') or 'other_station').lower() if isinstance(p, dict) else 'other_station'
            )
            gdf['station_name'] = props.apply(lambda p: p.get('name', '') if isinstance(p, dict) else '')
            cols_to_keep.extend(['station_type', 'station_name'])

        # Ensure returned object is a GeoDataFrame with a geometry column
        result = gdf[cols_to_keep].copy()
        try:
            result = gpd.GeoDataFrame(result, geometry=gpd.points_from_xy(result.longitude, result.latitude))
        except Exception:
            # If geometry creation fails, return the DataFrame as-is (caller should handle)
            pass
        return result

    except Exception as e:
        print(f"Error loading or processing {filepath}: {e}")
        return gpd.GeoDataFrame({
            'longitude': [], 'latitude': []
        }, geometry=gpd.points_from_xy([], []))


def run_data_pipeline():
    """Executes the full pipeline: loads data, merges, performs basic feature engineering, and exports to CSV."""
    
    # 1. Load and process all datasets
    street_lights_gdf = load_and_clean_data(STREET_LIGHT_FILE, 'StreetLight')
    night_life_gdf = load_and_clean_data(NIGHT_LIFE_FILE, 'NightLife')
    stations_gdf = load_and_clean_data(STATION_FILE, 'Station')
    police_stations_gdf = load_and_clean_data(POLICE_STATION_FILE, 'PoliceStation')

    # 2. Create the Master Grid/Analysis Points
    # For proximity analysis, we need a baseline of locations. 
    # Since the user implied they are preparing data for an ML model, we'll assume 
    # the target variable depends on location, and generate a representative grid.
    # The ultimate ML model would likely use crime incidents or property locations 
    # as its primary locations for feature creation. For this example, we'll use 
    # the union of all coordinates as a proxy for "analysis points".

    all_coords = pd.concat([
        street_lights_gdf[['longitude', 'latitude']],
        night_life_gdf[['longitude', 'latitude']],
        stations_gdf[['longitude', 'latitude']],
        police_stations_gdf[['longitude', 'latitude']]
    ]).drop_duplicates().reset_index(drop=True)

    if all_coords.empty:
        print("Error: No data points remaining after filtering. Cannot proceed.")
        return

    # Create a GeoDataFrame for the analysis points
    analysis_points = gpd.GeoDataFrame(
        all_coords,
        geometry=gpd.points_from_xy(all_coords.longitude, all_coords.latitude)
    )
    
    print(f"\nTotal unique spatial analysis points created: {len(analysis_points)}")

    # 3. Feature Engineering: Proximity Features (Distance to nearest amenity)
    
    # Haversine distance function (simplified for approximate calculation in degrees)
    # The actual distance calculation should ideally use a proper projection system, 
    # but for simplicity in a quick script, we use a crude approximation in Python.
    
    # Define a custom metric function to be passed to cKDTree for proximity search.
    # Using 'euclidean' on raw lat/lon is fast but inaccurate, so we warn against it
    # in real-world ML and provide placeholders for calculated distances.
    # For this exercise, we will calculate the Euclidean distance on (lon, lat) 
    # and rename the output column to imply proximity/count for demonstration.

    def calculate_proximity_features(source_gdf, target_gdf, target_name):
        """Calculates proximity features (distance and count) for a target feature set."""
        if target_gdf.empty:
            print(f"Warning: {target_name} data is empty. Skipping proximity calculation.")
            analysis_points[f'distance_to_{target_name.lower()}'] = math.nan
            analysis_points[f'count_of_nearby_{target_name.lower()}'] = 0
            return

        # Calculate distance to nearest feature in target_gdf
        # Using cKDTree with standard Euclidean distance on unprojected coordinates 
        # (WARNING: this is highly inaccurate for real distance/meters/km)
        from scipy.spatial import cKDTree
        
        # Extract coordinates for use in cKDTree
        source_coords = list(zip(source_gdf.geometry.x, source_gdf.geometry.y))
        target_coords = list(zip(target_gdf.geometry.x, target_gdf.geometry.y))
        
        tree = cKDTree(target_coords)
        
        # Query for the distance to the 1 nearest neighbor
        distances, indices = tree.query(source_coords, k=1)
        
        # Add distance feature to the analysis_points DataFrame
        analysis_points[f'distance_to_nearest_{target_name.lower()}'] = distances
        
        # Calculate count of nearby features within a small radius (e.g., 0.005 degrees ~ 500m at equator)
        # Again, this is an approximation due to unprojected data
        radius = 0.005  
        counts = tree.query_ball_point(source_coords, r=radius, return_length=True)
        analysis_points[f'count_of_nearby_{target_name.lower()}_{int(radius*100000)}m_approx'] = counts
    
    
    print("\n--- Generating Proximity Features (Distance in Approx. Degrees) ---")
    calculate_proximity_features(analysis_points, street_lights_gdf, "StreetLight")
    calculate_proximity_features(analysis_points, night_life_gdf, "NightLifeVenue")
    calculate_proximity_features(analysis_points, stations_gdf, "TransportStation")
    calculate_proximity_features(analysis_points, police_stations_gdf, "PoliceStation")
    
    # 4. Feature Engineering: Categorical Counts (Example for NightLife)
    # Count the number of different types of night life amenities within the radius
    nightlife_types = night_life_gdf['nightlife_amenity'].unique()
    
    if len(night_life_gdf) > 0:
        print("\n--- Generating Categorical Density Features (NightLife) ---")
        
        # Prepare night_life data geometry and types for spatial join or aggregation
        night_life_points = gpd.GeoDataFrame(
            night_life_gdf[['nightlife_amenity']],
            geometry=gpd.points_from_xy(night_life_gdf.longitude, night_life_gdf.latitude)
        )
        
        # Set spatial index for efficient querying
        night_life_points = night_life_points.set_index(night_life_points.index)
        
        # Perform spatial join (within a large radius for demo, warning applies)
        # Using a very generous buffer (e.g., 1 degree radius approx 111km - for demonstration purposes)
        # In a real scenario, convert units to meters and use a sensible radius like 500m or 1km
        BUFFER_SIZE = 0.01 
        
        # Project data for proper buffer/overlay if time allowed, but sticking to unprojected for simplicity
        
        # Create a spatial index for the query point 
        analysis_points_w_index = analysis_points.set_index(analysis_points.index)
        
        for amenity_type in nightlife_types:
            type_gdf = night_life_points[night_life_points['nightlife_amenity'] == amenity_type]
            
            if not type_gdf.empty:
                # Use query_bulk in cKDTree to count points within radius for specific amenity
                target_coords = list(zip(type_gdf.geometry.x, type_gdf.geometry.y))
                tree = cKDTree(target_coords)
                source_coords = list(zip(analysis_points_w_index.geometry.x, analysis_points_w_index.geometry.y))
                
                counts = tree.query_ball_point(source_coords, r=BUFFER_SIZE, return_length=True)
                
                column_name = f'count_{amenity_type}'
                analysis_points_w_index[column_name] = counts
                print(f"  - Added feature: {column_name}")
            
        analysis_points = analysis_points_w_index.copy()
            
    # 5. Final Cleanup and Export
    
    # Drop the internal geometry column and any temporary indices before export
    final_df = pd.DataFrame(analysis_points).drop(columns=['geometry'], errors='ignore')
    
    # Reorder columns: Coordinates first
    cols = ['longitude', 'latitude'] + [col for col in final_df.columns if col not in ['longitude', 'latitude']]
    final_df = final_df[cols]

    # Fill NaN/empty strings for cleaner output
    final_df = final_df.fillna(0)
    
    # Export to CSV
    final_df.to_csv(OUTPUT_CSV_FILE, index=False)
    
    print(f"\nSuccessfully generated {OUTPUT_CSV_FILE} with {len(final_df)} records.")
    print("\n--- Example Schema (First 5 Rows) ---")
    # to_markdown requires the optional 'tabulate' package; fall back to plain text if missing
    try:
        print(final_df.head().to_markdown(index=False))
    except Exception:
        print(final_df.head().to_string(index=False))


# Execute the pipeline
if __name__ == '__main__':
    run_data_pipeline()
    
# In a full-fledged ML pipeline, especially with spatial data, careful projection 
# and hyperparameter tuning for radius searches (like kNN, KD-Tree) would be critical.
# The current script assumes non-projected input for simplicity in this environment, 
# and the distance calculation should be treated as an approximation.