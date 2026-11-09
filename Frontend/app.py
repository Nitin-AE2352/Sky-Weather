
import os
import json
from pathlib import Path

import httpx
import pandas as pd
import streamlit as st
from dotenv import load_dotenv


# ==========================================
# APP CONFIGURATION
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_HOST = os.getenv("WEATHER_API_HOST", "127.0.0.1")
API_PORT = os.getenv("WEATHER_API_PORT", "8000")
API_URL = f"http://{API_HOST}:{API_PORT}"

APP_NAME = os.getenv("APP_NAME", "My Own Weather App")

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# LOAD CSS
# ==========================================

def load_css():
    css_path = Path(__file__).parent / "style.css"

    if css_path.exists():
        css = css_path.read_text(encoding="utf-8")
        st.markdown(
            f"<style>{css}</style>",
            unsafe_allow_html=True
        )


load_css()


# ==========================================
# SESSION STATE
# ==========================================

DEFAULT_STATE = {
    "weather_result": None,
    "selected_city": "Delhi",
    "chat_messages": [],
    "history_data": [],
    "mcp_tools": [],
    "mcp_tools_loaded": False,
}

for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==========================================
# API HELPER FUNCTIONS
# ==========================================

def api_get(endpoint, params=None):
    try:
        response = httpx.get(
            f"{API_URL}{endpoint}",
            params=params,
            timeout=30
        )

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get(
                "detail",
                error.response.text
            )
        except Exception:
            detail = error.response.text

        st.error(f"API Error: {detail}")
        return None

    except httpx.RequestError:
        st.error(
            "Backend connect nahi ho raha. "
            "Pehle FastAPI server start karo."
        )
        return None

    except Exception as error:
        st.error(f"Unexpected error: {error}")
        return None


def api_post(endpoint, payload):
    try:
        response = httpx.post(
            f"{API_URL}{endpoint}",
            json=payload,
            timeout=180
        )

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get(
                "detail",
                error.response.text
            )
        except Exception:
            detail = error.response.text

        st.error(f"API Error: {detail}")
        return None

    except httpx.RequestError:
        st.error("Backend server se connection nahi ho paya.")
        return None

    except Exception as error:
        st.error(f"Unexpected error: {error}")
        return None


def api_delete(endpoint):
    try:
        response = httpx.delete(
            f"{API_URL}{endpoint}",
            timeout=30
        )

        response.raise_for_status()
        return response.json()

    except httpx.HTTPStatusError as error:
        try:
            detail = error.response.json().get(
                "detail",
                error.response.text
            )
        except Exception:
            detail = error.response.text

        st.error(f"Delete Error: {detail}")
        return None

    except httpx.RequestError:
        st.error("Backend server se connection nahi ho paya.")
        return None

    except Exception as error:
        st.error(f"Unexpected error: {error}")
        return None


# ==========================================
# WEATHER DATA HELPERS
# ==========================================

def get_weather_data():
    result = st.session_state.weather_result

    if not isinstance(result, dict):
        return None

    return result.get("weather", {})


def get_city_data():
    result = st.session_state.weather_result

    if not isinstance(result, dict):
        return {}

    return result.get("city", {})


def get_current_data():
    weather = get_weather_data()

    if not isinstance(weather, dict):
        return {}

    return weather.get("current", {})


def format_value(value, suffix=""):
    if value is None:
        return "N/A"

    try:
        return f"{float(value):g}{suffix}"
    except (ValueError, TypeError):
        return f"{value}{suffix}"


def load_weather(city_name):
    city_name = city_name.strip()

    if not city_name:
        st.warning("City ka naam enter karo.")
        return False

    with st.spinner(f"{city_name} ka weather load ho raha hai..."):
        result = api_get(
            "/api/weather",
            params={"city": city_name}
        )

    if not result:
        return False

    if not isinstance(result, dict) or not result.get("weather"):
        st.error("Backend se valid weather data nahi mila.")
        return False

    st.session_state.weather_result = result

    city = result.get("city", {})

    st.session_state.selected_city = city.get(
        "name",
        city_name
    )

    st.session_state.chat_messages = []

    return True


# ==========================================
# HISTORY FUNCTIONS
# ==========================================

def load_history():
    result = api_get(
        "/api/weather/history",
        params={
            "city": st.session_state.selected_city,
            "limit": 20
        }
    )

    if isinstance(result, list):
        st.session_state.history_data = result

    elif isinstance(result, dict):
        st.session_state.history_data = result.get(
            "history",
            []
        )


