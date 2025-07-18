// Add initial welcome message when page loads
document.addEventListener('DOMContentLoaded', function() {
  // Initialize flatpickr calendar with updated date range
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

  addMessageToChat('bot', 'Welcome to Atmos - AI Powered weather forecaster.<br>Please select a date (available until 18 February 2026) to get a weather forecast.');
});

document.getElementById('weatherForm').addEventListener('submit', handleWeatherSubmit);

async function handleWeatherSubmit(e) {
  e.preventDefault();

  const date = document.getElementById('date').value;
  const reportLength = document.getElementById('reportLength').value;
  const errorDiv = document.getElementById('error');
  const chatContainer = document.getElementById('chatContainer');
  
  errorDiv.classList.remove('visible');
  errorDiv.textContent = '';

  addMessageToChat('user', `Date: ${date} (${reportLength} words report)`);

  try {
    console.log('Sending request for date:', date, 'report length:', reportLength);
    
    // Check if we're running from file:// protocol
    const isFileProtocol = window.location.protocol === 'file:';
    
    // Use the appropriate server URL based on how the app is loaded
    const baseUrl = isFileProtocol ? 'http://localhost:8000' : '';
    const apiUrl = `${baseUrl}/api/generate_forecast`;
    
    console.log('Using API URL:', apiUrl);
    
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

    console.log('Response status:', response.status);
    
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
    console.log('Received data:', data);

    const messageDiv = document.createElement('div');
    messageDiv.className = 'chat-message bot';
    messageDiv.appendChild(createWeatherCard(data));
    chatContainer.appendChild(messageDiv);
    
    // Ensure proper scrolling after card is generated
    requestAnimationFrame(() => {
      chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
      });
    });
    
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
  
  // Clear input after sending
  document.getElementById('date').value = '';
}

// Add new function to handle error display
function showError(message) {
  const errorDiv = document.getElementById('error');
  errorDiv.textContent = message;
  errorDiv.classList.add('visible');
  
  // Optional: Hide error after 5 seconds
  setTimeout(() => {
    errorDiv.classList.remove('visible');
  }, 5000);
}

function addMessageToChat(sender, message) {
  const chatContainer = document.getElementById('chatContainer');
  const messageDiv = document.createElement('div');
  messageDiv.className = `chat-message ${sender}`;
  
  if (sender === 'bot') {
    // Convert markdown to HTML using marked library
    messageDiv.innerHTML = marked.parse(message);
  } else {
    messageDiv.textContent = message;
  }
  
  chatContainer.appendChild(messageDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function createWeatherCard(weatherData) {
  const card = document.createElement('div');
  card.className = 'weather-card';

  // Update SVG icon to use external file
  const iconContainer = document.createElement('div');
  iconContainer.style.textAlign = 'center';
  iconContainer.style.marginBottom = '20px';
  iconContainer.innerHTML = `
    <img src="cloudy-day-3.svg" alt="Weather Icon" style="width: 64px; height: 64px;">
  `;
  card.appendChild(iconContainer);

  const grid = document.createElement('div');
  grid.className = 'weather-grid';

  const weatherItems = [
    { label: 'Temperature', value: `${Number(weatherData.data_used.temperature_2m).toFixed(2)}°C` },
    { label: 'Humidity', value: `${Number(weatherData.data_used.relative_humidity_2m).toFixed(2)}%` },
    { label: 'Precipitation', value: `${Number(weatherData.data_used.precipitation).toFixed(2)}mm` },
    { label: 'Wind Speed', value: `${Number(weatherData.data_used.wind_speed_10m).toFixed(2)}km/h` }
  ];

  weatherItems.forEach(item => {
    const weatherItem = document.createElement('div');
    weatherItem.className = 'weather-item';
    weatherItem.innerHTML = `
      <span class="label">${item.label}</span>
      <span class="value">${item.value}</span>
    `;
    grid.appendChild(weatherItem);
  });

  const response = document.createElement('div');
  response.className = 'weather-response';
  
  // Process the forecast text to ensure the warnings are properly styled
  let forecastText = weatherData.forecast;
  
  // Check if there are actual warnings from the API response
  if (weatherData.disaster_warnings && Object.keys(weatherData.disaster_warnings).length > 0) {
    // Find and style the warnings section without relying on markdown characters
    const warningRegex = /(Weather Warnings:[\s\S]*?)(?=\n\n|$)/g;
    forecastText = forecastText.replace(warningRegex, '<div class="highlighted-warnings">$1</div>');
  }
  
  response.innerHTML = marked.parse(forecastText);

  // Add a hint text
  const hintText = document.createElement('div');
  hintText.style.textAlign = 'center';
  hintText.style.color = '#666';
  hintText.style.fontSize = '0.9rem';
  hintText.style.marginTop = '10px';
  hintText.textContent = 'Click to see detailed analysis';

  card.appendChild(grid);
  card.appendChild(hintText);
  card.appendChild(response);

  card.addEventListener('click', () => {
    response.classList.toggle('visible');
    hintText.style.display = response.classList.contains('visible') ? 'none' : 'block';
  });

  return card;
}
