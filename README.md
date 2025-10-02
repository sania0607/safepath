# 🛡️ SafePa### 👥 **Community Safety Platform**
- **Incident Reporting**: Users can report scams, harassment, theft, and other safety concerns
- **Community Validation**: Helpful voting system for report verification
- **Real-time Alerts**: Stay informed about safety issues in your area
- **Filtering & Search**: Filter reports by type, location, and date

### 🔒 **User Authentication**
- Secure login and registration system
- Password hashing with Werkzeug security
- Session management for personalized experiencety-First Navigation App

**SafePath** is an innovative safety-first navigation application designed for urban travelers. It provides intelligent route planning that prioritizes user safety while maintaining efficiency, combined with a comprehensive community-driven incident reporting system.

## 🌟 Features

### 🗺️ **Smart Route Planning**
- **SafePath Route**: Prioritizes safety with advanced algorithms
- **Quick Route**: Fastest path with minimum safety threshold
- **Real-time Safety Calculation**: Uses community reports and multiple safety factors
- **Interactive Map**: Powered by Leaflet.js with OpenStreetMap integration

### � **Community Safety Platform**
- **Incident Reporting**: Users can report scams, harassment, theft, and other safety concerns
- **Community Validation**: Helpful voting system for report verification
- **Real-time Alerts**: Stay informed about safety issues in your area
- **Filtering & Search**: Filter reports by type, location, and date

### 🔒 **User Authentication**
- Secure login and registration system
- Session management for personalized experience

## 🧠 **SafePath Algorithm**

Our proprietary routing algorithm calculates safety scores using multiple factors:

```
Safety Score = (Lighting × 30%) + (Crowd Density × 25%) + (Crime Reports × 25%) + (Infrastructure × 20%)
```

### Safety Factors:
- **Lighting (30%)**: Time-based scoring with area-specific adjustments
- **Crowd Density (25%)**: Higher foot traffic = increased safety
- **Crime Reports (25%)**: Recent incident proximity and severity
- **Infrastructure (20%)**: Road conditions and maintenance quality

## 🚀 **Technology Stack**

- **Backend**: Flask 2.3.3 (Python)
- **Database**: PostgreSQL with psycopg2-binary
- **Frontend**: HTML5, CSS3, Bootstrap 5
- **Mapping**: Leaflet.js with OpenStreetMap
- **Authentication**: Werkzeug security, Flask sessions
- **Environment**: Python-dotenv for configuration

## Demo Credentials

- **Username:** admin, **Password:** password123
- **Username:** user, **Password:** mypassword

## Prerequisites

1. **Python 3.7 or higher**
2. **PostgreSQL** installed and running
3. **PostgreSQL user** with database creation privileges

## Installation

1. **Clone or download the project**

2. **Install Python dependencies:**
   ```
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL:**
   - Install PostgreSQL if not already installed
   - Create a PostgreSQL user (or use existing one)
   - Note down your database credentials

4. **Configure environment variables:**
   ```
   copy .env.example .env
   ```
   Edit `.env` file with your PostgreSQL credentials:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/safepath_db
   SECRET_KEY=your-secret-key-change-this-in-production
   
   # Or use individual components:
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=safepath_db
   DB_USER=your_username
   DB_PASSWORD=your_password
   ```

5. **Set up the database:**
   ```
   python setup_db.py
   ```

## Running the Application

1. **Navigate to the project directory**
2. **Run the Flask application:**
   ```
   python app.py
   ```
3. **Open your browser and go to** `http://localhost:5000`

## Project Structure

```
safepath/
├── app.py                    # Main Flask application with routing
├── database.py               # Database connection and operations
├── setup_db.py               # Database setup script
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── .env                      # Your environment variables
├── README.md                 # Project documentation
├── LICENSE                   # MIT License
├── .gitignore               # Git ignore rules
├── templates/               # HTML templates
│   ├── base.html            # Base template
│   ├── landing.html         # Landing page
│   ├── login.html           # Login page
│   ├── register.html        # Registration page
│   ├── home.html            # Main dashboard with map
│   ├── community_reports.html # Community reports feed
│   └── submit_report.html   # Report submission form
└── static/                  # Static files
    ├── css/                 # Stylesheets
    ├── js/                  # JavaScript files
    │   └── routing-algorithm.js # SafePath routing algorithm
    ├── images/              # Image assets
    ├── fonts/               # Font files
    └── vendor/              # Third-party libraries
```

## Database Schema

### Users Table
- `id` (Primary Key, Serial)
- `username` (Unique, VARCHAR(50))
- `email` (Unique, VARCHAR(100))
- `password_hash` (VARCHAR(255))
- `created_at` (Timestamp)

### Reports Table
- `id` (Primary Key, Serial)
- `user_id` (Foreign Key → users.id)
- `incident_type` (VARCHAR(50))
- `location` (VARCHAR(200))
- `description` (TEXT)
- `anonymous` (BOOLEAN)
- `helpful_count` (INTEGER)
- `created_at` (Timestamp)

### Reports_Helpful Table
- `user_id` (Foreign Key → users.id)
- `report_id` (Foreign Key → reports.id)
- `created_at` (Timestamp)
- Primary Key: (user_id, report_id)

## API Endpoints

### Authentication
- `GET /` - Landing page
- `GET,POST /login` - User login
- `GET,POST /register` - User registration
- `GET /logout` - User logout

### Main Application
- `GET /home` - Main dashboard with interactive map (protected)
- `GET /reports` - Community reports feed (protected)
- `GET /submit_report` - Report submission form (protected)
- `POST /submit_report` - Submit new incident report (protected)
- `POST /mark_helpful/<report_id>` - Mark report as helpful (protected)

### API Routes
- `POST /api/nearby-reports` - Get reports for route safety calculation

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Complete PostgreSQL connection string | `postgresql://user:pass@localhost:5432/dbname` |
| `SECRET_KEY` | Flask secret key for sessions | `your-secret-key` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `safepath_db` |
| `DB_USER` | PostgreSQL username | `your_username` |
| `DB_PASSWORD` | PostgreSQL password | `your_password` |

## Troubleshooting

### Database Connection Issues
1. **Check PostgreSQL is running:**
   ```
   # Windows (if using service)
   services.msc
   
   # Check if PostgreSQL service is running
   ```

2. **Verify credentials in .env file**

3. **Test connection manually:**
   ```
   psql -h localhost -U your_username -d postgres
   ```

### Common Errors
- **"database does not exist"** - Run `python setup_db.py`
- **"authentication failed"** - Check username/password in `.env`
- **"could not connect to server"** - Ensure PostgreSQL is running

## 🎯 **Key SafePath Features**

### Route Planning
- Enter origin and destination addresses
- Choose between SafePath (secure) or Quick (fast) routes
- View real-time safety insights and avoided incidents
- Interactive map with route visualization using Leaflet.js

### Incident Reporting
- Select from multiple incident types (scam, harassment, theft, etc.)
- Add precise location and detailed description
- Choose anonymous or public reporting options
- Community guidelines compliance checking

### Community Features
- Browse all community safety reports
- Filter by incident type, date, and location
- Mark reports as helpful for validation
- View community safety statistics and trends

## 🌍 **Demo Location**

Currently configured for **Greater Noida, India** with sample safety markers and routes.
**Map Center**: 28.5355°N, 77.3910°E

## Security Notes

- Change the secret key in production
- Use environment variables for sensitive data
- Implement additional security measures like CSRF protection
- Use HTTPS in production
- Consider implementing password complexity requirements
- Add rate limiting for login attempts
- Implement proper logging and monitoring