def delete_history(record_id):
    result = api_delete(
        f"/api/weather/history/{record_id}"
    )

    if result is not None:
        st.success("History record deleted.")
        load_history()
        st.rerun()


def build_mcp_arguments(tool, selected_city):
    schema = tool.get("inputSchema") or {}
    properties = schema.get("properties") or {}
    required = set(schema.get("required") or [])
    arguments = {}
    validation_errors = []
    complex_values = {}

    with st.form(key=f"mcp_form_{tool['name']}"):
        for name, parameter in properties.items():
            parameter = parameter if isinstance(parameter, dict) else {}
            label = parameter.get("title") or name.replace("_", " ").capitalize()
            if name in required:
                label += " (required)"

            choices = parameter.get("enum")
            value_type = parameter.get("type", "string")
            if isinstance(value_type, list):
                value_type = next(
                    (item for item in value_type if item != "null"),
                    "string",
                )

            default = parameter.get("default")
            if name == "city_name":
                default = selected_city
                label += " — blank uses selected city"

            key = f"mcp_{tool['name']}_{name}"
            if choices:
                value = st.selectbox(
                    label,
                    choices,
                    index=choices.index(default) if default in choices else 0,
                    key=key,
                )
            elif value_type == "boolean":
                value = st.checkbox(
                    label,
                    value=bool(default) if default is not None else False,
                    key=key,
                )
            elif value_type in ("integer", "number"):
                is_integer = value_type == "integer"
                value = st.number_input(
                    label,
                    min_value=parameter.get("minimum"),
                    max_value=parameter.get("maximum"),
                    value=default if default is not None else 0,
                    step=1 if is_integer else 0.1,
                    format="%d" if is_integer else "%g",
                    key=key,
                )
                if is_integer:
                    value = int(value)
            elif value_type in ("object", "array"):
                initial_value = default if default is not None else (
                    {} if value_type == "object" else []
                )
                complex_values[name] = st.text_area(
                    label,
                    value=json.dumps(initial_value, ensure_ascii=False, indent=2),
                    key=key,
                    help="Enter valid JSON.",
                )
            else:
                value = st.text_input(
                    label,
                    value=str(default) if default is not None else "",
                    key=key,
                )

            if name not in complex_values:
                if name == "city_name" and not str(value).strip():
                    value = selected_city
                if isinstance(value, str) and not value.strip():
                    if name in required:
                        validation_errors.append(f"{label} is required.")
                    continue
                arguments[name] = value

        submitted = st.form_submit_button(
            "Execute tool",
            type="primary",
            icon=":material/play_arrow:",
        )

    if not submitted:
        return None, []

    for name, raw_value in complex_values.items():
        try:
            arguments[name] = json.loads(raw_value)
        except json.JSONDecodeError as error:
            validation_errors.append(
                f"{name.replace('_', ' ').capitalize()} must be valid JSON: {error.msg}."
            )

    return arguments, validation_errors


def get_mcp_result_payload(result):
    if not isinstance(result, dict):
        return result, None

    if not result.get("success", True) or result.get("is_error"):
        return None, result.get("error") or result.get("content") or "Tool execution failed."

    payload = result.get("structuredContent")
    if payload is None:
        payload = result.get("content")

    if isinstance(payload, list) and len(payload) == 1:
        payload = payload[0]

    if isinstance(payload, dict) and payload.get("success") is False:
        return None, payload.get("error") or "The MCP tool reported an error."

    return payload, None


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="brand-icon">🌦️</div>
            <div>
                <h2>MyOwnWeather</h2>
                <p>Smart Weather Platform</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.markdown("📍 Search Location")

    city_input = st.text_input(
        "City name",
        value=st.session_state.selected_city,
        placeholder="Delhi, Mumbai, London",
        label_visibility="collapsed"
    )

    if st.button("🔍 Get Weather", use_container_width=True):
        if load_weather(city_input):
            st.rerun()

    st.divider()

    st.markdown("⚙️ Backend Status")

    if st.button("Check Backend", use_container_width=True):
        health = api_get("/api/health")

        if health:
            st.success("Backend connected")
            st.json(health)

    st.divider()

    st.markdown("🕘 Weather History")

    if st.button("Refresh History", use_container_width=True):
        load_history()

    for record in st.session_state.history_data:

        record_id = record.get("id")
        city_name = record.get("city_name", "Unknown")
        temperature = record.get("temperature", "N/A")
        recorded_at = record.get("recorded_at", "")

        with st.expander(
            f"🌡️ {city_name} - {temperature}°C"
        ):

            st.caption(recorded_at)

            st.write(
                f"Condition: "
                f"{record.get('weather_condition', 'N/A')}"
            )

            if st.button(
                "🗑️ Delete Record",
                key=f"delete_history_{record_id}"
            ):
                delete_history(record_id)


