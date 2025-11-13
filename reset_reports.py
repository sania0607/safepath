"""
Reset database reports with Delhi-specific sample data
Run this script to clear old Greater Noida reports and add Delhi reports
"""

from database import Database

# Initialize database
db = Database()
db.connect()  # Connect to database

print("=" * 60)
print("SafePath - Reset Reports to Delhi Data")
print("=" * 60)

# Clear all existing reports
print("\n1. Clearing existing reports...")
db.clear_all_reports()

# Get or create a default user for sample reports
print("\n2. Checking for sample user...")
sample_user = db.get_user('sania_')
if not sample_user:
    print("   Creating sample user...")
    db.create_user('sania_', 'sania@safepath.com', 'password123')
    sample_user = db.get_user('sania_')

user_id = sample_user['id']

# Delhi sample reports
print("\n3. Adding Delhi sample reports...")
delhi_reports = [
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

# Insert Delhi reports
count = 0
for report in delhi_reports:
    report_id = db.create_report(
        user_id=user_id,
        report_type=report['type'],
        title=report['title'],
        description=report['description'],
        location=report['location'],
        severity=report['severity'],
        time_of_day=report['time_of_day'],
        is_anonymous=report['is_anonymous']
    )
    if report_id:
        count += 1
        print(f"   ✓ Added: {report['title']}")

print(f"\n✅ Successfully added {count} Delhi reports!")
print("\n" + "=" * 60)
print("Reports reset complete! Restart your app to see Delhi reports.")
print("=" * 60)

# Close database connection
db.disconnect()
