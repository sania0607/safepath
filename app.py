from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from database import Database
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')

# Initialize database
db = Database()

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
    """Home page - only accessible after login"""
    if 'username' not in session:
        flash('Please log in to access this page.', 'error')
        return redirect(url_for('login'))
    
    # Get user details from database
    user = db.get_user(session['username'])
    
    return render_template('home.html', 
                         username=session['username'], 
                         user=user)

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
            return redirect(url_for('home'))
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
        # Add sample reports
        sample_reports = [
            {
                'type': 'scam',
                'title': 'Fake QR Code Payment Scam',
                'description': 'Someone put fake QR codes over real ones at the tea stall near Sec 16 metro. Lost ₹500 before realizing.',
                'location': 'Greater Noida Sector 16',
                'severity': 'high',
                'time_of_day': 'afternoon',
                'is_anonymous': True
            },
            {
                'type': 'harassment',
                'title': 'Street Harassment Incident',
                'description': 'Group of men making inappropriate comments near the mall entrance. Felt very unsafe walking alone.',
                'location': 'Alpha Commercial Belt',
                'severity': 'medium',
                'time_of_day': 'evening',
                'is_anonymous': False
            },
            {
                'type': 'lighting',
                'title': 'Very Poor Street Lighting',
                'description': 'Street lights have been broken for weeks. The entire stretch is very dark after 8 PM.',
                'location': 'Greater Noida Sector 22',
                'severity': 'medium',
                'time_of_day': 'night',
                'is_anonymous': False
            },
            {
                'type': 'infrastructure',
                'title': 'Dangerous Open Manholes',
                'description': 'Multiple uncovered manholes on the main road. Very dangerous for pedestrians and two-wheelers.',
                'location': 'Dadri Road, Greater Noida',
                'severity': 'high',
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

if __name__ == '__main__':
    init_database()
    app.run(debug=True)