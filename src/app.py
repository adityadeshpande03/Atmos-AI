from fastapi import FastAPI, HTTPException, Body, Request
from pymongo import MongoClient
from groq import Groq
import os
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from config import Settings, detect_disaster_warnings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Weather Forecast Generator",
              description="API for generating weather forecasts using Groq LLM and MongoDB data")

# Get the directory where the script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add CORS middleware with more permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic model for request
class ForecastRequest(BaseModel):
    date: str
    style: Optional[str] = "balanced"  # balanced, detailed, casual, broadcast
    report_length: Optional[int] = 200  # Default to 200 words
    
# Pydantic model for disaster warning
class DisasterWarning(BaseModel):
    level: str  # severe, moderate, minor
    message: str

# Updated Pydantic model for response
class ForecastResponse(BaseModel):
    date: str
    forecast: str
    data_used: Dict[str, Any]
    disaster_warnings: Dict[str, DisasterWarning] = {}

# Startup event to initialize connections
@app.on_event("startup")
async def startup_db_client():
    # Set up Groq API key
    app.groq_api_key = os.getenv("GROQ_API_KEY", Settings.GROQ_API_KEY)
    if not app.groq_api_key:
        raise ValueError("Missing Groq API key. Set GROQ_API_KEY as an environment variable.")
    
    # Initialize Groq client
    app.groq_client = Groq(api_key=app.groq_api_key)
    
    try:
        # Connect to MongoDB
        mongo_uri = os.getenv("MONGODB_URI", Settings.MONGO_URI)
        app.mongodb_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Test the connection
        app.mongodb_client.admin.command('ping')
        app.db = app.mongodb_client[Settings.DB_NAME]
        
        # Ensure the collection exists
        if "weather_data" not in app.db.list_collection_names():
            app.db.create_collection("chennai_weather")
            logger.warning("Created 'weather_data' collection as it did not exist")
        
        logger.info("Connected to MongoDB and initialized Groq client")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {str(e)}")
        # Continue running without MongoDB for testing/development
        app.mongodb_client = None
        app.db = None

# Shutdown event to close connections
@app.on_event("shutdown")
async def shutdown_db_client():
    if hasattr(app, 'mongodb_client') and app.mongodb_client:
        app.mongodb_client.close()
        logger.info("Closed MongoDB connection")

