// Weather icons SVG
const weatherIcons = {
  sunny: `<img src="./cloudy-day-3.svg" alt="Sunny Weather" style="width: 64px; height: 64px;">`,
  cloudy: `<img src="./cloudy-day-3.svg" alt="Cloudy Weather" style="width: 64px; height: 64px;">`,
  rainy: `<img src="./cloudy-day-3.svg" alt="Rainy Weather" style="width: 64px; height: 64px;">`,
  thunder: `<img src="./cloudy-day-3.svg" alt="Thunderstorm Weather" style="width: 64px; height: 64px;">`
};

// Initialize flatpickr calendar
document.addEventListener('DOMContentLoaded', function() {
  const dateInput = document.getElementById('date');
  flatpickr(dateInput, {
    dateFormat: "Y-m-d",
    minDate: "2024-01-01",
    maxDate: "2026-02-18",
    defaultDate: "today",
    altInput: true,
    altFormat: "F j, Y",
    disableMobile: true,
    clickOpens: true,
    allowInput: false
  });
});

// Form submission
document.getElementById('weatherForm').addEventListener('submit', handleWeatherSubmit);

async function handleWeatherSubmit(e) {
  e.preventDefault();

  const date = document.getElementById('date').value;
  const reportLength = document.getElementById('reportLength').value;
  const errorDiv = document.getElementById('error');
  
  errorDiv.classList.remove('visible');
  errorDiv.textContent = '';

  // Add user message to chat
  addMessage('user', `Requesting weather forecast for ${date} (${reportLength} words)`);

  try {
    // Check if we're running from file:// protocol
    const isFileProtocol = window.location.protocol === 'file:';
    
    // Use the appropriate server URL
    const baseUrl = isFileProtocol ? 'http://localhost:8000' : '';
    const apiUrl = `${baseUrl}/api/generate_forecast`;
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({
        date: date,
        style: 'balanced',
        report_length: parseInt(reportLength)
      }),
    });

    if (!response.ok) {
      let errorMessage = 'Failed to get forecast';
      
      if (response.status === 404) {
        errorMessage = `No weather data found for ${date}. Please try a date between January 1, 2024 and February 18, 2026.`;
      } else {
        try {
          const errorData = await response.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = await response.text();
        }
      }
      
      throw new Error(errorMessage);
    }

    const data = await response.json();
    
    // Add weather response to chat
    addWeatherResponse(data);

    // Clear input after sending
    document.getElementById('date').value = '';
    
  } catch (error) {
    console.error('Error in handleWeatherSubmit:', error);
    let errorMessage = error.message;
    
    if (error.message === 'Failed to fetch') {
      const isFileProtocol = window.location.protocol === 'file:';
      if (isFileProtocol) {
        errorMessage = 'Unable to connect to server. When running from a file:// URL, please ensure the FastAPI server is running at http://localhost:8000';
      } else {
        errorMessage = 'Unable to connect to server. Please ensure the FastAPI server is running.';
      }
    }
    
    showError(errorMessage);
  }
}

function showError(message) {
  const errorDiv = document.getElementById('error');
  errorDiv.textContent = message;
  errorDiv.classList.add('visible');
  
  setTimeout(() => {
    errorDiv.classList.remove('visible');
  }, 5000);
}

function addMessage(sender, content) {
  const chatContainer = document.getElementById('chatContainer');
  const welcomeMessage = document.querySelector('.welcome-message');
  if (welcomeMessage && chatContainer.children.length > 1) {
    welcomeMessage.remove();
  }

  const messageDiv = document.createElement('div');
  messageDiv.className = `message ${sender}-message`;
  messageDiv.textContent = content;
  
  chatContainer.appendChild(messageDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addWeatherResponse(weatherData) {
  const chatContainer = document.getElementById('chatContainer');
  const date = new Date(weatherData.date);
  
  // Determine weather icon based on conditions
  let weatherIcon = weatherIcons.cloudy; // default
  if (weatherData.data_used.precipitation > 5) {
    weatherIcon = weatherIcons.rainy;
  } else if (weatherData.data_used.precipitation > 0) {
    weatherIcon = weatherIcons.thunder;
  } else if (weatherData.data_used.temperature_2m > 25) {
    weatherIcon = weatherIcons.sunny;
  }

  // Format weather stats
  const temp = Number(weatherData.data_used.temperature_2m).toFixed(1);
  const humidity = Number(weatherData.data_used.relative_humidity_2m).toFixed(1);
  const precipitation = Number(weatherData.data_used.precipitation).toFixed(1);
  const windSpeed = Number(weatherData.data_used.wind_speed_10m).toFixed(1);
  
  // Process forecast text for warnings
  let forecastText = weatherData.forecast;
  let warningsHtml = '';
  
  if (weatherData.disaster_warnings && Object.keys(weatherData.disaster_warnings).length > 0) {
    const warningRegex = /(Weather Warnings:[\s\S]*?)(?=\n\n|$)/g;
    const warningsMatch = forecastText.match(warningRegex);
    if (warningsMatch) {
      warningsHtml = `<div class="weather-warning">
        <h3>⚠️ Weather Warnings</h3>
        ${marked.parse(warningsMatch[0].replace('Weather Warnings:', ''))}
      </div>`;
      forecastText = forecastText.replace(warningRegex, '');
    }
  }
  
  const messageDiv = document.createElement('div');
  messageDiv.className = 'message bot-message';
  messageDiv.innerHTML = `
    <p>Weather forecast for ${date.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
    <div class="weather-card">
      <div class="weather-icon">${weatherIcon}</div>
      <div class="weather-stats">
        <div class="weather-stat">
          <span class="value">${temp}°C</span>
          <span class="label">Temperature</span>
        </div>
        <div class="weather-stat">
          <span class="value">${humidity}%</span>
          <span class="label">Humidity</span>
        </div>
        <div class="weather-stat">
          <span class="value">${precipitation}mm</span>
          <span class="label">Precipitation</span>
        </div>
        <div class="weather-stat">
          <span class="value">${windSpeed}km/h</span>
          <span class="label">Wind Speed</span>
        </div>
      </div>
      <div class="forecast-toggle">Show Detailed Forecast ▼</div>
      <div class="weather-forecast">
        ${marked.parse(forecastText)}
        ${warningsHtml}
      </div>
    </div>
  `;
  
  chatContainer.appendChild(messageDiv);
  
  // Add click event to toggle forecast
  const forecastToggle = messageDiv.querySelector('.forecast-toggle');
  const weatherForecast = messageDiv.querySelector('.weather-forecast');
  
  forecastToggle.addEventListener('click', () => {
    weatherForecast.classList.toggle('visible');
    forecastToggle.textContent = weatherForecast.classList.contains('visible') ? 
      'Hide Detailed Forecast ▲' : 'Show Detailed Forecast ▼';
  });
  
  // Scroll to bottom
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Global error handler
window.addEventListener('unhandledrejection', function(event) {
  console.error('Unhandled promise rejection:', event.reason);
  const errorDiv = document.getElementById('error');
  if (errorDiv) {
    const errorMessage = event.reason.message || 'Network error occurred';
    errorDiv.textContent = errorMessage;
    errorDiv.classList.add('visible');
  }
});