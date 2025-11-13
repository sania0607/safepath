from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from database import Database
import os
from dotenv import load_dotenv
from safety_model import SafetyModel
from osmnx_routing import build_graph_for_bbox, annotate_graph_with_safety, safest_route_on_graph, fastest_route_on_graph
import pickle
from gemini_ai import analyze_safety_report, generate_route_safety_insight

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Initialize database
db = Database()

# Global variables for routing
safety_model = None
road_graph = None
graph_bounds = None


def init_safety_model():
    """Initialize the safety model (lazy load)."""
    global safety_model
    if safety_model is None:
        csv_path = os.environ.get("SAFEPATH_CSV", "merged_feature_data.csv")
        safety_model = SafetyModel(csv_path)
        safety_model.compute_scores()
        print(f"✓ Safety model loaded from {csv_path}")
    return safety_model


def init_road_graph(north, south, east, west, force_reload=False):
    """Initialize or reload the road graph for a bounding box."""
    global road_graph, graph_bounds
    
    # Try to load from cache first
    cache_file = "cached_road_graph.pkl"
    if not force_reload and road_graph is None and os.path.exists(cache_file):
        try:
            print("Loading cached road graph...")
            with open(cache_file, 'rb') as f:
                cache_data = pickle.load(f)
                road_graph = cache_data['graph']
                graph_bounds = cache_data['bounds']
            print(f"✓ Loaded cached graph: {len(road_graph.nodes)} nodes, {len(road_graph.edges)} edges")
            return road_graph
        except Exception as e:
            print(f"Warning: Could not load cache ({e}), will download fresh")
    
    # Check if we can reuse cached graph
    if not force_reload and road_graph is not None and graph_bounds is not None:
        gn, gs, ge, gw = graph_bounds
        # More lenient bbox check - reuse if overlaps significantly
        if (north <= gn + 0.01 and south >= gs - 0.01 and 
            east <= ge + 0.01 and west >= gw - 0.01):
            print("✓ Reusing cached road graph")
            return road_graph
    
    # Use smaller bbox for faster download (reduce by 50%)
    lat_center = (north + south) / 2
    lon_center = (east + west) / 2
    lat_range = (north - south) * 0.5  # Reduce to 50% of requested
    lon_range = (east - west) * 0.5
    
    north_reduced = lat_center + lat_range / 2
    south_reduced = lat_center - lat_range / 2
    east_reduced = lon_center + lon_range / 2
    west_reduced = lon_center - lon_range / 2
    
    # Download smaller graph for faster response
    print(f"Downloading road graph (optimized area)...")
    G = build_graph_for_bbox(north_reduced, south_reduced, east_reduced, west_reduced)
    print(f"✓ Downloaded {len(G.nodes)} nodes, {len(G.edges)} edges")
    
    sm = init_safety_model()
    print("Annotating graph with safety scores...")
    G = annotate_graph_with_safety(G, sm)
    print("✓ Graph annotated with safety scores")
    
    road_graph = G
    # Store original bounds for better reuse
    graph_bounds = (north, south, east, west)
    return road_graph

def init_database():
    """Initialize database connection and create tables"""
    if db.connect():
        if db.create_tables():
            # Create default users if they don't exist
            create_default_users()
        else:
            print("Failed to create tables")
    else:
        print("Failed to connect to database")

def create_default_users():
    """Create default users for demo purposes"""
    default_users = [
        ('admin', 'password123', 'admin@example.com'),
        ('user', 'mypassword', 'user@example.com')
    ]
    
    for username, password, email in default_users:
        existing_user = db.get_user(username)
        if not existing_user:
            password_hash = generate_password_hash(password)
            user_id = db.create_user(username, password_hash, email)
            if user_id:
                print(f"Created default user: {username}")

@app.route('/')
def index():
    """Landing page - public welcome page"""
    return render_template('landing.html')

@app.route('/home')
def home():
    """Redirect to safe-routes page (home is deprecated)"""
    return redirect(url_for('safe_routes'))