# Main endpoint to generate forecast
@app.post("/api/generate_forecast")
async def generate_forecast(request: ForecastRequest):
    logger.info(f"Received request: {request}")
    try:
        # Validate and format date
        try:
            parsed_date = datetime.strptime(request.date, '%Y-%m-%d')
            formatted_date = parsed_date.strftime('%Y-%m-%d')  # Ensure consistent YYYY-MM-DD format
            logger.info(f"Formatted date: {formatted_date}")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Check MongoDB connection
        if not hasattr(app, 'db') or app.db is None:
            raise HTTPException(status_code=503, detail="Database connection is not available")
        
        # Query MongoDB with exact date match - try both collection names
        weather_data = None
        
        # Try different collections and query formats
        collections_to_try = ["chennai_weather", "weather_data"]
        
        for collection_name in collections_to_try:
            if collection_name in app.db.list_collection_names():
                collection = app.db[collection_name]
                
                # Try exact date format first
                query1 = {"date": formatted_date}
                
                # Also try with regex to match date at beginning of string (for datetime fields)
                query2 = {"date": {"$regex": f"^{formatted_date}"}}
                
                # Try different date formats that might be in the database
                query3 = {"date": f"{formatted_date}T00:00:00Z"}
                query4 = {"date": f"{formatted_date} 00:00:00+00:00"}
                
                fields = { 
                    "_id": 0,
                    "date": 1,
                    "temperature_2m": 1,
                    "relative_humidity_2m": 1,
                    "dew_point_2m": 1,
                    "apparent_temperature": 1,
                    "precipitation": 1,
                    "rain": 1,
                    "snowfall": 1,
                    "snow_depth": 1,
                    "pressure_msl": 1,
                    "surface_pressure": 1,
                    "cloud_cover": 1,
                    "cloud_cover_low": 1,
                    "cloud_cover_mid": 1,
                    "cloud_cover_high": 1,
                    "wind_speed_10m": 1,
                    "wind_speed_100m": 1,
                    "wind_direction_10m": 1,
                    "wind_direction_100m": 1,
                    "wind_gusts_10m": 1,
                }
                
                # Try each query
                for query in [query1, query2, query3, query4]:
                    logger.info(f"Trying MongoDB query on {collection_name}: {query}")
                    result = collection.find_one(query, fields)
                    if result:
                        weather_data = result
                        logger.info(f"Found data in collection {collection_name} with query {query}")
                        break
                
                if weather_data:
                    break
        
        # If no data found, log available data for debugging
        if not weather_data:
            logger.warning(f"No weather data found for date: {formatted_date}")
            
            # Log a sample of data to help debug
            for collection_name in collections_to_try:
                if collection_name in app.db.list_collection_names():
                    collection = app.db[collection_name]
                    sample = list(collection.find().limit(1))
                    if sample:
                        logger.info(f"Sample data from {collection_name}: {sample}")
                        
                    # Check date format in the collection
                    dates_sample = list(collection.find({}, {"date": 1, "_id": 0}).limit(5))
                    if dates_sample:
                        logger.info(f"Sample dates from {collection_name}: {dates_sample}")
            
            raise HTTPException(status_code=404, detail=f"No weather data found for {formatted_date}. Please try a different date between 2024-01-01 and 2026-02-18.")
        
        # Apply disaster warning detection rules
        disaster_warnings = detect_disaster_warnings(weather_data)
        
        # Determine style instruction based on request
        style_instructions = {
            "balanced": "Vary the summary format. Sometimes make it detailed and scientific, other times casual and conversational.",
            "detailed": "Make the forecast detailed and scientific with technical meteorological information.",
            "casual": "Make the forecast casual and conversational, as if talking to a friend.",
            "broadcast": "Format the forecast like a professional weather reporter's broadcast script."
        }
        
        style_text = style_instructions.get(request.style, style_instructions["balanced"])
        
        # Create a formatted warnings section for the LLM
        warnings_section = ""
        if disaster_warnings:
            warnings_section = "\n\nWeather Warnings:\n\n"
            for warning_type, warning_info in disaster_warnings.items():
                severity = warning_info['level'].upper()
                warnings_section += f"- {severity}: {warning_info['message']}\n"
        else:
            warnings_section = "\n\nWeather Warnings:\n\nNo weather warnings for this date.\n"
        
        # Add instruction to include the warnings section
        instructions_for_warnings = """
        Important: Make sure to include a 'Weather Warnings' section in your response,
        with the exact warnings provided below. Do not use markdown formatting like # or **.
        Format the warnings as a simple text section with the same style as your forecast.
        Include this section at the end of your forecast.
        """
        
        # Construct the dynamic prompt with specific word count instruction and warnings
        prompt = f"""
        Generate a weather forecast for {request.date} that is EXACTLY {request.report_length} words long.
        Base the forecast on the following weather data.
        Do not mention "today" or "tomorrow"—just focus on the future weather for this date.
        {style_text}
        {instructions_for_warnings}
        Make sure the response is engaging and natural.
        
        Weather data:
        - Temperature: {weather_data.get('temperature_2m', 'N/A')}°C (Feels like {weather_data.get('apparent_temperature', 'N/A')}°C)
        - Humidity: {weather_data.get('relative_humidity_2m', 'N/A')}%
        - Dew Point: {weather_data.get('dew_point_2m', 'N/A')}°C
        - Precipitation: {weather_data.get('precipitation', 'N/A')} mm (Rain: {weather_data.get('rain', 'N/A')} mm, Snowfall: {weather_data.get('snowfall', 'N/A')} mm)
        - Snow Depth: {weather_data.get('snow_depth', 'N/A')} mm
        - Pressure: {weather_data.get('pressure_msl', 'N/A')} hPa (Surface: {weather_data.get('surface_pressure', 'N/A')} hPa)
        - Cloud Cover: {weather_data.get('cloud_cover', 'N/A')}% (Low: {weather_data.get('cloud_cover_low', 'N/A')}%, Mid: {weather_data.get('cloud_cover_mid', 'N/A')}%, High: {weather_data.get('cloud_cover_high', 'N/A')}%)
        - Wind: {weather_data.get('wind_speed_10m', 'N/A')} km/h at 10m, gusting to {weather_data.get('wind_gusts_10m', 'N/A')} km/h
        
        {warnings_section}
        
        Remember: The response must be EXACTLY {request.report_length} words long. Not more, not less.
        Make the forecast natural and engaging while maintaining accuracy.
        Include the WEATHER WARNINGS section at the end of your forecast.
        """

        # Send the prompt to Groq's LLM with adjusted temperature for more consistent length
        logger.info(f"Sending prompt to Groq's LLM")
        try:
            completion = app.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": f"You are a weather forecaster. Generate forecasts that are exactly {request.report_length} words long."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1024,
                top_p=0.9,
            )
            
            # Extract the generated forecast
            forecast = completion.choices[0].message.content
            logger.info("Successfully received forecast from Groq")
        except Exception as e:
            logger.error(f"Error from Groq API: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error from language model service: {str(e)}")
        
        # Return response with forecast, data used, and disaster warnings
        return ForecastResponse(
            date=request.date,
            forecast=forecast,
            data_used=weather_data,
            disaster_warnings=disaster_warnings
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they already have status codes
        raise
    except Exception as e:
        logger.error(f"Error generating forecast: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating forecast: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    db_status = "connected" if (hasattr(app, 'mongodb_client') and app.mongodb_client) else "disconnected"
    return {
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

# Now mount static files - at a prefix that won't conflict with API routes
frontend_path = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# Create a specific route for file:// protocol access
@app.get("/api")
async def api_info():
    return {"message": "API is running. You can use /api/generate_forecast for weather forecasts."}

# Mount frontend files
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")