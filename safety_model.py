import math
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def haversine_meters(lon1, lat1, lon2, lat2):
    # Returns distance in meters between two lat/lon points
    R = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class SafetyModel:
    """Rule-based safety scorer for spatial analysis points.

    This class loads `merged_feature_data.csv`, computes a normalized safety
    score per analysis point using configurable weights, and exposes helpers
    for scoring locations and building a cost graph for routing.
    """

    def __init__(self, csv_path: str = "merged_feature_data.csv"):
        self.df = pd.read_csv(csv_path)
        # Ensure lon/lat exist
        assert "longitude" in self.df.columns and "latitude" in self.df.columns, "CSV must contain longitude/latitude"

        # Prepare KDTree for nearest-point lookup
        self._coords = np.vstack([self.df["longitude"].values, self.df["latitude"].values]).T
        self._tree = cKDTree(self._coords)
        self.scores = None

    def compute_scores(self, weights: Dict[str, float] = None):
        """Compute a normalized safety score per point.

        weights: mapping of feature groups to weights. Reasonable defaults are
        provided but you can override.
        """
        if weights is None:
            weights = {
                "streetlight": 1.0,  # closer/bigger count => safer
                "police": 1.5,
                "station": 0.5,
                "nightlife": -0.7,  # more nightlife density -> slightly less safe at night
            }

        df = self.df.copy()

        # Derive simple features that are present in the merged CSV.
        # Use distance-to-nearest as an inverse safety indicator and counts as direct.
        # For missing columns, default neutral values.
        def safe_get(col, default=0.0):
            return df[col] if col in df.columns else pd.Series(default, index=df.index)

        dist_light = safe_get("distance_to_nearest_streetlight").fillna(9999.0).astype(float)
        count_light = safe_get("count_of_nearby_streetlight_500m_approx").fillna(0).astype(float)

        dist_police = safe_get("distance_to_nearest_policestation").fillna(9999.0).astype(float)
        count_police = safe_get("count_of_nearby_policestation_500m_approx").fillna(0).astype(float)

        dist_station = safe_get("distance_to_nearest_transportstation").fillna(9999.0).astype(float)
        count_station = safe_get("count_of_nearby_transportstation_500m_approx").fillna(0).astype(float)

        # Nightlife counts (higher may reduce safety at night)
        nightlife_cols = [c for c in df.columns if c.startswith("count_") and c not in [
            "count_of_nearby_streetlight_500m_approx",
            "count_of_nearby_policestation_500m_approx",
            "count_of_nearby_transportstation_500m_approx",
        ]]
        nightlife_count = df[nightlife_cols].sum(axis=1) if nightlife_cols else pd.Series(0, index=df.index)

        # Convert degree-based distances (from original script) to a proxy metric (smaller is better)
        # The original script stored distances in degrees; treat them as small numbers and invert.
        # We use normalized components to combine them safely.
        comp_light = (1.0 / (1.0 + dist_light)) + (count_light * 0.01)
        comp_police = (1.0 / (1.0 + dist_police)) + (count_police * 0.1)
        comp_station = (1.0 / (1.0 + dist_station)) + (count_station * 0.02)
        comp_nightlife = nightlife_count

        # Combine with weights
        raw_score = (
            weights["streetlight"] * comp_light
            + weights["police"] * comp_police
            + weights["station"] * comp_station
            + weights["nightlife"] * comp_nightlife
        )

        # Normalize to 0-1
        minv = raw_score.min()
        maxv = raw_score.max()
        if maxv - minv <= 0:
            norm = np.ones_like(raw_score)
        else:
            norm = (raw_score - minv) / (maxv - minv)

        self.scores = pd.Series(norm, index=df.index)
        return self.scores

    def score_location(self, lon: float, lat: float) -> float:
        """Return interpolated safety score for a lon/lat by nearest analysis point."""
        if self.scores is None:
            raise RuntimeError("Call compute_scores() first")
        _, idx = self._tree.query([lon, lat], k=1)
        return float(self.scores.iloc[idx])

    def nearest_index(self, lon: float, lat: float) -> int:
        _, idx = self._tree.query([lon, lat], k=1)
        return int(idx)


if __name__ == "__main__":
    m = SafetyModel()
    s = m.compute_scores()
    print("Computed safety scores for", len(s), "points")
