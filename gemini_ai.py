"""
Gemini AI Integration for SafePath
Provides intelligent report analysis using Google's Gemini LLM
"""

import os
import google.generativeai as genai
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

def initialize_gemini():
    """Initialize Gemini AI with API key"""
    if GEMINI_API_KEY and GEMINI_API_KEY != 'your-gemini-api-key-here':
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    return False

def analyze_safety_report(title, description, report_type=None):
    """
    Analyze a safety report using Gemini AI
    
    Args:
        title (str): Report title
        description (str): Detailed report description
        report_type (str): Optional - type of report
    
    Returns:
        dict: Analysis results including severity, insights, and recommendations
    """
    
    # Check if Gemini is configured
    if not initialize_gemini():
        # Fallback to rule-based analysis if API key not configured
        return fallback_analysis(title, description, report_type)
    
    try:
        # Create the model (using Gemini 2.5 Flash)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Create the prompt
        prompt = f"""
You are a safety analysis AI for SafePath, a women's safety navigation app in Delhi, India.

Analyze this community safety report and provide a structured assessment:

**Report Title:** {title}
**Report Type:** {report_type if report_type else 'Not specified'}
**Description:** {description}

Provide your analysis in the following JSON format (respond ONLY with valid JSON, no extra text):

{{
    "severity": "low/medium/high",
    "incident_category": "harassment/theft/infrastructure/lighting/suspicious_activity/scam/other",
    "safety_concerns": ["list of specific safety issues identified"],
    "time_sensitivity": "immediate/urgent/moderate/low",
    "recommended_actions": ["list of 2-3 recommended actions"],
    "sentiment": "fearful/concerned/informative/neutral",
    "risk_level": 1-10,
    "summary": "One sentence summary of the incident"
}}

Focus on:
- Women's safety concerns
- Infrastructure issues (lighting, CCTV, patrols)
- Suspicious activities or harassment patterns
- Time-sensitive threats
"""
        
        # Generate response
        response = model.generate_content(prompt)
        
        # Parse the JSON response
        try:
            # Extract JSON from response text
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            analysis = json.loads(response_text)
            
            # Add metadata
            analysis['ai_powered'] = True
            analysis['model'] = 'gemini-2.5-flash'
            
            return analysis
            
        except json.JSONDecodeError:
            # If JSON parsing fails, return structured fallback
            return {
                'severity': extract_severity_from_text(response.text),
                'summary': response.text[:200],
                'ai_powered': True,
                'model': 'gemini-2.5-flash',
                'note': 'Partial AI analysis (JSON parsing failed)'
            }
    
    except Exception as e:
        print(f"Gemini AI Error: {str(e)}")
        # Fallback to rule-based analysis
        return fallback_analysis(title, description, report_type)

def fallback_analysis(title, description, report_type=None):
    """
    Rule-based fallback analysis when AI is unavailable
    
    Args:
        title (str): Report title
        description (str): Report description
        report_type (str): Report type
    
    Returns:
        dict: Basic analysis results
    """
    text = (title + ' ' + description).lower()
    
    # Severity detection (rule-based)
    severity = 'medium'  # default
    high_severity_keywords = ['attack', 'assault', 'robbery', 'threat', 'danger', 'scared', 'followed', 'harass']
    low_severity_keywords = ['broken', 'light', 'bulb', 'minor', 'suggestion']
    
    if any(keyword in text for keyword in high_severity_keywords):
        severity = 'high'
    elif any(keyword in text for keyword in low_severity_keywords):
        severity = 'low'
    
    # Category detection
    category = 'other'
    if report_type:
        category = report_type.lower()
    else:
        if any(word in text for word in ['light', 'lighting', 'dark', 'bulb']):
            category = 'lighting'
        elif any(word in text for word in ['harass', 'follow', 'catcall', 'stare']):
            category = 'harassment'
        elif any(word in text for word in ['theft', 'steal', 'rob', 'snatch']):
            category = 'theft'
        elif any(word in text for word in ['scam', 'fraud', 'cheat']):
            category = 'scam'
    
    # Sentiment detection
    sentiment = 'neutral'
    if any(word in text for word in ['scared', 'afraid', 'fear', 'terrified']):
        sentiment = 'fearful'
    elif any(word in text for word in ['concern', 'worry', 'unsafe']):
        sentiment = 'concerned'
    
    return {
        'severity': severity,
        'incident_category': category,
        'safety_concerns': extract_concerns(text),
        'sentiment': sentiment,
        'ai_powered': False,
        'model': 'rule-based',
        'summary': description[:150] + '...' if len(description) > 150 else description
    }

def extract_concerns(text):
    """Extract safety concerns from text"""
    concerns = []
    
    if 'light' in text or 'dark' in text:
        concerns.append('Poor lighting')
    if 'alone' in text or 'isolated' in text or 'deserted' in text:
        concerns.append('Isolated area')
    if 'follow' in text or 'stalk' in text:
        concerns.append('Suspicious activity')
    if 'night' in text or 'evening' in text:
        concerns.append('Night-time safety')
    if 'crowd' in text or 'group' in text:
        concerns.append('Crowding issues')
    
    return concerns if concerns else ['General safety concern']

def extract_severity_from_text(text):
    """Extract severity from AI response text"""
    text_lower = text.lower()
    
    if 'high' in text_lower or 'severe' in text_lower or 'critical' in text_lower:
        return 'high'
    elif 'low' in text_lower or 'minor' in text_lower:
        return 'low'
    else:
        return 'medium'

def generate_route_safety_insight(route_data):
    """
    Generate AI-powered safety insights for a route
    
    Args:
        route_data (dict): Route information including safety score, distance, etc.
    
    Returns:
        str: Natural language safety insight
    """
    
    if not initialize_gemini():
        return None
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        prompt = f"""
As a safety advisor for SafePath, provide a brief (2-3 sentences) safety insight about this route:

Route Safety Score: {route_data.get('safety_score', 'N/A')}/10
Distance: {route_data.get('distance', 'N/A')} km
Estimated Time: {route_data.get('time', 'N/A')} minutes

Safety Features Nearby:
- Streetlights: {route_data.get('streetlights', 0)}
- Police Stations: {route_data.get('police_stations', 0)}
- Metro Stations: {route_data.get('metro_stations', 0)}

Provide a helpful, concise safety insight for a woman traveling this route. Be reassuring but honest.
"""
        
        response = model.generate_content(prompt)
        return response.text.strip()
        
    except Exception as e:
        print(f"Route insight generation error: {str(e)}")
        return None

# Test function
if __name__ == "__main__":
    # Test the AI analysis
    test_title = "Unsafe area near metro station"
    test_description = "Walking alone at night, a group of men followed me from the metro station. Very scared. Poor lighting in the area."
    
    result = analyze_safety_report(test_title, test_description, "harassment")
    print("\nAI Analysis Result:")
    print(json.dumps(result, indent=2))
