from pymongo import MongoClient
from groq import Groq
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Settings:
    MONGO_URI = "mongodb://localhost:27017/"
    DB_NAME = "weather_data"
    COLLECTION_NAME = "weather_data"
    GROQ_API_KEY = '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'
    
    # Updated disaster warning thresholds with lower values to detect even minor warnings
    DISASTER_THRESHOLDS = {
        "heavy_rain": 20.0,  # mm precipitation (lowered from 30.0)
        "flood_risk": 40.0,  # mm precipitation (lowered from 50.0)
        "severe_wind": 50.0,  # km/h wind speed (lowered from 60.0)
        "high_wind": 30.0,   # km/h wind speed (new minor threshold)
        "extreme_heat": 38.0, # °C (lowered from 40.0)
        "hot_weather": 34.0,  # °C (new minor threshold)
        "high_humidity": 80.0, # % (new threshold)
        "cyclone_risk": 70.0, # km/h wind with heavy rain (lowered from 80.0)
        "drought_risk": {
            "max_temp": 33.0,  # °C (lowered from 35.0)
            "max_humidity": 40.0,  # % (raised from 30.0 to be more sensitive)
            "max_precipitation": 1.0,  # mm (raised from 0.5 to be more sensitive)
        }
    }

def get_db():
    """Creates database connection"""
    try:
        client = MongoClient(Settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client[Settings.DB_NAME]
        collection = db[Settings.COLLECTION_NAME]
        return client, collection
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        raise

# Initialize clients
client_groq = Groq(api_key=Settings.GROQ_API_KEY)
mongo_client, collection = get_db()

def format_date(date_str: str) -> str:
    """Format YYYY-MM-DD to include default time"""
    return f"{date_str} 23:00:00+00:00"

def check_mongo_connection():
    """Check if MongoDB connection is alive and reconnect if needed"""
    global mongo_client, collection
    try:
        if mongo_client is None or not mongo_client.is_primary:
            logger.warning("MongoDB connection lost, attempting to reconnect...")
            mongo_client, collection = get_db()
        return mongo_client is not None
    except:
        return False

def format_date_with_default_time(date_str: str) -> str:
    """Add default time to YYYY-MM-DD date format"""
    return f"{date_str} 23:00:00+00:00"

# Update how we get weather data
def get_weather_data(date_str: str):
    """Get weather data for a specific date"""
    query_date = format_date_with_default_time(date_str)
    return collection.find_one({"date": query_date}, {"_id": 0})

def detect_disaster_warnings(weather_data):
    """
    Applies rule-based filtering to detect potential disaster conditions
    Returns a dictionary with disaster types and severity levels
    """
    if not weather_data:
        return {}
    
    warnings = {}
    thresholds = Settings.DISASTER_THRESHOLDS
    
    # Check for heavy rain and flooding
    precipitation = float(weather_data.get('precipitation', 0))
    if precipitation >= thresholds["flood_risk"]:
        warnings["flood"] = {
            "level": "severe",
            "message": f"SEVERE FLOOD RISK: Extreme precipitation of {precipitation}mm expected."
        }
    elif precipitation >= thresholds["heavy_rain"]:
        warnings["flood"] = {
            "level": "moderate",
            "message": f"FLOOD WATCH: Heavy rainfall of {precipitation}mm expected."
        }
    elif precipitation >= 10.0:  # Even minor rain warning
        warnings["rain"] = {
            "level": "minor",
            "message": f"Moderate rainfall of {precipitation}mm expected."
        }
    
    # Check for wind conditions
    wind_speed = float(weather_data.get('wind_speed_10m', 0))
    wind_gusts = float(weather_data.get('wind_gusts_10m', 0))
    max_wind = max(wind_speed, wind_gusts)
    
    if max_wind >= thresholds["severe_wind"]:
        warnings["wind"] = {
            "level": "severe",
            "message": f"SEVERE WIND WARNING: Wind speeds up to {max_wind}km/h expected."
        }
    elif max_wind >= thresholds["high_wind"]:
        warnings["wind"] = {
            "level": "moderate",
            "message": f"WIND ADVISORY: Strong winds up to {max_wind}km/h expected."
        }
    elif max_wind >= 20.0:  # Even light wind warning
        warnings["wind"] = {
            "level": "minor",
            "message": f"Breezy conditions with winds up to {max_wind}km/h expected."
        }
    
    # Check for temperature conditions
    temperature = float(weather_data.get('temperature_2m', 0))
    if temperature >= thresholds["extreme_heat"]:
        warnings["heat"] = {
            "level": "severe",
            "message": f"EXTREME HEAT WARNING: Temperatures reaching {temperature}°C expected."
        }
    elif temperature >= thresholds["hot_weather"]:
        warnings["heat"] = {
            "level": "moderate",
            "message": f"HEAT ADVISORY: Hot weather with temperatures of {temperature}°C expected."
        }
    elif temperature >= 30.0:  # Even warm weather
        warnings["heat"] = {
            "level": "minor",
            "message": f"Warm weather with temperatures of {temperature}°C expected."
        }
    elif temperature <= 10.0:  # Cold weather
        warnings["cold"] = {
            "level": "minor",
            "message": f"Cool conditions with temperatures of {temperature}°C expected."
        }
    
    # Check for humidity conditions
    humidity = float(weather_data.get('relative_humidity_2m', 50))
    if humidity >= thresholds["high_humidity"]:
        warnings["humidity"] = {
            "level": "moderate",
            "message": f"HIGH HUMIDITY: Uncomfortable conditions with humidity at {humidity}%."
        }
    elif humidity >= 70.0:  # Even moderate humidity
        warnings["humidity"] = {
            "level": "minor",
            "message": f"Moderately humid conditions ({humidity}%) may cause discomfort."
        }
    
    # Check for cyclone conditions (high winds + rain)
    if max_wind >= thresholds["cyclone_risk"] and precipitation >= thresholds["heavy_rain"]:
        warnings["cyclone"] = {
            "level": "severe",
            "message": f"CYCLONE WARNING: High winds ({max_wind}km/h) with heavy rainfall ({precipitation}mm)."
        }
    elif max_wind >= 40.0 and precipitation >= 15.0:  # Even moderate storm
        warnings["storm"] = {
            "level": "moderate",
            "message": f"STORM CONDITIONS: Moderate winds ({max_wind}km/h) with rainfall ({precipitation}mm)."
        }
    
    # Check for drought conditions
    drought_threshold = thresholds["drought_risk"]
    if (temperature >= drought_threshold["max_temp"] and 
        humidity <= drought_threshold["max_humidity"] and 
        precipitation <= drought_threshold["max_precipitation"]):
        warnings["drought"] = {
            "level": "moderate",
            "message": f"DROUGHT CONDITIONS: High temperature ({temperature}°C), low humidity ({humidity}%), minimal precipitation."
        }
    
    # Check for cloudiness if relevant
    cloud_cover = float(weather_data.get('cloud_cover', 0))
    if cloud_cover >= 80:
        warnings["clouds"] = {
            "level": "minor",
            "message": f"OVERCAST CONDITIONS: Heavy cloud cover ({cloud_cover}%) expected."
        }
    
    # Check pressure for potential weather changes
    pressure = float(weather_data.get('pressure_msl', 1013.25))
    if pressure < 1000:
        warnings["pressure"] = {
            "level": "minor",
            "message": f"LOW PRESSURE SYSTEM: Atmospheric pressure of {pressure}hPa may lead to unsettled weather."
        }
    elif pressure > 1025:
        warnings["pressure"] = {
            "level": "minor",
            "message": f"HIGH PRESSURE SYSTEM: Atmospheric pressure of {pressure}hPa indicating stable conditions."
        }
        
    return warnings

# Define the target date (ensure format matches your MongoDB storage format)
target_date = "2025-02-28"

# Retrieve weather data from MongoDB
if not check_mongo_connection():
    print("Failed to connect to MongoDB.")
    exit()

weather_data = get_weather_data(target_date)

if not weather_data:
    print(f"No weather data found for {target_date}.")
    exit()

# Detect disaster warnings
disaster_warnings = detect_disaster_warnings(weather_data)

# Construct the dynamic prompt
prompt = f"""
Generate a **full-day weather forecast** for {target_date} based on the following data.
Do not mention "today" or "tomorrow"—just focus on the future weather for this date.

Vary the summary format every time. Sometimes make it **detailed and scientific**, 
other times **casual and conversational**, or even **like a weather reporter's broadcast**. 
Make sure the response feels **unique, natural, and engaging** each time.

Here is the predicted weather data:

- **Temperature:** {weather_data['temperature_2m']}°C (Feels like {weather_data['apparent_temperature']}°C)
- **Humidity:** {weather_data['relative_humidity_2m']}%
- **Dew Point:** {weather_data['dew_point_2m']}°C
- **Precipitation:** {weather_data['precipitation']} mm (Rain: {weather_data['rain']} mm, Snowfall: {weather_data['snowfall']} mm)
- **Snow Depth:** {weather_data['snow_depth']} mm
- **Atmospheric Pressure:** {weather_data['pressure_msl']} hPa (Surface Pressure: {weather_data['surface_pressure']} hPa)
- **Cloud Cover:** {weather_data['cloud_cover']}% (Low: {weather_data['cloud_cover_low']}%, Mid: {weather_data['cloud_cover_mid']}%, High: {weather_data['cloud_cover_high']}%)
- **Wind Speed:** {weather_data['wind_speed_10m']} km/h at 10m, {weather_data['wind_speed_100m']} km/h at 100m
- **Wind Direction:** {weather_data['wind_direction_10m']}° at 10m, {weather_data['wind_direction_100m']}° at 100m
- **Wind Gusts:** {weather_data['wind_gusts_10m']} km/h

Make sure the response is **not boring** and feels like a real forecast.
"""

# Include disaster warnings in the prompt if any
if disaster_warnings:
    prompt += "\n\nDisaster Warnings:\n"
    for warning_type, warning_details in disaster_warnings.items():
        prompt += f"- **{warning_type.capitalize()}** ({warning_details['level']}): {warning_details['message']}\n"

# Send the prompt to Groq's LLM
completion = client_groq.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": prompt}],
    temperature=1,
    max_completion_tokens=1024,
    top_p=1,
    stream=True
)

# Stream the response properly
print("\n📡 Future Weather Forecast:\n")
for chunk in completion:
    if hasattr(chunk, "choices") and chunk.choices:  # Ensure chunk has choices
        content = chunk.choices[0].delta.content
        if content:  # Avoid printing None or empty content
            print(content, end="", flush=True)

# Close MongoDB connection
if mongo_client:
    mongo_client.close()
