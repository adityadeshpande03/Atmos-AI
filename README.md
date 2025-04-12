# Atmos-AI Chennai Weather Forecasting System

An AI-powered weather forecasting system that combines LSTM-trained historical weather data with advanced natural language generation to provide detailed and engaging weather forecasts for Chennai.

## Overview

This project uses a combination of technologies to deliver accurate and natural-sounding weather forecasts:
- Historical weather data trained using LSTM (Long Short-Term Memory) networks
- MongoDB for storing the LSTM-predicted weather data
- Groq LLM for natural language generation
- FastAPI backend for serving predictions
- Interactive web frontend for user queries

## Features

- Interactive date selection up to February 18, 2026
- Customizable forecast length (100-500 words)
- Real-time weather data visualization
- Automatic disaster warnings detection
- Responsive web interface

## Technical Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, FastAPI
- **Database**: MongoDB (storing LSTM-trained predictions)
- **AI/ML**: 
  - LSTM for weather prediction training
  - Groq LLM for natural language generation
- **APIs**: RESTful endpoints for forecast generation

## Data Preparation and LSTM Training

1. Prepare your historical weather data in CSV format:
```csv
date,temperature,humidity,precipitation,wind_speed,pressure
2024-01-01,28.5,75,0.2,12,1012
```

2. Train the LSTM model:
```bash
python src/train_lstm.py --input data/weather_history.csv --epochs 100 --batch_size 32
```

3. Generate predictions using trained model:
```bash
python src/generate_predictions.py --model models/lstm_model.h5 --forecast_days 365
```

4. Import predictions to MongoDB:
```bash
python src/import_to_mongodb.py --predictions predictions.csv
```

MongoDB document structure:
```json
{
    "date": "2025-01-01",
    "predictions": {
        "temperature": 28.5,
        "humidity": 75.0,
        "precipitation": 0.2,
        "wind_speed": 12.0,
        "pressure": 1012.0
    }
}
```

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/yourusername/atmos-ai-chennai-weather.git
cd atmos-ai-chennai-weather
```

2. Create and activate virtual environment:
```bash
python -m venv venv
.\venv\Scripts\activate  # On Windows
source venv/bin/activate # On Unix/MacOS
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start the MongoDB service:
```bash
mongod --dbpath data/db
```

5. Start the FastAPI server:
```bash
uvicorn src.app:app --reload --port 8000
```

6. Open `frontend/index.html` in your browser

## Data Flow

1. Historical weather data was initially processed and trained using LSTM networks
2. Trained predictions were stored in MongoDB for quick access
3. When a user requests a forecast:
   - The system retrieves LSTM-predicted data from MongoDB
   - Processes it through disaster warning detection
   - Generates natural language forecasts using Groq LLM
   - Returns formatted response to the frontend

## Environment Setup

The project requires the following environment variables:
```bash
MONGODB_URI=mongodb://localhost:27017
GROQ_API_KEY=your_groq_api_key
```


## Note

The weather predictions available in this system are based on LSTM-trained models and should be used for demonstration purposes only. Always refer to official weather services for critical weather-related decisions.
