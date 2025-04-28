# Atmos-AI Chennai Weather Forecasting System

An AI-powered weather forecasting system that combines LSTM-trained historical weather data with Llama-4-Scout-17B-16E-Instruct Multimodel by Meta-AI for advanced natural language generation to provide detailed and engaging weather forecasts for Chennai.

## Overview

This project uses a combination of technologies to deliver accurate and natural-sounding weather forecasts:
- Historical weather data trained using LSTM (Long Short-Term Memory) networks.
- MongoDB for storing the LSTM-predicted weather data.
- Llama-4-Scout-17B-16E-Instruct Multimodel (AI Model) by Meta-AI for natural language generation using Groq API.
- FastAPI backend for serving predictions.
- Interactive web frontend for user queries.

## Features

- Interactive date selection up to February 18, 2026.
- Customizable forecast length (100-300 words).
- Real-time weather data visualization.
- Automatic disaster warnings detection.
- Responsive web interface.

## Technical Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python, FastAPI
- **Database**: MongoDB (storing LSTM-trained predictions)
- **AI/ML**: 
  - ML Model - LSTM for weather prediction training
  - AI Model - Llama-4-Scout-17B-16E-Instruct Multimodel (AI Model) by Meta-AI for natural language generation using Groq API
- **APIs**: RESTful endpoints for forecast generation

## Data Preparation and LSTM Training

1. Prepare your historical weather data in CSV format:
```csv
Refer the .csv file in lstm_predictions folder
```

2. Train the LSTM model:
```bash
Run the .ipynb file in lstm_predictions folder.
A predictions.csv file will be generated once the lstm model is trained.
```

3. Import predictions to MongoDB:
```bash
Using MongoDB Compass ingest the predictions data into a collection.
```

## Getting Started

1. Clone the repository:
```bash
git clone https://github.com/adityadeshpande03/atmos-ai-chennai-weather.git
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

6. Open `frontend_prod_level/index.html` in your browser

## Data Flow

1. Historical weather data was initially processed and trained using LSTM networks
2. Trained predictions were stored in MongoDB for quick access
3. When a user requests a forecast using the frontend:
   - The system retrieves LSTM-predicted data from MongoDB
   - Processes it through disaster warning detection
   - Generates natural language forecasts using Llama-4-Scout-17B-16E-Instruct Multimodel (AI Model) by Meta-AI using Groq API
   - Returns formatted response to the frontend

## Environment Setup

The project requires the following environment variables:
```bash
MONGODB_URI=mongodb://localhost:27017
GROQ_API_KEY=your_groq_api_key
```
