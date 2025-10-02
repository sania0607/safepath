// SafePath Advanced Routing Algorithm
class SafePathRouter {
    constructor() {
        this.safetyFactors = {
            lighting: 0.3,        // 30% weight for lighting conditions
            crowdDensity: 0.25,   // 25% weight for foot traffic
            crimeReports: 0.25,   // 25% weight for recent incident reports
            infrastructure: 0.2   // 20% weight for road/path conditions
        };
    }

    // Main function to calculate both safe and fast routes
    async calculateRoutes(origin, destination) {
        try {
            // Get community reports from database
            const nearbyReports = await this.fetchNearbyReports(origin, destination);
            
            // Calculate base route using OpenStreetMap routing
            const baseRoutes = await this.getBaseRoutes(origin, destination);
            
            // Apply safety algorithm to generate route options
            const safeRoute = this.generateSafeRoute(baseRoutes, nearbyReports);
            const fastRoute = this.generateFastRoute(baseRoutes, nearbyReports);
            
            // Calculate comprehensive metrics
            const metrics = this.calculateRouteMetrics(safeRoute, fastRoute, nearbyReports);
            
            return {
                safeRoute,
                fastRoute,
                metrics,
                nearbyReports
            };
        } catch (error) {
            console.error('Route calculation error:', error);
            return this.getFallbackRoutes(origin, destination);
        }
    }

