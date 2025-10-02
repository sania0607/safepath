// SafePath Map Functionality
let map;
let routingControl;
let currentRoutePolylines = [];
let safetyMarkers = [];

// Custom marker icons
const markerIcons = {
    lighting: L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #FFA500; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">🔦</div>',
        iconSize: [30, 30]
    }),
    harassment: L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #FF4444; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">⚠️</div>',
        iconSize: [30, 30]
    }),
    scam: L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #FF6B6B; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">🚨</div>',
        iconSize: [30, 30]
    }),
    infrastructure: L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #FD79A8; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">🚧</div>',
        iconSize: [30, 30]
    }),
    other: L.divIcon({
        className: 'custom-marker',
        html: '<div style="background: #667EEA; color: white; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; font-size: 18px; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">❗</div>',
        iconSize: [30, 30]
    })
};

// Initialize Map with Leaflet.js (OpenStreetMap - No API Key Required!)
function initMap() {
    console.log('Initializing SafePath map...');
    
    // Hide loading message first
    const loadingElement = document.getElementById('map-loading');
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    
    // Greater Noida coordinates
    const greaterNoida = [28.5355, 77.3910];
    
    try {
        // Create map centered on Greater Noida
        map = L.map('map', {
            center: greaterNoida,
            zoom: 13,
            zoomControl: true
        });
        
        // Add OpenStreetMap tile layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
        // Add sample safety markers
        addSafetyMarkers();
        
        // Map click listener for reporting
        map.on('click', function(e) {
            console.log('Map clicked at:', e.latlng);
        });
        
        console.log('✅ SafePath map initialized successfully!');
        
    } catch (error) {
        console.error('❌ Error initializing map:', error);
        
        // Show error message
        const mapElement = document.getElementById('map');
        if (mapElement) {
            mapElement.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: center; height: 100%; flex-direction: column; color: #666; background: #f8f9fa;">
                    <h3>🗺️ Map Loading Error</h3>
                    <p>Unable to load the map. Please refresh the page.</p>
                    <button onclick="location.reload()" style="padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">Refresh Page</button>
                </div>
            `;
        }
    }
}

// Add sample safety markers
function addSafetyMarkers() {
    const issueLocations = [
        { lat: 28.5400, lng: 77.3850, type: 'lighting', title: 'Poor Lighting Reported', description: 'Street lights not working in this area' },
        { lat: 28.5320, lng: 77.3950, type: 'harassment', title: 'Harassment Incident', description: 'Multiple reports of harassment' },
        { lat: 28.5380, lng: 77.3880, type: 'scam', title: 'Scam Activity Reported', description: 'Suspicious activity reported by users' },
        { lat: 28.5290, lng: 77.3820, type: 'infrastructure', title: 'Road Damage', description: 'Poor road conditions' }
    ];
    
    issueLocations.forEach(issue => {
        const marker = L.marker([issue.lat, issue.lng], {
            icon: markerIcons[issue.type]
        }).addTo(map);
        
        marker.bindPopup(`
            <div style="padding: 10px;">
                <strong>${issue.title}</strong><br>
                <p style="margin: 5px 0; color: #666;">${issue.description}</p>
                <small style="color: #999;">Reported by community</small>
            </div>
        `);
        
        safetyMarkers.push(marker);
    });
}

// Find safe route function
async function findSafeRoute() {
    const origin = document.getElementById('origin').value;
    const destination = document.getElementById('destination').value;
    
    if (!destination.trim()) {
        alert('Please enter a destination');
        return;
    }
    
    // Show route options
    const routeOptionsElement = document.getElementById('routeOptions');
    if (routeOptionsElement) {
        routeOptionsElement.style.display = 'block';
    }
    
    const safetyInsightsElement = document.getElementById('safetyInsights');
    if (safetyInsightsElement) {
        safetyInsightsElement.style.display = 'block';
    }
    
    // Clear existing routes
    currentRoutePolylines.forEach(polyline => map.removeLayer(polyline));
    currentRoutePolylines = [];
    
    // Display demo routes for now
    displayDemoRoutes();
}

// Display demo routes
function displayDemoRoutes() {
    console.log('Displaying demo routes');
    
    // Demo safe route
    const safeRoute = [
        [28.5355, 77.3910],
        [28.5365, 77.3920],
        [28.5375, 77.3935],
        [28.5385, 77.3950],
        [28.5390, 77.3970],
        [28.5400, 77.3985]
    ];
    
    // Demo fast route
    const fastRoute = [
        [28.5355, 77.3910],
        [28.5358, 77.3925],
        [28.5368, 77.3945],
        [28.5378, 77.3965],
        [28.5388, 77.3980],
        [28.5400, 77.3985]
    ];
    
    // Display safe route (green)
    const safePolyline = L.polyline(safeRoute, {
        color: '#00b894',
        weight: 6,
        opacity: 0.8,
        smoothFactor: 1
    }).addTo(map);
    
    safePolyline.bindPopup('<strong>🛡️ SafePath Route</strong><br/>Prioritizes your safety');
    currentRoutePolylines.push(safePolyline);
    
    // Display fast route (pink)
    const fastPolyline = L.polyline(fastRoute, {
        color: '#fd79a8',
        weight: 5,
        opacity: 0.6,
        smoothFactor: 1
    }).addTo(map);
    
    fastPolyline.bindPopup('<strong>⚡ Quick Route</strong><br/>Fastest available path');
    currentRoutePolylines.push(fastPolyline);
    
    // Fit map to show routes
    const bounds = L.latLngBounds([...safeRoute, ...fastRoute]);
    map.fitBounds(bounds, { padding: [50, 50] });
    
    // Add start/end markers
    addRouteMarkers(safeRoute[0], safeRoute[safeRoute.length - 1]);
    
    // Update UI with demo data
    updateRouteUIDemo();
}

// Add route markers
function addRouteMarkers(start, end) {
    const startIcon = L.divIcon({
        className: 'route-marker',
        html: '<div style="background: #00b894; color: white; border-radius: 50%; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">A</div>',
        iconSize: [25, 25]
    });
    
    const endIcon = L.divIcon({
        className: 'route-marker',
        html: '<div style="background: #e17055; color: white; border-radius: 50%; width: 25px; height: 25px; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 3px solid white; box-shadow: 0 2px 10px rgba(0,0,0,0.3);">B</div>',
        iconSize: [25, 25]
    });
    
    L.marker(start, { icon: startIcon }).addTo(map).bindPopup('Start Point');
    L.marker(end, { icon: endIcon }).addTo(map).bindPopup('Destination');
}

// Update route UI with demo data
function updateRouteUIDemo() {
    const routeCardsElement = document.getElementById('routeCards');
    if (routeCardsElement) {
        routeCardsElement.innerHTML = `
            <div class="route-option active" onclick="selectRoute('safe')">
                <div class="route-icon safe">🛡️</div>
                <div class="route-details">
                    <h5>Safe Route</h5>
                    <span class="route-time">18 min</span>
                    <span class="route-safety">95% Safety Score</span>
                </div>
            </div>
            <div class="route-option" onclick="selectRoute('fast')">
                <div class="route-icon fast">⚡</div>
                <div class="route-details">
                    <h5>Fastest Route</h5>
                    <span class="route-time">14 min</span>
                    <span class="route-safety">72% Safety Score</span>
                </div>
            </div>
        `;
    }
    
    const safetyDataElement = document.getElementById('safetyData');
    if (safetyDataElement) {
        safetyDataElement.innerHTML = `
            <div class="insight-item">
                <span class="insight-icon">💡</span>
                <span>Well-lit main roads selected</span>
            </div>
            <div class="insight-item">
                <span class="insight-icon">👥</span>
                <span>Higher foot traffic areas preferred</span>
            </div>
            <div class="insight-item">
                <span class="insight-icon">⚠️</span>
                <span>2 reported issues avoided</span>
            </div>
        `;
    }
}

// Select route function
function selectRoute(routeType) {
    // Remove active class from all route options
    document.querySelectorAll('.route-option').forEach(option => {
        option.classList.remove('active');
    });
    
    // Add active class to selected route
    event.target.closest('.route-option').classList.add('active');
    
    console.log(`Selected ${routeType} route`);
}

// Report issue function
function reportIssue(issueType) {
    if (issueType) {
        // Redirect to submit report with issue type
        window.location.href = `/submit_report?type=${issueType}`;
    } else {
        // General report submission
        window.location.href = '/submit_report';
    }
}

// Center map function
function centerMap() {
    if (map) {
        const greaterNoida = [28.5355, 77.3910];
        map.setView(greaterNoida, 13);
    }
}

// Toggle layer function
function toggleLayer(layer) {
    if (layer === 'reports') {
        safetyMarkers.forEach(marker => {
            if (map.hasLayer(marker)) {
                map.removeLayer(marker);
            } else {
                map.addLayer(marker);
            }
        });
    }
    console.log(`Toggling ${layer} layer`);
}

// Update current location simulation
function updateCurrentLocation() {
    const locations = [
        'Greater Noida, Sec 16',
        'Greater Noida, Sec 15', 
        'Greater Noida, Alpha Commercial Belt',
        'Greater Noida, Sec 18',
        'Greater Noida, Knowledge Park'
    ];
    
    setInterval(() => {
        const randomLocation = locations[Math.floor(Math.random() * locations.length)];
        const currentLocationElement = document.getElementById('currentLocation');
        if (currentLocationElement) {
            currentLocationElement.textContent = randomLocation;
        }
    }, 30000);
}

// Route planning function for alternative input
async function planRoute() {
    const from = document.getElementById('from-location').value;
    const to = document.getElementById('to-location').value;
    
    if (!from || !to) {
        alert('Please enter both From and To locations');
        return;
    }
    
    try {
        const response = await fetch('/api/get-route', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ from, to })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                displayRoute(data.route);
                document.getElementById('route-info').innerHTML = `
                    <div class="alert alert-success">
                        <strong>Route Found!</strong><br>
                        Distance: ${data.route.distance}km<br>
                        Safety Score: ${data.route.safety_score}/10<br>
                        Estimated Time: ${data.route.duration} minutes
                    </div>
                `;
            } else {
                document.getElementById('route-info').innerHTML = `
                    <div class="alert alert-warning">
                        ${data.message}
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error planning route:', error);
        document.getElementById('route-info').innerHTML = `
            <div class="alert alert-danger">
                Error planning route. Please try again.
            </div>
        `;
    }
}

// Display route from API
function displayRoute(route) {
    currentRoutePolylines.forEach(polyline => map.removeLayer(polyline));
    currentRoutePolylines = [];
    
    if (route.coordinates && route.coordinates.length > 0) {
        const polyline = L.polyline(route.coordinates, {
            color: route.safety_score > 7 ? '#4CAF50' : route.safety_score > 5 ? '#FF9800' : '#F44336',
            weight: 5,
            opacity: 0.8
        }).addTo(map);
        
        currentRoutePolylines.push(polyline);
        map.fitBounds(polyline.getBounds());
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing SafePath...');
    
    // Add loading message to map container
    const mapElement = document.getElementById('map');
    if (mapElement) {
        mapElement.innerHTML = `
            <div id="map-loading" style="display: flex; align-items: center; justify-content: center; height: 100%; flex-direction: column; color: #666; background: #f8f9fa;">
                <div style="text-align: center;">
                    <h3>🗺️ Loading SafePath Map...</h3>
                    <p>Initializing interactive map with safety markers</p>
                    <div style="margin: 20px 0;">
                        <div style="border: 3px solid #f3f3f3; border-top: 3px solid #007bff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
                    </div>
                    <p style="font-size: 12px; color: #999;">Powered by OpenStreetMap</p>
                </div>
            </div>
        `;
    }
    
    // Initialize map after a short delay
    setTimeout(() => {
        initMap();
        updateCurrentLocation();
    }, 100);
});