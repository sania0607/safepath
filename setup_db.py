"""
Database Setup Script for Flask Login App
Run this script to set up your PostgreSQL database
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (not to specific database)
        connection = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD')
        )
        
        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = connection.cursor()
        
        # Check if database exists
        db_name = os.getenv('DB_NAME', 'flask_login_db')
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE "{db_name}"')
            print(f"Database '{db_name}' created successfully!")
        else:
            print(f"Database '{db_name}' already exists.")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error creating database: {e}")
        print("Make sure PostgreSQL is running and your credentials are correct.")

def setup_database():
    """Set up the complete database with tables"""
    from database import Database
    
    db = Database()
    if db.connect():
        print("Connected to PostgreSQL successfully!")
        
        if db.create_tables():
            print("Tables created successfully!")
        else:
            print("Failed to create tables.")
        
        db.disconnect()
    else:
        print("Failed to connect to database.")

if __name__ == "__main__":
    print("Setting up PostgreSQL database for Flask Login App...")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Please create a .env file with your PostgreSQL credentials.")
        print("You can copy .env.example and update the values.")
        exit(1)
    
    # Check required environment variables
    required_vars = ['DB_USER', 'DB_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("Please update your .env file with the missing values.")
        exit(1)
    
    print("🔧 Creating database...")
    create_database()
    
    print("🔧 Setting up tables...")
    setup_database()
    
    print("✅ Database setup complete!")
    print("You can now run the Flask application.")