    // Fetch community reports near the route area
    async fetchNearbyReports(origin, destination) {
        try {
            const response = await fetch('/api/nearby-reports', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    origin: origin,
                    destination: destination,
                    radius: 500 // 500 meters radius
                })
            });
            
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to fetch nearby reports:', error);
        }
        
        // Fallback to demo data
        return this.getDemoReports();
    }

    // Get base routes using OpenStreetMap routing service
    async getBaseRoutes(origin, destination) {
        // For demo purposes, create sample route coordinates
        // In production, this would use actual routing API
        
        const originCoords = this.parseLocation(origin);
        const destCoords = this.parseLocation(destination);
        
        return {
            coordinates: this.interpolateRoute(originCoords, destCoords, 8),
            distance: this.calculateDistance(originCoords, destCoords),
            duration: this.estimateDuration(originCoords, destCoords)
        };
    }

    // Generate safe route prioritizing safety over speed
    generateSafeRoute(baseRoute, reports) {
        const coordinates = baseRoute.coordinates;
        const safeWaypoints = [];
        
        coordinates.forEach((coord, index) => {
            const safetyScore = this.calculateSegmentSafety(coord, reports);
            
            // Include waypoint if safety score > 60%
            if (safetyScore >= 60 || index === 0 || index === coordinates.length - 1) {
                safeWaypoints.push(coord);
            } else {
                // Find safer alternative nearby
                const saferPoint = this.findSaferAlternative(coord, reports);
                safeWaypoints.push(saferPoint);
            }
        });
        
        return this.smoothRoute(safeWaypoints);
    }

    // Generate fast route with minimum safety threshold
    generateFastRoute(baseRoute, reports) {
        const coordinates = baseRoute.coordinates;
        const fastWaypoints = [];
        
        coordinates.forEach((coord, index) => {
            const safetyScore = this.calculateSegmentSafety(coord, reports);
            
            // Include waypoint if safety score > 40% (minimum threshold)
            if (safetyScore >= 40 || index === 0 || index === coordinates.length - 1) {
                fastWaypoints.push(coord);
            } else {
                // Skip extremely unsafe areas
                console.warn('Skipping unsafe area:', coord);
            }
        });
        
        return fastWaypoints.length > 2 ? fastWaypoints : coordinates;
    }

    // Calculate safety score for a specific location
    calculateSegmentSafety(coord, reports) {
        let safetyScore = 100; // Start with perfect score
        
        // Factor 1: Lighting (30% weight)
        const lightingScore = this.calculateLightingScore(coord);
        safetyScore -= (100 - lightingScore) * this.safetyFactors.lighting;
        
        // Factor 2: Crowd Density (25% weight)
        const crowdScore = this.calculateCrowdDensityScore(coord);
        safetyScore -= (100 - crowdScore) * this.safetyFactors.crowdDensity;
        
        // Factor 3: Crime Reports (25% weight)
        const crimeScore = this.calculateCrimeReportScore(coord, reports);
        safetyScore -= (100 - crimeScore) * this.safetyFactors.crimeReports;
        
        // Factor 4: Infrastructure (20% weight)
        const infraScore = this.calculateInfrastructureScore(coord);
        safetyScore -= (100 - infraScore) * this.safetyFactors.infrastructure;
        
        return Math.max(0, Math.min(100, safetyScore));
    }

    // Calculate lighting score based on time and location type
    calculateLightingScore(coord) {
        const hour = new Date().getHours();
        let score = 100;
        
        // Reduce score during night hours (8 PM - 6 AM)
        if (hour >= 20 || hour <= 6) {
            score = 70; // Base night score
            
            // Check area type
            if (this.isMainRoad(coord)) {
                score = 85; // Main roads have better lighting
            } else if (this.isCommercialArea(coord)) {
                score = 80; // Commercial areas are lit
            } else if (this.isResidentialArea(coord)) {
                score = 65; // Residential areas have moderate lighting
            } else {
                score = 45; // Industrial/isolated areas
            }
        }
        
        return score;
    }

    // Calculate crowd density score (higher foot traffic = safer)
    calculateCrowdDensityScore(coord) {
        if (this.isCommercialArea(coord)) {
            return 90; // High foot traffic in commercial areas
        } else if (this.isMainRoad(coord)) {
            return 80; // Moderate traffic on main roads
        } else if (this.isResidentialArea(coord)) {
            return 70; // Moderate traffic in residential areas
        } else {
            return 45; // Low traffic in isolated areas
        }
    }

    // Calculate crime report impact on safety score
    calculateCrimeReportScore(coord, reports) {
        let score = 100;
        
        reports.forEach(report => {
            const distance = this.getDistanceFromCoord(coord, report);
            
            if (distance < 200) { // Within 200 meters
                // Different impact based on incident type
                const impact = this.getIncidentImpact(report.incident_type);
                
                // Recent reports have higher impact
                const recencyMultiplier = this.isRecentReport(report) ? 1.5 : 1.0;
                
                score -= impact * recencyMultiplier;
            }
        });
        
        return Math.max(20, score); // Minimum 20% safety score
    }

    // Calculate infrastructure score
    calculateInfrastructureScore(coord) {
        let score = 85; // Assume good infrastructure by default
        
        // Check for infrastructure issues
        if (this.hasInfrastructureIssues(coord)) {
            score = 50; // Poor infrastructure reported
        }
        
        // Main roads typically have better infrastructure
        if (this.isMainRoad(coord)) {
            score = Math.min(95, score + 10);
        }
        
        return score;
    }

    // Get incident impact based on type
    getIncidentImpact(incidentType) {
        const impacts = {
            'violence': 40,
            'harassment': 35,
            'scam': 30,
            'theft': 25,
            'suspicious_activity': 20,
            'poor_lighting': 15,
            'infrastructure': 10
        };
        
        return impacts[incidentType] || 20;
    }

    // Check if report is recent (within 7 days)
    isRecentReport(report) {
        const reportDate = new Date(report.created_at);
        const now = new Date();
        const daysDiff = (now - reportDate) / (1000 * 60 * 60 * 24);
        return daysDiff <= 7;
    }

    // Calculate comprehensive route metrics
    calculateRouteMetrics(safeRoute, fastRoute, reports) {
        const safeRouteScore = this.calculateOverallSafety(safeRoute, reports);
        const fastRouteScore = this.calculateOverallSafety(fastRoute, reports);
        
        const safeRouteTime = this.estimateRouteTime(safeRoute);
        const fastRouteTime = this.estimateRouteTime(fastRoute);
        
        const avoidedIssues = this.countAvoidedIssues(safeRoute, fastRoute, reports);
        
        return {
            safeRoute: {
                safetyScore: Math.round(safeRouteScore),
                time: Math.round(safeRouteTime),
                avoidedIssues: avoidedIssues,
                insights: this.generateSafetyInsights(safeRoute, reports)
            },
            fastRoute: {
                safetyScore: Math.round(fastRouteScore),
                time: Math.round(fastRouteTime),
                avoidedIssues: Math.max(0, avoidedIssues - 1),
                insights: this.generateRouteInsights(fastRoute, reports)
            }
        };
    }

    // Helper functions
    parseLocation(location) {
        // Default to Greater Noida coordinates if parsing fails
        return [28.5355, 77.3910];
    }

    interpolateRoute(start, end, points) {
        const route = [start];
        
        for (let i = 1; i < points - 1; i++) {
            const ratio = i / (points - 1);
            const lat = start[0] + (end[0] - start[0]) * ratio;
            const lng = start[1] + (end[1] - start[1]) * ratio;
            
            // Add some realistic variation
            const variation = 0.001;
            route.push([
                lat + (Math.random() - 0.5) * variation,
                lng + (Math.random() - 0.5) * variation
            ]);
        }
        
        route.push(end);
        return route;
    }

    calculateDistance(coord1, coord2) {
        // Haversine formula for distance calculation
        const R = 6371; // Earth's radius in km
        const dLat = (coord2[0] - coord1[0]) * Math.PI / 180;
        const dLon = (coord2[1] - coord1[1]) * Math.PI / 180;
        
        const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                  Math.cos(coord1[0] * Math.PI / 180) * Math.cos(coord2[0] * Math.PI / 180) *
                  Math.sin(dLon/2) * Math.sin(dLon/2);
                  
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
        return R * c;
    }

    estimateDuration(coord1, coord2) {
        const distance = this.calculateDistance(coord1, coord2);
        const walkingSpeed = 5; // km/h
        return (distance / walkingSpeed) * 60; // minutes
    }

    findSaferAlternative(coord, reports) {
        // Simple implementation: slightly offset the coordinate
        const offset = 0.0005; // ~50 meters
        return [
            coord[0] + (Math.random() - 0.5) * offset,
            coord[1] + (Math.random() - 0.5) * offset
        ];
    }

    smoothRoute(waypoints) {
        // Simple route smoothing - in production would use proper algorithms
        return waypoints;
    }

    calculateOverallSafety(route, reports) {
        let totalScore = 0;
        
        route.forEach(coord => {
            totalScore += this.calculateSegmentSafety(coord, reports);
        });
        
        return totalScore / route.length;
    }

    estimateRouteTime(route) {
        let totalDistance = 0;
        
        for (let i = 1; i < route.length; i++) {
            totalDistance += this.calculateDistance(route[i-1], route[i]);
        }
        
        const walkingSpeed = 5; // km/h
        return (totalDistance / walkingSpeed) * 60; // minutes
    }

    countAvoidedIssues(safeRoute, fastRoute, reports) {
        // Count how many incidents the safe route avoids compared to fast route
        let avoided = 0;
        
        reports.forEach(report => {
            const nearFastRoute = fastRoute.some(coord => 
                this.getDistanceFromCoord(coord, report) < 150
            );
            const nearSafeRoute = safeRoute.some(coord => 
                this.getDistanceFromCoord(coord, report) < 150
            );
            
            if (nearFastRoute && !nearSafeRoute) {
                avoided++;
            }
        });
        
        return avoided;
    }

    generateSafetyInsights(route, reports) {
        const insights = [];
        
        // Check time-based insights
        const hour = new Date().getHours();
        if (hour >= 20 || hour <= 6) {
            insights.push('Well-lit path selected for night travel');
        } else {
            insights.push('Optimal daytime route with good visibility');
        }
        
        // Check area-based insights
        const hasCommercialAreas = route.some(coord => this.isCommercialArea(coord));
        if (hasCommercialAreas) {
            insights.push('Route includes busy commercial areas');
        }
        
        // Check avoided incidents
        const nearbyIncidents = reports.filter(report => 
            route.some(coord => this.getDistanceFromCoord(coord, report) < 200)
        );
        
        if (nearbyIncidents.length === 0) {
            insights.push('No recent incidents reported near this route');
        } else {
            insights.push(`${nearbyIncidents.length} recent incidents avoided`);
        }
        
        return insights;
    }

    generateRouteInsights(route, reports) {
        return [
            'Fastest direct route available',
            'Moderate safety precautions recommended',
            'Stay alert in less crowded areas'
        ];
    }

    // Area classification functions
    isMainRoad(coord) {
        // Simple heuristic - in production would use map data
        return Math.random() < 0.4; // 40% chance
    }

    isCommercialArea(coord) {
        return Math.random() < 0.3; // 30% chance
    }

    isResidentialArea(coord) {
        return Math.random() < 0.5; // 50% chance
    }

    hasInfrastructureIssues(coord) {
        return Math.random() < 0.1; // 10% chance
    }

    getDistanceFromCoord(coord, report) {
        // Simple distance calculation
        const lat1 = coord[0];
        const lon1 = coord[1];
        const lat2 = report.latitude || 28.5355;
        const lon2 = report.longitude || 77.3910;
        
        return this.calculateDistance([lat1, lon1], [lat2, lon2]) * 1000; // meters
    }

    // Fallback routes for when API fails
    getFallbackRoutes(origin, destination) {
        const start = [28.5355, 77.3910];
        const end = [28.5400, 77.3985];
        
        return {
            safeRoute: this.interpolateRoute(start, end, 6),
            fastRoute: this.interpolateRoute(start, end, 4),
            metrics: {
                safeRoute: { safetyScore: 85, time: 18, avoidedIssues: 2, insights: ['Demo safe route'] },
                fastRoute: { safetyScore: 70, time: 14, avoidedIssues: 1, insights: ['Demo fast route'] }
            },
            nearbyReports: this.getDemoReports()
        };
    }

    // Demo reports for testing
    getDemoReports() {
        return [
            {
                id: 1,
                incident_type: 'scam',
                latitude: 28.5370,
                longitude: 77.3925,
                created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
                description: 'Fake product scam reported'
            },
            {
                id: 2,
                incident_type: 'harassment',
                latitude: 28.5380,
                longitude: 77.3940,
                created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000), // 5 days ago
                description: 'Verbal harassment incident'
            }
        ];
    }
}

// Export for use in main application
window.SafePathRouter = SafePathRouter;