@app.route('/safe-routes')
def safe_routes():
    """Safe routes page with interactive map and community reports"""
    if 'username' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    # Get all community reports to display on map
    reports = db.get_all_reports()
    
    return render_template('safe_routes.html', 
                         username=session['username'],
                         reports=reports)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Get user from database
        user = db.get_user(username)
        
        if user and check_password_hash(user['password_hash'], password):
            session['username'] = username
            session['user_id'] = user['id']
            
            # Update last login
            db.update_last_login(username)
            
            flash('Login successful!', 'success')
            return redirect(url_for('safe_routes'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page - only accessible after login"""
    if 'username' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    # Get user details from database
    user = db.get_user(session['username'])
    
    return render_template('dashboard.html', 
                         username=session['username'], 
                         user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')
        
        # Check if user already exists
        existing_user = db.get_user(username)
        if existing_user:
            flash('Username already exists!', 'error')
        else:
            # Create new user
            password_hash = generate_password_hash(password)
            user_id = db.create_user(username, password_hash, email)
            
            if user_id:
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Registration failed. Please try again.', 'error')
    
    return render_template('register.html')

@app.route('/reports')
def community_reports():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get reports from database
    reports = db.get_all_reports()
    
    # If no reports in database, add some sample data
    if not reports:
        # Add sample reports for Delhi area
        sample_reports = [
            {
                'type': 'scam',
                'title': 'ATM Card Skimming Alert',
                'description': 'Suspicious device found attached to ATM at Connaught Place. Be careful while using ATMs in this area.',
                'location': 'Connaught Place, Delhi',
                'severity': 'high',
                'time_of_day': 'afternoon',
                'is_anonymous': True
            },
            {
                'type': 'harassment',
                'title': 'Eve Teasing Incident',
                'description': 'Women being harassed by group of men near the bus stop. Multiple complaints from commuters.',
                'location': 'Nehru Place, Delhi',
                'severity': 'high',
                'time_of_day': 'evening',
                'is_anonymous': False
            },
            {
                'type': 'scam',
                'title': 'Fake Job Offer Scam',
                'description': 'Scammers operating near placement consultancy promising government jobs for upfront payment.',
                'location': 'Laxmi Nagar, Delhi',
                'severity': 'medium',
                'time_of_day': 'afternoon',
                'is_anonymous': True
            },
            {
                'type': 'lighting',
                'title': 'No Street Lights',
                'description': 'Complete darkness on the main road after sunset. Multiple chain snatching incidents reported.',
                'location': 'Dwarka Sector 12, Delhi',
                'severity': 'high',
                'time_of_day': 'night',
                'is_anonymous': False
            },
            {
                'type': 'infrastructure',
                'title': 'Broken Footpath',
                'description': 'Large portion of footpath collapsed. Pedestrians forced to walk on busy road.',
                'location': 'Rohini Sector 8, Delhi',
                'severity': 'medium',
                'time_of_day': 'morning',
                'is_anonymous': False
            },
            {
                'type': 'scam',
                'title': 'Pickpocketing Gang Active',
                'description': 'Organized pickpocket gang targeting passengers near metro station. Lost wallet and phone.',
                'location': 'Rajiv Chowk Metro, Delhi',
                'severity': 'high',
                'time_of_day': 'evening',
                'is_anonymous': True
            },
            {
                'type': 'harassment',
                'title': 'Safety Concern for Women',
                'description': 'Men following and making inappropriate gestures near college gate. Students feeling unsafe.',
                'location': 'Kamla Nagar, Delhi',
                'severity': 'high',
                'time_of_day': 'afternoon',
                'is_anonymous': False
            },
            {
                'type': 'lighting',
                'title': 'Poor Visibility at Night',
                'description': 'Street lights malfunctioning in residential colony. Women afraid to go out after dark.',
                'location': 'Mayur Vihar Phase 1, Delhi',
                'severity': 'medium',
                'time_of_day': 'night',
                'is_anonymous': False
            },
            {
                'type': 'scam',
                'title': 'Auto Rickshaw Overcharging',
                'description': 'Auto drivers refusing meter and demanding 3x fare. Targeting tourists and women traveling alone.',
                'location': 'Chandni Chowk, Delhi',
                'severity': 'low',
                'time_of_day': 'afternoon',
                'is_anonymous': True
            },
            {
                'type': 'infrastructure',
                'title': 'Open Drainage Gutter',
                'description': 'Uncovered drainage running along sidewalk. Foul smell and safety hazard, especially at night.',
                'location': 'Saket, Delhi',
                'severity': 'medium',
                'time_of_day': 'evening',
                'is_anonymous': False
            },
            {
                'type': 'harassment',
                'title': 'Stalking Incident',
                'description': 'Man following women from metro to residential area. Has been seen multiple times.',
                'location': 'Lajpat Nagar, Delhi',
                'severity': 'high',
                'time_of_day': 'night',
                'is_anonymous': True
            },
            {
                'type': 'scam',
                'title': 'Fake Medicine Sellers',
                'description': 'People selling fake Ayurvedic medicines door-to-door. Elderly citizens being targeted.',
                'location': 'Janakpuri, Delhi',
                'severity': 'medium',
                'time_of_day': 'morning',
                'is_anonymous': False
            }
        ]
        
        # Insert sample reports
        for sample in sample_reports:
            db.create_report(
                user_id=session['user_id'],
                report_type=sample['type'],
                title=sample['title'],
                description=sample['description'],
                location=sample['location'],
                severity=sample['severity'],
                time_of_day=sample['time_of_day'],
                is_anonymous=sample['is_anonymous']
            )
        
        # Get reports again after inserting samples
        reports = db.get_all_reports()
    
    username = session.get('username', 'User')
    return render_template('community_reports.html', username=username, reports=reports)

@app.route('/submit_report', methods=['GET', 'POST'])
def submit_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get form data
        report_type = request.form.get('type')
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        severity = request.form.get('severity')
        time_of_day = request.form.get('time_of_day')
        is_anonymous = bool(request.form.get('anonymous'))
        notify_authorities = bool(request.form.get('notify_authorities'))
        
        # Validate required fields
        if not all([report_type, title, description, location, severity]):
            flash('Please fill in all required fields.', 'error')
            return render_template('submit_report.html', username=session.get('username', 'User'))
        
        # 🤖 AI-POWERED ANALYSIS - Use Gemini to analyze the report
        try:
            ai_analysis = analyze_safety_report(title, description, report_type)
            
            # Override severity if AI suggests different (and user didn't explicitly set it)
            if ai_analysis.get('ai_powered') and ai_analysis.get('severity'):
                suggested_severity = ai_analysis['severity']
                # Inform user if AI adjusted severity
                if suggested_severity != severity and ai_analysis.get('ai_powered'):
                    flash(f'AI Analysis: Severity adjusted to "{suggested_severity}" based on report content.', 'info')
                    severity = suggested_severity
            
            # Store AI insights in session for display (optional)
            if ai_analysis.get('ai_powered'):
                flash(f'✨ AI Insight: {ai_analysis.get("summary", "Report analyzed successfully")}', 'info')
        
        except Exception as e:
            print(f"AI Analysis Error: {str(e)}")
            # Continue with manual severity if AI fails
            pass
        
        # Create report in database
        report_id = db.create_report(
            user_id=session['user_id'],
            report_type=report_type,
            title=title,
            description=description,
            location=location,
            severity=severity,
            time_of_day=time_of_day,
            is_anonymous=is_anonymous,
            notify_authorities=notify_authorities
        )
        
        if report_id:
            flash('Your report has been submitted successfully! Thank you for helping the community stay safe.', 'success')
            return redirect(url_for('community_reports'))
        else:
            flash('There was an error submitting your report. Please try again.', 'error')
    
    username = session.get('username', 'User')
    return render_template('submit_report.html', username=username)

@app.route('/mark_helpful/<int:report_id>', methods=['POST'])
def mark_helpful(report_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    success = db.mark_report_helpful(report_id, session['user_id'])
    
    if success:
        return {'success': True, 'message': 'Marked as helpful!'}
    else:
        return {'success': False, 'message': 'Already marked or error occurred'}

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.pop('username', None)
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/api/nearby-reports', methods=['POST'])
def get_nearby_reports():
    """Get community reports near a route for safety calculations"""
    try:
        data = request.get_json()
        origin = data.get('origin')
        destination = data.get('destination')
        radius = data.get('radius', 500)  # meters
        
        # For demo purposes, return reports from Greater Noida area
        # In production, this would calculate actual geographical proximity
        reports = db.get_all_reports()
        
        # Filter reports to simulate proximity to route
        # In production, would use actual geographical calculations
        nearby_reports = []
        for report in reports:
            # Add some demo coordinates if not present
            if not hasattr(report, 'latitude'):
                report['latitude'] = 28.5355 + (hash(str(report['id'])) % 100) * 0.0001
                report['longitude'] = 77.3910 + (hash(str(report['id'])) % 100) * 0.0001
            
            nearby_reports.append({
                'id': report['id'],
                'incident_type': report['incident_type'],
                'latitude': report.get('latitude', 28.5355),
                'longitude': report.get('longitude', 77.3910),
                'description': report['description'],
                'created_at': report['created_at'].isoformat(),
                'helpful_count': report.get('helpful_count', 0)
            })
        
        return jsonify(nearby_reports)
        
    except Exception as e:
        print(f"Error fetching nearby reports: {e}")
        return jsonify([]), 500


@app.route('/api/safest-route', methods=['POST'])
def api_safest_route():
    """Compute the safest route between two coordinates using OSMnx."""
    try:
        data = request.get_json()
        
        # Parse origin and destination
        origin = data.get("origin")
        destination = data.get("destination")
        
        if not origin or not destination:
            return jsonify({"status": "error", "message": "Missing origin or destination"}), 400
        
        origin_coords = (float(origin["lon"]), float(origin["lat"]))
        dest_coords = (float(destination["lon"]), float(destination["lat"]))
        
        # Parse bbox (optional; use default if not provided)
        bbox = data.get("bbox")
        if bbox:
            north = float(bbox["north"])
            south = float(bbox["south"])
            east = float(bbox["east"])
            west = float(bbox["west"])
        else:
            # Default: use a SMALL bbox around endpoints for faster download
            lats = [origin_coords[1], dest_coords[1]]
            lons = [origin_coords[0], dest_coords[0]]
            # Reduce padding to 0.02 degrees (~2km) for much faster downloads
            padding = 0.02  # Changed from 0.05 to 0.02
            north = max(lats) + padding
            south = min(lats) - padding
            east = max(lons) + padding
            west = min(lons) - padding
        
        # Initialize graph (will reuse cached if bbox is covered)
        G = init_road_graph(north, south, east, west)
        
        # Compute both safest and fastest routes
        safest_path = safest_route_on_graph(G, origin_coords, dest_coords)
        fastest_path = fastest_route_on_graph(G, origin_coords, dest_coords)
        
        if not safest_path or not fastest_path:
            return jsonify({
                "status": "error",
                "message": "No route found between the given points. They may be disconnected or outside the graph bounds."
            }), 404
        
        # Format response with both routes as GeoJSON LineStrings
        return jsonify({
            "status": "success",
            "safest_route": {
                "type": "LineString",
                "coordinates": safest_path  # [[lon, lat], [lon, lat], ...]
            },
            "fastest_route": {
                "type": "LineString",
                "coordinates": fastest_path  # [[lon, lat], [lon, lat], ...]
            },
            "waypoints": safest_path,  # For backward compatibility
            "num_nodes": len(safest_path)
        })
    
    except Exception as e:
        print(f"Error computing route: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/safety-score', methods=['POST'])
def api_safety_score():
    """Get the safety score for a specific location."""
    try:
        data = request.get_json()
        lon = float(data.get("lon"))
        lat = float(data.get("lat"))
        
        sm = init_safety_model()
        score = sm.score_location(lon, lat)
        
        return jsonify({
            "status": "success",
            "lon": lon,
            "lat": lat,
            "safety_score": float(score)
        })
    
    except Exception as e:
        print(f"Error getting safety score: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    init_database()
    app.run(debug=True)