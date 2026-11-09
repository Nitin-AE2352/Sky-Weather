
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail =
      typeof payload === "object" && payload !== null
        ? payload.detail || payload.message || payload.error
        : payload;

    const error = new Error(
      typeof detail === "string"
        ? detail
        : `Request failed with status ${response.status}`
    );

    error.status = response.status;
    error.detail = detail;
    error.payload = payload;

    throw error;
  }

  return payload;
}

function queryString(values = {}) {
  const params = new URLSearchParams();

  Object.entries(values).forEach(([key, value]) => {
    if (
      value !== undefined &&
      value !== null &&
      String(value).trim() !== ""
    ) {
      params.set(key, String(value));
    }
  });

  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  health() {
    return request("/api/health");
  },

  searchCities(city) {
    return request(`/api/cities/search${queryString({ city })}`);
  },

  weather(city, location = null) {
    return request(
      `/api/weather${queryString({
        city,
        latitude: location?.latitude,
        longitude: location?.longitude,
        timezone: location?.timezone,
        country: location?.country,
        country_code: location?.country_code,
        admin1: location?.admin1,
        admin2: location?.admin2,
        id: location?.id,
        population: location?.population,
      })}`
    );
  },

  currentWeather(city) {
    return request(`/api/weather/current${queryString({ city })}`);
  },

  forecast(city) {
    return request(`/api/weather/forecast${queryString({ city })}`);
  },

  compare(city, location = null) {
    return request(
      `/api/weather/compare${queryString({
        city,
        latitude: location?.latitude,
        longitude: location?.longitude,
        timezone: location?.timezone,
        country: location?.country,
        country_code: location?.country_code,
        admin1: location?.admin1,
        admin2: location?.admin2,
        id: location?.id,
        population: location?.population,
      })}`
    );
  },

  assistant(question, weatherData, chatHistory = []) {
    return request("/api/assistant/chat", {
      method: "POST",
      body: JSON.stringify({
        question,
        weather_data: weatherData,
        chat_history: chatHistory,
      }),
    });
  },

  assistantStatus() {
    return request("/api/assistant/status");
  },

  history(limit = 50, city = "") {
    return request(
      `/api/weather/history${queryString({ limit, city })}`
    );
  },

  deleteHistory(recordId) {
    return request(`/api/weather/history/${encodeURIComponent(recordId)}`, {
      method: "DELETE",
    });
  },

  mcpTools() {
    return request("/api/mcp/tools");
  },

  mcpCall(toolName, argumentsObject = {}, selectedCity = "") {
    return request("/api/mcp/call", {
      method: "POST",
      body: JSON.stringify({
        tool_name: toolName,
        arguments: argumentsObject,
        selected_city: selectedCity,
      }),
    });
  },
};

export default api;