# ==========================================
# MAIN HEADER
# ==========================================

st.markdown(
    """
    <div class="main-header">
        <div class="header-label">
            PERSONAL WEATHER INTELLIGENCE
        </div>
        <h1>Weather Dashboard</h1>
        <p>
            Weather forecasts, live insights and AI assistance
        </p>
    </div>
    """,
    unsafe_allow_html=True
)


# ==========================================
# INITIAL WEATHER LOAD
# ==========================================

if st.session_state.weather_result is None:
    load_weather(st.session_state.selected_city)


# ==========================================
# WEATHER DASHBOARD
# ==========================================

weather = get_weather_data()
city = get_city_data()
current = get_current_data()

if weather and current:

    city_name = city.get(
        "name",
        st.session_state.selected_city
    )

    country = city.get("country", "")
    admin1 = city.get("admin1", "")

    location_parts = [
        part for part in [admin1, country] if part
    ]

    location_text = ", ".join(location_parts)

    temperature = current.get("temperature_2m")
    feels_like = current.get("apparent_temperature")
    humidity = current.get("relative_humidity_2m")
    wind_speed = current.get("wind_speed_10m")
    pressure = current.get("pressure_msl")
    cloud_cover = current.get("cloud_cover")
    precipitation = current.get("precipitation")

    condition = current.get(
        "description",
        "Weather information"
    )

    # ======================================
    # MAIN WEATHER CARD
    # ======================================

    st.markdown(
        f"""
        <div class="weather-card">
            <div class="weather-location">
                📍 {city_name}, {location_text}
            </div>
            <div class="weather-condition">
                {condition}
            </div>
            <div class="temperature">
                {format_value(temperature, "°C")}
            </div>
            <div class="feels-like">
                Feels like {format_value(feels_like, "°C")}
            </div>
            <div class="weather-note">
                Data source: Open-Meteo forecast model
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ======================================
    # WEATHER METRICS
    # ======================================

    st.markdown("🌡️ Current Weather Details")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Humidity",
        format_value(humidity, "%")
    )

    col2.metric(
        "Wind Speed",
        format_value(wind_speed, " km/h")
    )

    col3.metric(
        "Pressure",
        format_value(pressure, " hPa")
    )

    col4.metric(
        "Cloud Cover",
        format_value(cloud_cover, "%")
    )

    col5, col6 = st.columns(2)

    col5.metric(
        "Precipitation",
        format_value(precipitation, " mm")
    )

    col6.metric(
        "Weather Code",
        format_value(current.get("weather_code"))
    )

    st.divider()

    # ======================================
    # HOURLY FORECAST
    # ======================================

    st.markdown("⏰ Hourly Forecast")

    hourly = weather.get("hourly", {})

    hourly_times = hourly.get("time", [])
    hourly_temperatures = hourly.get("temperature_2m", [])

    if hourly_times and hourly_temperatures:

        hourly_df = pd.DataFrame({
            "Time": pd.to_datetime(hourly_times),
            "Temperature (°C)": hourly_temperatures
        })

        hourly_df = (
            hourly_df.head(24)
            .set_index("Time")
        )

        st.line_chart(
            hourly_df,
            use_container_width=True
        )

    else:
        st.info("Hourly forecast available nahi hai.")

    st.divider()

    # ======================================
    # DAILY FORECAST
    # ======================================

    st.markdown("📅 7-Day Forecast")

    daily = weather.get("daily", {})

    daily_times = daily.get("time", [])
    max_temps = daily.get("temperature_2m_max", [])
    min_temps = daily.get("temperature_2m_min", [])
    daily_conditions = daily.get("description", [])
    rain_values = daily.get("precipitation_sum", [])
    wind_values = daily.get("wind_speed_10m_max", [])

    forecast_rows = []

    for index, day in enumerate(daily_times):

        forecast_rows.append({
            "Date": day,

            "Condition": (
                daily_conditions[index]
                if index < len(daily_conditions)
                else "N/A"
            ),

            "Max Temp (°C)": (
                max_temps[index]
                if index < len(max_temps)
                else None
            ),

            "Min Temp (°C)": (
                min_temps[index]
                if index < len(min_temps)
                else None
            ),

            "Rain (mm)": (
                rain_values[index]
                if index < len(rain_values)
                else None
            ),

            "Max Wind (km/h)": (
                wind_values[index]
                if index < len(wind_values)
                else None
            )
        })

    if forecast_rows:

        forecast_df = pd.DataFrame(forecast_rows)

        st.dataframe(
            forecast_df,
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Daily forecast available nahi hai.")

    st.divider()

    # ======================================
    # AI WEATHER ASSISTANT
    # ======================================

    st.markdown("🤖 AI Weather Assistant")

    st.caption(
        "Weather ke baare mein natural language mein question pucho."
    )

    for message in st.session_state.chat_messages:

        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    user_question = st.chat_input(
        "Example: Kya aaj baarish hone wali hai?"
    )

    if user_question:

        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):

            with st.spinner("AI answer prepare kar raha hai..."):

                ai_result = api_post(
                    "/api/assistant/chat",
                    {
                        "question": user_question,
                        "weather_data": st.session_state.weather_result
                    }
                )

                if ai_result:

                    answer = (
                        ai_result.get("answer")
                        or ai_result.get("response")
                        or ai_result.get("message")
                        or str(ai_result)
                    )

                    st.markdown(answer)

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": answer
                    })

                else:

                    error_message = (
                        "AI response nahi mil paya. "
                        "Ollama server aur model check karo."
                    )

                    st.error(error_message)

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": error_message
                    })

    if st.button("Clear AI Chat"):
        st.session_state.chat_messages = []
        st.rerun()

    st.divider()

    # ======================================
    # MCP WEATHER TOOLS
    # ======================================

    with st.container(border=True, key="mcp-tools-panel"):
        st.subheader("MCP weather tools", divider="rainbow")
        st.caption(
            "Search cities, check forecasts, compare providers, "
            "or review saved weather searches."
        )

        if st.button(
            "Refresh tools",
            icon=":material/refresh:",
            key="refresh_mcp_tools",
        ):
            st.session_state.mcp_tools_loaded = False

        if not st.session_state.mcp_tools_loaded:
            tools_response = api_get("/api/mcp/tools")
            st.session_state.mcp_tools_loaded = True

            if isinstance(tools_response, list):
                st.session_state.mcp_tools = tools_response
            elif isinstance(tools_response, dict):
                st.session_state.mcp_tools = tools_response.get("tools", [])
                if not tools_response.get("connected", tools_response.get("success", True)):
                    st.error(
                        tools_response.get("error")
                        or "MCP server is unavailable. Check the backend and try refreshing."
                    )

        tools_list = st.session_state.mcp_tools
        tool_names = [
            tool.get("name")
            for tool in tools_list
            if isinstance(tool, dict) and tool.get("name")
        ]
        tools_by_name = {
            tool["name"]: tool
            for tool in tools_list
            if isinstance(tool, dict) and tool.get("name")
        }

        if tool_names:
            selected_tool_name = st.selectbox(
                "Choose a tool",
                tool_names,
                format_func=lambda name: name.replace("_", " "),
                key="selected_mcp_tool",
            )
            selected_tool = tools_by_name[selected_tool_name]
            description = selected_tool.get("description", "").strip()
            if description:
                st.caption(description)

            arguments, validation_errors = build_mcp_arguments(
                selected_tool,
                st.session_state.selected_city,
            )

            if arguments is not None:
                if validation_errors:
                    for message in validation_errors:
                        st.error(message)
                else:
                    with st.spinner("Executing MCP tool..."):
                        mcp_result = api_post(
                            "/api/mcp/call",
                            {
                                "tool_name": selected_tool_name,
                                "arguments": arguments,
                                "selected_city": st.session_state.selected_city,
                            },
                        )

                    if mcp_result is not None:
                        result_payload, result_error = get_mcp_result_payload(mcp_result)
                        if result_error:
                            st.error(f"Tool failed: {result_error}")
                        else:
                            st.success("Tool completed.")
                            with st.expander("Execution result", expanded=True):
                                st.json(result_payload)
        else:
            st.info(
                "No MCP tools are available. Confirm that the backend and MCP "
                "server are running, then refresh."
            )

    st.divider()

    # ======================================
    # FOOTER
    # ======================================

    st.markdown(
        """
        <div class="footer">
            MyOwnWeather • Built with Streamlit, FastAPI,
            Open-Meteo, Ollama, MCP and SQLite
        </div>
        """,
        unsafe_allow_html=True
    )

else:

    st.warning(
        "Weather data load nahi hua. "
        "City name check karo aur backend server verify karo."
    )

    if st.button("Retry Weather"):
        if load_weather(st.session_state.selected_city):
            st.rerun()
