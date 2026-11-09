# 🌦️ My Own AI Weather App

A smart AI-powered weather application built using **Python, FastAPI, Streamlit, Ollama Local AI, MCP, SQLite, Pandas, Plotly, and HTTPX**.

The application provides weather information, forecasts, weather history, interactive visualizations, and an AI-powered weather assistant using a locally running AI model.

---

## ✨ Features

- 🔍 Search weather by city name
- 🌡️ Current weather conditions
- 🕐 Hourly weather forecast
- 📅 7-day weather forecast
- 🗄️ Weather history using SQLite
- 🤖 AI-powered weather assistant
- 🧠 Local AI using Ollama
- 🔌 Custom Weather REST API
- 🛠️ MCP weather tools
- 📊 Interactive weather dashboard
- 📈 Weather charts and data visualization

---

## 🛠️ Technologies Used

- Python
- Streamlit
- FastAPI
- Ollama
- MCP
- SQLite
- Pandas
- Plotly
- HTTPX

---

## 📁 Project Structure

```text
AI-Weather-App/
│
├── Frontend/
│   ├── app.py
│   ├── style.css
│   └── assets/
│
├── Backend/
│   ├── main.py
│   ├── weather_api.py
│   ├── ai_agent.py
│   ├── mcp_server.py
│   └── mcp_client.py
│
├── Database/
│   └── history.py
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🗄️ Database

The application uses **SQLite** for storing weather-related data.

The database is stored at:

```text
Database/weather_history.db
```

The database is initialized automatically when the backend imports `Database.history`.

### Database Tables

#### `weather_history`

Stores current weather snapshots and advanced metrics such as:

- UV Index
- AQI
- Visibility
- Wind Gusts
- Sunrise
- Sunset

#### `favorite_cities`

Stores:

- Saved cities
- Coordinates
- Last-viewed timestamps

#### `search_history`

Stores:

- City search queries
- Search result counts

#### `app_settings`

Stores application preferences using key/value pairs.

Existing weather history is preserved. Missing tables and columns can be added automatically without deleting the existing database file.

---

## ⚙️ Installation

### 1. Clone the Project

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd AI-Weather-App
```

---

### 2. Create a Virtual Environment

```bash
py -3.12 -m venv venv
```

---

### 3. Activate the Environment

#### Windows PowerShell

```powershell
.\venv\Scripts\Activate.ps1
```

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5. Configure Environment Variables

Create a `.env` file in the project root:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:1.5b

WEATHER_API_HOST=127.0.0.1
WEATHER_API_PORT=8000
```

---

## 🤖 Start Ollama

Make sure **Ollama** is installed and running.

If the model is not already installed, pull it using:

```bash
ollama pull qwen2.5:1.5b
```

The application uses the local AI model:

```text
qwen2.5:1.5b
```

---

# 🚀 Run the Application

## Start the Weather API

From the project root, run:

```powershell
uvicorn main:app --reload --app-dir Backend
```

The FastAPI backend will run on:

```text
http://127.0.0.1:8000
```

---

## 📚 Open API Documentation

FastAPI automatically provides interactive API documentation at:

```text
http://127.0.0.1:8000/docs
```

---

## 🖥️ Start the Streamlit Frontend

Open another terminal and run:

```powershell
streamlit run Frontend/app.py
```

Streamlit will open the weather application in your browser.

---

# 🌦️ Weather Data Source

The initial implementation uses **Open-Meteo** as the weather data source.

The application flow is:

```text
User
  ↓
Streamlit Frontend
  ↓
FastAPI Backend
  ↓
Weather API
  ↓
Open-Meteo
  ↓
Weather Data
  ↓
Dashboard + AI Assistant
```

The custom FastAPI backend provides application-specific API endpoints over the weather data source.

---

# 🤖 AI Assistant Workflow

The AI weather assistant uses a local AI model through Ollama.

```text
User Question
      ↓
AI Weather Assistant
      ↓
MCP Weather Tools
      ↓
Weather Information
      ↓
Ollama
      ↓
Qwen 2.5 Model
      ↓
AI Response
```

The local AI model processes user questions and helps provide weather-related assistance.

---

# 📊 Weather Dashboard

The dashboard can display:

- Current weather conditions
- Temperature
- Feels-like temperature
- Weather condition
- Hourly forecast
- 7-day forecast
- UV Index
- Rain probability
- Cloud cover
- Sunrise and sunset
- Air quality information
- Weather history
- Interactive charts

---

## 📈 Data Visualization

The project uses tools such as:

- **Pandas** for data processing
- **Plotly** for interactive charts and visualizations

These tools help present weather information in a more interactive and understandable format.

---

# 🧠 MCP Integration

MCP weather tools are used to connect the AI assistant with weather-related functionality.

The MCP integration includes components such as:

```text
mcp_server.py
mcp_client.py
```

These components support communication between the AI assistant and weather tools.

---

## 📌 Project Status

🚧 **Under Development**

More features and weather-data integrations may be added in future versions.

---

## 👨‍💻 Developer

**Nitin Tripathi**

Built with **Python, FastAPI, Streamlit, Local AI, Ollama, MCP, SQLite, Pandas, Plotly, and HTTPX**.