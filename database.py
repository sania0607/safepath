import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Database:
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            # Try DATABASE_URL first, then individual components
            database_url = os.getenv('DATABASE_URL')
            
            if database_url:
                self.connection = psycopg2.connect(database_url)
            else:
                self.connection = psycopg2.connect(
                    host=os.getenv('DB_HOST', 'localhost'),
                    port=os.getenv('DB_PORT', '5432'),
                    database=os.getenv('DB_NAME', 'my_new_project_db'),
                    user=os.getenv('DB_USER'),
                    password=os.getenv('DB_PASSWORD')
                )
            
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def create_tables(self):
        """Create necessary tables if they don't exist"""
        try:
            # Users table
            create_users_table = """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                email VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            );
            """
            
            # Reports table
            create_reports_table = """
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                type VARCHAR(50) NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT NOT NULL,
                location VARCHAR(300) NOT NULL,
                severity VARCHAR(20) NOT NULL,
                time_of_day VARCHAR(20),
                is_anonymous BOOLEAN DEFAULT FALSE,
                notify_authorities BOOLEAN DEFAULT FALSE,
                helpful_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            # Reports helpful tracking table
            create_helpful_table = """
            CREATE TABLE IF NOT EXISTS reports_helpful (
                id SERIAL PRIMARY KEY,
                report_id INTEGER REFERENCES reports(id),
                user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(report_id, user_id)
            );
            """
            
            self.cursor.execute(create_users_table)
            self.cursor.execute(create_reports_table)
            self.cursor.execute(create_helpful_table)
            self.connection.commit()
            print("Tables created successfully")
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False
    
    def create_user(self, username, password_hash, email=None):
        """Create a new user"""
        try:
            query = """
            INSERT INTO users (username, password_hash, email)
            VALUES (%s, %s, %s)
            RETURNING id;
            """
            self.cursor.execute(query, (username, password_hash, email))
            user_id = self.cursor.fetchone()['id']
            self.connection.commit()
            return user_id
        except Exception as e:
            print(f"Error creating user: {e}")
            self.connection.rollback()
            return None
    
    def get_user(self, username):
        """Get user by username"""
        try:
            query = "SELECT * FROM users WHERE username = %s;"
            self.cursor.execute(query, (username,))
            return self.cursor.fetchone()
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    def update_last_login(self, username):
        """Update user's last login timestamp"""
        try:
            query = """
            UPDATE users 
            SET last_login = CURRENT_TIMESTAMP 
            WHERE username = %s;
            """
            self.cursor.execute(query, (username,))
            self.connection.commit()
        except Exception as e:
            print(f"Error updating last login: {e}")
    
    def get_all_users(self):
        """Get all users (for admin purposes)"""
        try:
            query = "SELECT id, username, email, created_at, last_login FROM users;"
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []
    
    def create_report(self, user_id, report_type, title, description, location, severity, time_of_day=None, is_anonymous=False, notify_authorities=False):
        """Create a new safety report"""
        try:
            query = """
            INSERT INTO reports (user_id, type, title, description, location, severity, time_of_day, is_anonymous, notify_authorities)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id;
            """
            self.cursor.execute(query, (user_id, report_type, title, description, location, severity, time_of_day, is_anonymous, notify_authorities))
            report_id = self.cursor.fetchone()['id']
            self.connection.commit()
            return report_id
        except Exception as e:
            print(f"Error creating report: {e}")
            self.connection.rollback()
            return None
    
    def get_all_reports(self, limit=50):
        """Get all reports from the database"""
        try:
            query = """
            SELECT r.id, r.type, r.title, r.description, r.location, r.severity, 
                   r.time_of_day, r.is_anonymous, r.helpful_count, r.created_at,
                   CASE 
                       WHEN r.is_anonymous THEN 'Anonymous User'
                       ELSE u.username 
                   END as display_name
            FROM reports r
            LEFT JOIN users u ON r.user_id = u.id
            ORDER BY r.created_at DESC
            LIMIT %s;
            """
            self.cursor.execute(query, (limit,))
            reports = self.cursor.fetchall()
            
            # Convert to list of dictionaries with relative timestamps
            report_list = []
            for report in reports:
                # Calculate relative timestamp
                created_at = report['created_at']
                now = datetime.now()
                time_diff = now - created_at
                
                if time_diff.days > 0:
                    timestamp = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    timestamp = f"{hours} hour{'s' if hours > 1 else ''} ago"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    timestamp = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    timestamp = "Just now"
                
                report_dict = {
                    'id': report['id'],
                    'type': report['type'],
                    'title': report['title'],
                    'description': report['description'],
                    'location': report['location'],
                    'severity': report['severity'],
                    'time_of_day': report['time_of_day'],
                    'is_anonymous': report['is_anonymous'],
                    'helpful_count': report['helpful_count'],
                    'user': report['display_name'],
                    'timestamp': timestamp
                }
                report_list.append(report_dict)
                
            return report_list
        except Exception as e:
            print(f"Error getting reports: {e}")
            return []
    
    def mark_report_helpful(self, report_id, user_id):
        """Mark a report as helpful by a user"""
        try:
            # Check if user already marked this report as helpful
            check_query = "SELECT id FROM reports_helpful WHERE report_id = %s AND user_id = %s;"
            self.cursor.execute(check_query, (report_id, user_id))
            
            if self.cursor.fetchone():
                return False  # Already marked as helpful
            
            # Add to helpful table
            insert_query = "INSERT INTO reports_helpful (report_id, user_id) VALUES (%s, %s);"
            self.cursor.execute(insert_query, (report_id, user_id))
            
            # Update helpful count
            update_query = "UPDATE reports SET helpful_count = helpful_count + 1 WHERE id = %s;"
            self.cursor.execute(update_query, (report_id,))
            
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error marking report as helpful: {e}")
            self.connection.rollback()
            return False
    
    def get_reports_by_type(self, report_type, limit=50):
        """Get reports filtered by type"""
        try:
            query = """
            SELECT r.id, r.type, r.title, r.description, r.location, r.severity, 
                   r.time_of_day, r.is_anonymous, r.helpful_count, r.created_at,
                   CASE 
                       WHEN r.is_anonymous THEN 'Anonymous User'
                       ELSE u.username 
                   END as display_name
            FROM reports r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.type = %s
            ORDER BY r.created_at DESC
            LIMIT %s;
            """
            self.cursor.execute(query, (report_type, limit))
            reports = self.cursor.fetchall()
            
            # Convert to list of dictionaries (same as get_all_reports)
            report_list = []
            for report in reports:
                created_at = report['created_at']
                now = datetime.now()
                time_diff = now - created_at
                
                if time_diff.days > 0:
                    timestamp = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
                elif time_diff.seconds > 3600:
                    hours = time_diff.seconds // 3600
                    timestamp = f"{hours} hour{'s' if hours > 1 else ''} ago"
                elif time_diff.seconds > 60:
                    minutes = time_diff.seconds // 60
                    timestamp = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    timestamp = "Just now"
                
                report_dict = {
                    'id': report['id'],
                    'type': report['type'],
                    'title': report['title'],
                    'description': report['description'],
                    'location': report['location'],
                    'severity': report['severity'],
                    'time_of_day': report['time_of_day'],
                    'is_anonymous': report['is_anonymous'],
                    'helpful_count': report['helpful_count'],
                    'user': report['display_name'],
                    'timestamp': timestamp
                }
                report_list.append(report_dict)
                
            return report_list
        except Exception as e:
            print(f"Error getting reports by type: {e}")
            return []