import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Activity,
  Bot,
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudRain,
  CloudSnow,
  CloudSun,
  Snowflake,
  Zap,
  Compass,
  Droplets,
  Gauge,
  History,
  MapPin,
  Menu,
  MessageCircle,
  RefreshCw,
  Search,
  Send,
  Sun,
  Thermometer,
  Trash2,
  Wind,
  X,
  Eye,
  Sunrise,
  Sunset,
  CalendarDays,
  BarChart3,
  Settings,
  AlertCircle,
  CheckCircle2,
  LoaderCircle,
  Bell,
  Star,
  SunMedium,
  Umbrella,
} from "lucide-react";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "./services/api";
import "./App.css";

const DEFAULT_CITY = "Noida";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: Cloud },
  { id: "forecast", label: "Forecast", icon: CalendarDays },
  { id: "compare", label: "Compare", icon: BarChart3 },
  { id: "assistant", label: "AI Assistant", icon: Bot },
  { id: "history", label: "History", icon: History },
];

function getWeatherIcon(code, isDay = true) {
  if (code === 0) return isDay ? Sun : Cloud;

  if ([1, 2].includes(code)) return CloudSun;
  if (code === 3) return Cloud;
  if ([45, 48].includes(code)) return CloudFog;

  if ([51, 53, 55, 56, 57].includes(code)) {
    return CloudDrizzle;
  }

  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) {
    return CloudRain;
  }

  if ([71, 73, 75, 77, 85, 86].includes(code)) {
    return CloudSnow;
  }

  if ([95, 96, 99].includes(code)) {
    return CloudLightning;
  }

  return Cloud;
}

function getWeatherIconTone(code) {
  if (code === 0) return "sunny";
  if ([1, 2].includes(code)) return "partly";
  if (code === 3) return "cloudy";
  if ([45, 48].includes(code)) return "foggy";
  if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82].includes(code)) {
    return "rainy";
  }
  if ([71, 73, 75, 77, 85, 86].includes(code)) return "snowy";
  if ([95, 96, 99].includes(code)) return "stormy";

  return "cloudy";
}

function WeatherConditionIcon({ code, size = 24 }) {
  const tone = getWeatherIconTone(Number(code));
  const cloudSize = Math.round(size * 0.78);
  const detailSize = Math.round(size * 0.42);

  return (
    <span
      className={`weather-glyph weather-glyph-${tone}`}
      style={{ "--weather-glyph-size": `${size}px` }}
      aria-hidden="true"
    >
      {tone === "sunny" && <Sun className="glyph-sun" size={size} />}
      {tone === "partly" && (
        <>
          <Sun className="glyph-sun" size={detailSize} />
          <Cloud className="glyph-cloud" size={cloudSize} />
        </>
      )}
      {(tone === "cloudy" || tone === "foggy") && (
        <Cloud className="glyph-cloud" size={size} />
      )}
      {tone === "rainy" && (
        <>
          <Cloud className="glyph-cloud" size={cloudSize} />
          <Droplets className="glyph-rain" size={detailSize} />
        </>
      )}
      {tone === "snowy" && (
        <>
          <Cloud className="glyph-cloud" size={cloudSize} />
          <Snowflake className="glyph-snow" size={detailSize} />
        </>
      )}
      {tone === "stormy" && (
        <>
          <Cloud className="glyph-cloud" size={cloudSize} />
          <Zap className="glyph-lightning" size={detailSize} />
        </>
      )}
      {tone === "foggy" && <span className="glyph-fog-lines" />}
    </span>
  );
}

function getWeatherDescription(code) {
  const descriptions = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snowfall",
    73: "Moderate snowfall",
    75: "Heavy snowfall",
    77: "Snow grains",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm",
  };

  return descriptions[code] || "Weather information";
}

function formatHour(value) {
  if (!value) return "--";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value).slice(-5);
  }

  return date.toLocaleTimeString("en-IN", {
    hour: "numeric",
    hour12: true,
  });
}

function formatDate(value, options = {}) {
  if (!value) return "--";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  const isCalendarDate = /^\d{4}-\d{2}-\d{2}$/.test(value);

  return date.toLocaleDateString("en-IN", {
    ...options,
    ...(isCalendarDate ? { timeZone: "UTC" } : {}),
  });
}

function getCurrentWeather(bundle) {
  return bundle?.weather?.current || bundle?.current || {};
}

function getHourlyWeather(bundle) {
  return bundle?.weather?.hourly || bundle?.hourly || {};
}

function getDailyWeather(bundle) {
  return bundle?.weather?.daily || bundle?.daily || {};
}

function getAirQuality(bundle) {
  return (
    bundle?.weather?.air_quality?.current ||
    bundle?.air_quality?.current ||
    bundle?.air_quality ||
    {}
  );
}

function getAirQualityMetadata(bundle) {
  return bundle?.weather?.air_quality || bundle?.air_quality || {};
}

function getNumber(value, fallback = "--") {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return fallback;
  }

  const number = Number(value);

  return Number.isFinite(number) ? number : fallback;
}

function getDecimal(value, digits = 1, fallback = "--") {
  const number = Number(value);

  return Number.isFinite(number)
    ? number.toFixed(digits)
    : fallback;
}

function getTemperature(value, unit) {
  const number = Number(value);

  if (!Number.isFinite(number)) return "--";

  return unit === "F"
    ? Math.round((number * 9) / 5 + 32)
    : Math.round(number);
}

function getAqiDetails(airQuality) {
  const usAqi = Number(airQuality.us_aqi);
  const europeanAqi = Number(airQuality.european_aqi);
  const hasUsAqi = Number.isFinite(usAqi);
  const hasEuropeanAqi = Number.isFinite(europeanAqi);

  if (!hasUsAqi && !hasEuropeanAqi) {
    return {
      value: null,
      scale: "AQI",
      label: "Unavailable",
      className: "neutral",
      needsCaution: false,
    };
  }

  const value = hasUsAqi ? usAqi : europeanAqi;
  const scale = hasUsAqi ? "US AQI" : "European AQI";
  const bands = hasUsAqi
    ? [
        [50, "Good", "good"],
        [100, "Moderate", "moderate"],
        [150, "Unhealthy for sensitive groups", "sensitive"],
        [200, "Unhealthy", "unhealthy"],
        [300, "Very unhealthy", "danger"],
        [Infinity, "Hazardous", "danger"],
      ]
    : [
        [20, "Good", "good"],
        [40, "Fair", "moderate"],
        [60, "Moderate", "sensitive"],
        [80, "Poor", "unhealthy"],
        [100, "Very poor", "danger"],
        [Infinity, "Extremely poor", "danger"],
      ];
  const [, label, className] = bands.find(
    ([upperBound]) => value <= upperBound
  );

  return {
    value,
    scale,
    label,
    className,
    needsCaution: hasUsAqi ? value > 100 : value > 60,
  };
}

function getMcpArguments(input, tool, selectedCity) {
  const rawInput = input.trim();
  let argumentsObject = {};
  const schema = tool.inputSchema || tool.input_schema || {};
  const properties = schema.properties || {};
  const cityArgumentNames = ["city_name", "city", "location"];
  const cityArgumentName = cityArgumentNames.find(
    (name) => properties[name]
  );

  if (rawInput) {
    try {
      argumentsObject = JSON.parse(rawInput);
    } catch (error) {
      const looksLikePlainCity =
        cityArgumentName &&
        !/[{}\[\]:]/.test(rawInput) &&
        !rawInput.startsWith('"');

      if (looksLikePlainCity) {
        argumentsObject[cityArgumentName] = rawInput;
      } else {
        const positionMatch = error.message.match(/position (\d+)/);
        const position = positionMatch
          ? Number(positionMatch[1])
          : null;
        const location = Number.isFinite(position)
          ? ` near character ${position + 1}`
          : "";
        const example = cityArgumentName
          ? `{"${cityArgumentName}":"${selectedCity}"}`
          : "{}";
        throw new Error(
          `Arguments JSON is invalid${location}. Use {} or a valid JSON object, for example ${example}.`
        );
      }
    }

    if (
      typeof argumentsObject === "string" &&
      cityArgumentName
    ) {
      argumentsObject = { [cityArgumentName]: argumentsObject };
    }

    if (
      !argumentsObject ||
      typeof argumentsObject !== "object" ||
      Array.isArray(argumentsObject)
    ) {
      throw new Error(
        'MCP arguments must be a JSON object, such as {"city_name":"Noida"}.'
      );
    }
  }

  if (cityArgumentName && !String(argumentsObject[cityArgumentName] ?? "").trim()) {
    argumentsObject[cityArgumentName] = selectedCity;
  }

  return argumentsObject;
}

function getWeatherAlerts(current, aqiDetails) {
  const alerts = [];
  const temperature = Number(current.temperature_2m);
  const wind = Number(current.wind_gusts_10m ?? current.wind_speed_10m);
  const rain = Number(current.precipitation);

  if (Number.isFinite(temperature) && temperature >= 38) {
    alerts.push({
      tone: "orange",
      title: "High temperature",
      message: "Stay hydrated and avoid prolonged midday exposure.",
    });
  }

  if (Number.isFinite(wind) && wind >= 45) {
    alerts.push({
      tone: "pink",
      title: "Strong wind",
      message: `Wind gusts may reach ${Math.round(wind)} km/h.`,
    });
  }

  if (Number.isFinite(rain) && rain >= 5) {
    alerts.push({
      tone: "blue",
      title: "Rain expected",
      message: "Consider carrying an umbrella before heading out.",
    });
  }

  if (aqiDetails.needsCaution) {
    alerts.push({
      tone: "yellow",
      title: "Air quality notice",
      message: "Sensitive groups should reduce prolonged outdoor activity.",
    });
  }

  return alerts;
}

function getHistoryId(item) {
  return item.id ?? item.record_id ?? item.history_id;
}

function getHistoryCity(item) {
  return item.city || item.city_name || "Unknown city";
}

function getHistoryTemperature(item) {
  return (
    item.temperature ??
    item.temperature_2m ??
    item.temp ??
    "--"
  );
}

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string") {
    return detail;
  }

  return (
    error?.message ||
    "Something went wrong. Please try again."
  );
}

function getSuggestionName(suggestion) {
  if (typeof suggestion === "string") {
    return suggestion;
  }

  return (
    suggestion?.name ||
    suggestion?.city ||
    suggestion?.label ||
    suggestion?.display_name ||
    ""
  );
}

function getSuggestionDetails(suggestion) {
  if (!suggestion || typeof suggestion === "string") {
    return "";
  }

  return [
    suggestion.admin1,
    suggestion.country,
  ]
    .filter(Boolean)
    .filter((value, index, values) => values.indexOf(value) === index)
    .join(", ");
}

function getCityFromWeatherQuestion(question) {
  const ignoredWords = new Set([
    "a", "about", "aj", "am", "an", "and", "at", "aaj", "abhi",
    "batao", "btao", "can", "condition", "conditions", "could",
    "current", "forecast", "for", "hai", "hain", "hawa", "how",
    "hows", "humidity", "in", "is", "it", "ka", "kaisa", "kaisi",
    "kaise", "kal", "ke", "ki", "ky", "kya", "like", "mausam",
    "me", "mein", "mujhe", "outside", "please", "rain", "raining",
    "raha", "rahe", "rahi", "right", "tell", "temperature", "the",
    "there", "today", "tomorrow", "weather", "what", "whats", "will",
    "wind", "with", "you", "कैसा", "कैसी", "कैसे", "क्या", "आज",
    "अभी", "का", "की", "के", "में", "मौसम", "बताओ", "बताइए",
    "है", "होगा", "होगी", "कल",
  ]);
  const tokens = question
    .replace(/[^\p{L}\p{M}\p{N}\s'-]/gu, " ")
    .split(/\s+/)
    .filter((token) => token && !ignoredWords.has(token.toLocaleLowerCase()));

  if (tokens.length === 0 || tokens.length > 5) {
    return "";
  }

  return tokens.join(" ").trim();
}

function StatCard({
  icon: Icon,
  label,
  value,
  unit,
  description,
  tone = "blue",
}) {
  return (
    <div className={`stat-card ${tone}`}>
      <div className="stat-card-top">
        <span className="stat-icon">
          <Icon size={19} />
        </span>

        <span className="stat-label">{label}</span>
      </div>

      <div className="stat-value">
        {value}
        {unit && <span>{unit}</span>}
      </div>

      {description && (
        <p className="stat-description">
          {description}
        </p>
      )}
    </div>
  );
}

function EmptyState({
  icon: Icon = Cloud,
  title,
  message,
}) {
  return (
    <div className="empty-state">
      <Icon size={35} />
      <h3>{title}</h3>
      <p>{message}</p>
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const [city, setCity] = useState(DEFAULT_CITY);
  const [cityContext, setCityContext] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [weatherBundle, setWeatherBundle] = useState(null);

  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [backendStatus, setBackendStatus] = useState("checking");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [temperatureUnit, setTemperatureUnit] = useState(
    () => localStorage.getItem("skycast-temperature-unit") || "C"
  );
  const [autoRefresh, setAutoRefresh] = useState(
    () => localStorage.getItem("skycast-auto-refresh") === "true"
  );
  const [favoriteCities, setFavoriteCities] = useState(
    () => JSON.parse(localStorage.getItem("skycast-favorite-cities") || "[]")
  );

  const [citySuggestions, setCitySuggestions] = useState([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);
  const [citySearchError, setCitySearchError] = useState("");
  const [selectedForecastDate, setSelectedForecastDate] = useState("");

  // Prevents older city-search responses from replacing newer results.
  const suggestionRequestId = useRef(0);
  const selectedLocationRef = useRef(null);

  const [comparison, setComparison] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [comparisonError, setComparisonError] = useState("");

  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [assistantStatus, setAssistantStatus] = useState(null);

  const [assistantMessages, setAssistantMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your SkyCast AI assistant. Ask me about the weather, temperature, rain, wind or travel conditions.",
    },
  ]);

  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantWorkingMessage, setAssistantWorkingMessage] = useState("");

  const [mcpTools, setMcpTools] = useState([]);
  const [mcpLoading, setMcpLoading] = useState(false);

  // MCP execution state.
  const [mcpExecutingTool, setMcpExecutingTool] = useState("");
  const [mcpArgumentsInput, setMcpArgumentsInput] = useState("");
  const [mcpResult, setMcpResult] = useState(null);
  const [mcpError, setMcpError] = useState("");

  const current = useMemo(
    () => getCurrentWeather(weatherBundle),
    [weatherBundle]
  );

  const hourly = useMemo(
    () => getHourlyWeather(weatherBundle),
    [weatherBundle]
  );

  const daily = useMemo(
    () => getDailyWeather(weatherBundle),
    [weatherBundle]
  );

  const airQuality = useMemo(
    () => getAirQuality(weatherBundle),
    [weatherBundle]
  );
  const airQualityMetadata = useMemo(
    () => getAirQualityMetadata(weatherBundle),
    [weatherBundle]
  );

  const temperature = getNumber(current.temperature_2m);
  const feelsLike = getNumber(current.apparent_temperature);
  const humidity = getNumber(current.relative_humidity_2m);
  const windSpeed = getNumber(current.wind_speed_10m);
  const windDirection = getNumber(current.wind_direction_10m);
  const pressure = getNumber(current.pressure_msl);
  const visibility = getNumber(current.visibility);

  const weatherCode = Number(current.weather_code ?? 0);
  const isDay = current.is_day !== 0;

  const WeatherIcon = getWeatherIcon(weatherCode, isDay);
  const weatherIconTone = getWeatherIconTone(weatherCode);

  const aqiDetails = useMemo(
    () => getAqiDetails(airQuality),
    [airQuality]
  );
  const weatherAlerts = useMemo(
    () => getWeatherAlerts(current, aqiDetails),
    [current, aqiDetails]
  );
  const sunrise = daily.sunrise?.[0];
  const sunset = daily.sunset?.[0];
  const uvIndex = daily.uv_index_max?.[0] ?? current.uv_index;
  const rainChance = daily.precipitation_probability_max?.[0];
  const cloudCover = current.cloud_cover;

  const hourlyChartData = useMemo(() => {
    const times = hourly.time || [];
    const temperatures = hourly.temperature_2m || [];

    return times
      .slice(0, 24)
      .map((time, index) => ({
        time: formatHour(time),
        temperature: getTemperature(
          temperatures[index],
          temperatureUnit
        ),
      }))
      .filter((item) =>
        Number.isFinite(Number(item.temperature))
      );
  }, [hourly, temperatureUnit]);

  const dailyForecast = useMemo(() => {
    const times = daily.time || [];
    const maxTemps = daily.temperature_2m_max || [];
    const minTemps = daily.temperature_2m_min || [];
    const codes = daily.weather_code || [];
    const rain = daily.precipitation_probability_max || [];

    return times.map((time, index) => ({
      date: time,
      max: maxTemps[index],
      min: minTemps[index],
      code: codes[index],
      rain: rain[index],
    }));
  }, [daily]);

  const forecastHighlights = useMemo(() => {
    const warmestDay = dailyForecast
      .filter((item) => item.max !== null && item.max !== undefined && Number.isFinite(Number(item.max)))
      .reduce(
        (warmest, item) =>
          !warmest || Number(item.max) > Number(warmest.max)
            ? item
            : warmest,
        null
      );
    const coolestDay = dailyForecast
      .filter((item) => item.min !== null && item.min !== undefined && Number.isFinite(Number(item.min)))
      .reduce(
        (coolest, item) =>
          !coolest || Number(item.min) < Number(coolest.min)
            ? item
            : coolest,
        null
      );
    const rainiestDay = dailyForecast
      .filter((item) => item.rain !== null && item.rain !== undefined && Number.isFinite(Number(item.rain)))
      .reduce(
        (rainiest, item) =>
          !rainiest || Number(item.rain) > Number(rainiest.rain)
            ? item
            : rainiest,
        null
      );

    return { warmestDay, coolestDay, rainiestDay };
  }, [dailyForecast]);
  const selectedForecast = dailyForecast.find(
    (item) => item.date === selectedForecastDate
  );

  const displayTemperature = (value) =>
    getTemperature(value, temperatureUnit);

  const toggleFavoriteCity = () => {
    const normalized = city.trim();
    if (!normalized) return;

    setFavoriteCities((previous) => {
      const next = previous.includes(normalized)
        ? previous.filter((item) => item !== normalized)
        : [...previous, normalized].slice(-8);
      localStorage.setItem(
        "skycast-favorite-cities",
        JSON.stringify(next)
      );
      return next;
    });
  };

  // --------------------------------------------------
  // WEATHER LOADING
  // --------------------------------------------------

  const loadWeather = useCallback(
    async (cityName, showRefresh = false) => {
      const cleanCity = (
        typeof cityName === "string"
          ? cityName
          : getSuggestionName(cityName)
      ).trim();

      if (!cleanCity) {
        setError("Please enter a city name.");
        return;
      }

      const selectedLocation =
        cityName &&
        typeof cityName === "object" &&
        cityName.latitude !== undefined &&
        cityName.longitude !== undefined
          ? cityName
          : null;
      const savedLocation = selectedLocationRef.current;
      const location =
        selectedLocation ||
        (savedLocation &&
        getSuggestionName(savedLocation).toLocaleLowerCase() ===
          cleanCity.toLocaleLowerCase()
          ? savedLocation
          : null);

      if (showRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      try {
        const data = await api.weather(cleanCity, location);

        setWeatherBundle(data);
        selectedLocationRef.current = data?.city || location;
        setCityContext(getSuggestionDetails(data?.city));
        setSelectedForecastDate("");

        setCity(
          data?.city?.name ||
          data?.city ||
          cleanCity
        );

        setSearchInput("");
        setCitySuggestions([]);
        setCitySearchError("");
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    []
  );

  // --------------------------------------------------
  // BACKEND STATUS
  // --------------------------------------------------

  const checkBackend = useCallback(async () => {
    try {
      await api.health();
      setBackendStatus("online");
    } catch {
      setBackendStatus("offline");
    }
  }, []);

  // --------------------------------------------------
  // WEATHER HISTORY
  // --------------------------------------------------

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);

    try {
      const data = await api.history(50);

      const records = Array.isArray(data)
        ? data
        : data?.history ||
          data?.records ||
          data?.data ||
          [];

      setHistory(records);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  const handleDeleteHistory = async (id) => {
    if (id === null || id === undefined) {
      return;
    }

    try {
      await api.deleteHistory(id);

      setHistory((previous) =>
        previous.filter(
          (item) => getHistoryId(item) !== id
        )
      );
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  // --------------------------------------------------
  // WEATHER COMPARISON
  // --------------------------------------------------

  const loadComparison = useCallback(async () => {
    const selectedLocation = selectedLocationRef.current;
    const location =
      selectedLocation &&
      getSuggestionName(selectedLocation).toLocaleLowerCase() ===
        city.toLocaleLowerCase()
        ? selectedLocation
        : null;

    setComparisonLoading(true);
    setComparison(null);
    setComparisonError("");

    try {
      const data = await api.compare(city, location);
      setComparison(data);
    } catch (err) {
      setComparisonError(getErrorMessage(err));
    } finally {
      setComparisonLoading(false);
    }
  }, [city]);

  // --------------------------------------------------
  // AI ASSISTANT STATUS
  // --------------------------------------------------

  const loadAssistantStatus = useCallback(async () => {
    try {
      const data = await api.assistantStatus();
      setAssistantStatus(data);
    } catch {
      setAssistantStatus(null);
    }
  }, []);

  // --------------------------------------------------
  // MCP TOOL DISCOVERY
  // --------------------------------------------------

  const loadMcpTools = useCallback(async () => {
    setMcpLoading(true);
    setMcpError("");

    try {
      const data = await api.mcpTools();

      const tools = Array.isArray(data)
        ? data
        : data?.tools ||
          data?.data ||
          [];

      setMcpTools(tools);
    } catch (err) {
      setMcpTools([]);
      setMcpError(getErrorMessage(err));
    } finally {
      setMcpLoading(false);
    }
  }, []);

  // --------------------------------------------------
  // MCP TOOL EXECUTION
  // --------------------------------------------------

  const runMcpTool = async (tool) => {
    const toolName = tool?.name;

    if (!toolName) {
      setMcpError("Invalid MCP tool name.");
      return;
    }

    if (mcpExecutingTool) {
      return;
    }

    setMcpExecutingTool(toolName);
    setMcpResult(null);
    setMcpError("");

    try {
      const argumentsObject = getMcpArguments(
        mcpArgumentsInput,
        tool,
        city
      );

      const response = await api.mcpCall(
        toolName,
        argumentsObject,
        city
      );

      setMcpResult({
        toolName,
        arguments: argumentsObject,
        response,
      });
    } catch (err) {
      setMcpError(getErrorMessage(err));
    } finally {
      setMcpExecutingTool("");
    }
  };

  // --------------------------------------------------
  // INITIAL DATA LOADING
  // --------------------------------------------------

  useEffect(() => {
    checkBackend();
    loadWeather(DEFAULT_CITY);
    loadAssistantStatus();
  }, [
    checkBackend,
    loadWeather,
    loadAssistantStatus,
  ]);

  useEffect(() => {
    localStorage.setItem(
      "skycast-temperature-unit",
      temperatureUnit
    );
    localStorage.setItem(
      "skycast-auto-refresh",
      String(autoRefresh)
    );
  }, [temperatureUnit, autoRefresh]);

  useEffect(() => {
    if (!autoRefresh || !city) return undefined;

    const timer = window.setInterval(() => {
      loadWeather(city, true);
    }, 15 * 60 * 1000);

    return () => window.clearInterval(timer);
  }, [autoRefresh, city, loadWeather]);

  // --------------------------------------------------
  // PAGE BASED DATA LOADING
  // --------------------------------------------------

  useEffect(() => {
    if (activePage === "history") {
      loadHistory();
    }

    if (activePage === "compare") {
      loadComparison();
    }

    if (activePage === "assistant") {
      loadMcpTools();
    }
  }, [
    activePage,
    loadHistory,
    loadComparison,
    loadMcpTools,
  ]);

  // --------------------------------------------------
  // CITY SEARCH
  // --------------------------------------------------

  const handleSearch = async (event) => {
    event.preventDefault();

    const value = searchInput.trim();

    if (!value || loading) return;

    setCitySearchError("");

    try {
      const data = await api.searchCities(value);
      const suggestions = Array.isArray(data)
        ? data
        : data?.cities ||
          data?.results ||
          data?.suggestions ||
          [];

      if (suggestions.length === 0) {
        setCitySearchError(`No cities found for "${value}".`);
        return;
      }

      const exactMatch = suggestions.find(
        (suggestion) =>
          getSuggestionName(suggestion).toLocaleLowerCase() ===
          value.toLocaleLowerCase()
      );

      await loadWeather(exactMatch || suggestions[0]);
    } catch (err) {
      setCitySearchError(getErrorMessage(err));
    }
  };

  const handleCitySuggestions = async (value) => {
    setSearchInput(value);
    setCitySearchError("");

    // Increment request ID so old responses are ignored.
    const currentRequestId = ++suggestionRequestId.current;

    if (value.trim().length < 2) {
      setCitySuggestions([]);
      setSuggestionsLoading(false);
      return;
    }

    setSuggestionsLoading(true);

    try {
      const data = await api.searchCities(value.trim());

      // Ignore outdated responses.
      if (
        currentRequestId !== suggestionRequestId.current
      ) {
        return;
      }

      const suggestions = Array.isArray(data)
        ? data
        : data?.cities ||
          data?.results ||
          data?.suggestions ||
          [];

      setCitySuggestions(suggestions);
    } catch {
      if (
        currentRequestId === suggestionRequestId.current
      ) {
        setCitySuggestions([]);
        setCitySearchError("City search is unavailable. Please try again.");
      }
    } finally {
      if (
        currentRequestId === suggestionRequestId.current
      ) {
        setSuggestionsLoading(false);
      }
    }
  };

  const selectSuggestion = async (suggestion) => {
    const selectedCity = getSuggestionName(suggestion);

    if (!selectedCity) return;

    suggestionRequestId.current += 1;

    setSearchInput(selectedCity);
    setCitySuggestions([]);
    setSuggestionsLoading(false);
    setCitySearchError("");

    await loadWeather(suggestion);
  };

  // --------------------------------------------------
  // AI ASSISTANT CHAT
  // --------------------------------------------------

  const sendAssistantMessage = async (event) => {
    event.preventDefault();

    const question = assistantInput.trim();

    if (!question || assistantLoading) {
      return;
    }

    const userMessage = {
      role: "user",
      content: question,
    };

    setAssistantMessages((previous) => [
      ...previous,
      userMessage,
    ]);

    setAssistantInput("");
    setAssistantLoading(true);
    setAssistantWorkingMessage("Checking live weather...");

    try {
      let contextWeather = weatherBundle;
      const requestedCity = getCityFromWeatherQuestion(question);
      const selectedCityName = getSuggestionName(
        weatherBundle?.city
      );

      if (
        requestedCity &&
        requestedCity.toLocaleLowerCase() !==
          selectedCityName.toLocaleLowerCase()
      ) {
        const searchResult = await api.searchCities(requestedCity);
        const matches = Array.isArray(searchResult)
          ? searchResult
          : searchResult?.cities ||
            searchResult?.results ||
            searchResult?.suggestions ||
            [];

        if (matches.length === 0) {
          throw new Error(
            `I couldn't find a city matching "${requestedCity}". Please check the spelling or choose a city from the search bar.`
          );
        }

        setAssistantWorkingMessage(
          `Loading live weather for ${getSuggestionName(matches[0])}...`
        );
        contextWeather = await api.weather(
          getSuggestionName(matches[0]),
          matches[0]
        );
      } else if (!contextWeather) {
        setAssistantWorkingMessage(`Loading live weather for ${city}...`);
        contextWeather = await api.weather(city);
      }

      const response = await api.assistant(
        question,
        contextWeather,
        assistantMessages.slice(-6)
      );

      const answer =
        response?.answer ||
        response?.response ||
        response?.message ||
        response?.result ||
        "I could not generate a response.";

      setAssistantMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            typeof answer === "string"
              ? answer
              : JSON.stringify(answer, null, 2),
        },
      ]);
    } catch (err) {
      setAssistantMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content:
            `Sorry, I couldn't process that request. ${getErrorMessage(err)}`,
        },
      ]);
    } finally {
      setAssistantLoading(false);
      setAssistantWorkingMessage("");
    }
  };

  // --------------------------------------------------
  // NAVIGATION
  // --------------------------------------------------

  const handleNavigation = (page) => {
    setActivePage(page);
    setMobileMenuOpen(false);
    setError("");
  };

  // --------------------------------------------------
  // DASHBOARD PAGE
  // --------------------------------------------------

  const renderForecastOutlook = () => {
    const { warmestDay, coolestDay, rainiestDay } = forecastHighlights;

    if (dailyForecast.length === 0) {
      return null;
    }

    return (
      <div className="forecast-outlook">
        <div className="forecast-outlook-heading">
          <div>
            <p className="eyebrow">THE WEEK AHEAD</p>
            <h3>Plan your week at a glance</h3>
            <p>Weather highlights for {city}</p>
          </div>
          <label className="forecast-date-picker">
            <CalendarDays size={17} aria-hidden="true" />
            <span>Pick a forecast date</span>
            <input
              type="date"
              aria-label={`Select a forecast date for ${city}`}
              min={dailyForecast[0]?.date}
              max={dailyForecast[dailyForecast.length - 1]?.date}
              value={selectedForecastDate}
              onChange={(event) =>
                setSelectedForecastDate(event.target.value)
              }
            />
          </label>
        </div>

        <div className="forecast-highlights">
          {warmestDay && (
            <div className="forecast-highlight warm">
              <span className="forecast-highlight-icon">
                <SunMedium size={19} aria-hidden="true" />
              </span>
              <span className="forecast-highlight-label">Warmest day</span>
              <strong>
                {formatDate(warmestDay.date, { weekday: "short" })}
                <span>
                  {displayTemperature(warmestDay.max)}°{temperatureUnit}
                </span>
              </strong>
            </div>
          )}

          {coolestDay && (
            <div className="forecast-highlight cool">
              <span className="forecast-highlight-icon">
                <Thermometer size={19} aria-hidden="true" />
              </span>
              <span className="forecast-highlight-label">Coolest night</span>
              <strong>
                {formatDate(coolestDay.date, { weekday: "short" })}
                <span>
                  {displayTemperature(coolestDay.min)}°{temperatureUnit}
                </span>
              </strong>
            </div>
          )}

          {rainiestDay && (
            <div className="forecast-highlight rain">
              <span className="forecast-highlight-icon">
                <Umbrella size={19} aria-hidden="true" />
              </span>
              <span className="forecast-highlight-label">Highest rain chance</span>
              <strong>
                {formatDate(rainiestDay.date, { weekday: "short" })}
                <span>{getNumber(rainiestDay.rain, 0)}%</span>
              </strong>
            </div>
          )}
        </div>
        {selectedForecast && (
          <p className="forecast-date-summary" aria-live="polite">
            Selected day:{" "}
            <strong>
              {formatDate(selectedForecast.date, {
                weekday: "long",
                day: "numeric",
                month: "long",
              })}
            </strong>
            {" · "}
            {getWeatherDescription(Number(selectedForecast.code))}
            {" · "}
            High {displayTemperature(selectedForecast.max)}°{temperatureUnit}
            {" · "}
            Low {displayTemperature(selectedForecast.min)}°{temperatureUnit}
            {" · "}
            Rain {getNumber(selectedForecast.rain, 0)}%
          </p>
        )}
      </div>
    );
  };

  const renderDashboard = () => (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">WEATHER OVERVIEW</p>
          <h1>Today's Weather</h1>

          <p className="muted-text">
            Here's what's happening in {city}.
          </p>
        </div>

        <div className="dashboard-actions">
          <button
            className="unit-toggle"
            onClick={() =>
              setTemperatureUnit((value) =>
                value === "C" ? "F" : "C"
              )
            }
            title="Toggle temperature unit"
          >
            °{temperatureUnit}
          </button>

          <button
            className={`favorite-button ${
              favoriteCities.includes(city) ? "is-favorite" : ""
            }`}
            onClick={toggleFavoriteCity}
            title="Save city"
          >
            <Star size={17} fill="currentColor" />
          </button>

          <button
            className="auto-refresh-toggle"
            onClick={() => setAutoRefresh((value) => !value)}
            title="Toggle 15 minute auto-refresh"
          >
            <RefreshCw size={15} />
            <span>{autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}</span>
          </button>

          <button
            className="icon-button"
            onClick={() => loadWeather(city, true)}
            disabled={loading || refreshing}
            title="Refresh weather"
          >
            <RefreshCw
              size={18}
              className={refreshing ? "spin" : ""}
            />
          </button>
        </div>
      </div>

      <div className="hero-grid">
        <section className="current-card">
          <div className="current-card-top">
            <div>
              <div className="location-line">
                <MapPin size={16} />
                <span>{city}</span>
              </div>

              {cityContext && (
                <p className="location-context">{cityContext}</p>
              )}

              <p className="weather-description">
                {getWeatherDescription(weatherCode)}
              </p>
            </div>

            <WeatherIcon
              size={64}
              strokeWidth={1.3}
              className={`weather-icon weather-icon-${weatherIconTone}`}
            />
          </div>

          <div className="temperature-display">
            {displayTemperature(temperature)}
            <span>°{temperatureUnit}</span>
          </div>

          <div className="feels-like">
            Feels like {displayTemperature(feelsLike)}°{temperatureUnit}
          </div>

          <div className="current-card-bottom">
            <span>
              <Sunrise size={16} />
              Live weather conditions
            </span>

            <span>
              <Activity size={16} />
              Updated {current.time ? formatHour(current.time) : "just now"}
            </span>
          </div>

          <div className="advanced-metrics">
            <div className="advanced-metric">
              <SunMedium size={18} />
              <span>UV Index</span>
              <strong>{getDecimal(uvIndex, 1)}</strong>
            </div>
            <div className="advanced-metric">
              <Umbrella size={18} />
              <span>Rain Chance</span>
              <strong>{getNumber(rainChance, 0)}%</strong>
            </div>
            <div className="advanced-metric">
              <Cloud size={18} />
              <span>Cloud Cover</span>
              <strong>{getNumber(cloudCover, 0)}%</strong>
            </div>
            <div className="advanced-metric">
              <Sunrise size={18} />
              <span>Sunrise</span>
              <strong>{sunrise ? formatHour(sunrise) : "--"}</strong>
            </div>
            <div className="advanced-metric">
              <Sunset size={18} />
              <span>Sunset</span>
              <strong>{sunset ? formatHour(sunset) : "--"}</strong>
            </div>
          </div>

          {weatherAlerts.length > 0 && (
            <section className="weather-alerts" aria-label="Weather alerts">
              <div className="alerts-heading">
                <Bell size={17} />
                <div>
                  <strong>Weather alerts</strong>
                  <span>Important conditions to keep in mind</span>
                </div>
              </div>
              <div className="alerts-list">
                {weatherAlerts.map((alert) => (
                  <div className={`weather-alert ${alert.tone}`} key={alert.title}>
                    <strong>{alert.title}</strong>
                    <span>{alert.message}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {favoriteCities.length > 0 && (
            <div className="favorite-cities" aria-label="Favorite cities">
              <span>Favorites</span>
              {favoriteCities.map((favorite) => (
                <button
                  key={favorite}
                  onClick={() => loadWeather(favorite)}
                  className={favorite === city ? "selected" : ""}
                >
                  <Star size={13} fill="currentColor" />
                  {favorite}
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="aqi-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">AIR QUALITY ESTIMATE</p>
              <h2>Air Quality Index</h2>
              <p className="card-subtitle">Estimated for {city}</p>
            </div>

            <Wind size={23} />
          </div>

          <div className="aqi-main">
            <div className="aqi-number">
              {getNumber(aqiDetails.value)}
            </div>

            <span
              className={`aqi-status ${aqiDetails.className}`}
            >
              {aqiDetails.label}
            </span>
          </div>

          <p className="muted-text">
            {aqiDetails.scale} scale. Index scales and guidance can vary by country.
          </p>

          <div className="aqi-footer">
            <span>
              {airQualityMetadata.updated_at
                ? `Model update: ${airQualityMetadata.updated_at.replace("T", " ")}`
                : "No recent model update available"}
              {airQualityMetadata.source
                ? ` · ${airQualityMetadata.source}`
                : ""}
              <br />
              Not a local monitoring-station measurement.
            </span>
            <Activity size={17} />
          </div>
        </section>
      </div>

      <div className="stats-grid">
        <StatCard
          icon={Thermometer}
          label="Feels Like"
          value={displayTemperature(feelsLike)}
          unit={`°${temperatureUnit}`}
          description="Perceived temperature"
          tone="orange"
        />

        <StatCard
          icon={Droplets}
          label="Humidity"
          value={humidity}
          unit="%"
          description="Relative humidity"
          tone="blue"
        />

        <StatCard
          icon={Wind}
          label="Wind Speed"
          value={windSpeed}
          unit=" km/h"
          description={`Direction ${windDirection}°`}
          tone="cyan"
        />

        <StatCard
          icon={Gauge}
          label="Pressure"
          value={pressure}
          unit=" hPa"
          description="At sea level"
          tone="mint"
        />

        <StatCard
          icon={Eye}
          label="Visibility"
          value={
            visibility === "--"
              ? "--"
              : (Number(visibility) / 1000).toFixed(1)
          }
          unit={visibility === "--" ? "" : " km"}
          description="Current range"
          tone="purple"
        />

        <StatCard
          icon={Sun}
          label="Weather"
          value={getWeatherDescription(weatherCode)}
          description="Right now"
          tone="yellow"
        />
      </div>

      <section className="content-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">NEXT 24 HOURS</p>
            <h2>Hourly temperature</h2>
          </div>

          <span className="section-icon">
            <Activity size={20} />
          </span>
        </div>

        {hourlyChartData.length > 0 ? (
          <div className="chart-container">
            <ResponsiveContainer
              width="100%"
              height={260}
            >
              <AreaChart data={hourlyChartData}>
                <defs>
                  <linearGradient
                    id="temperatureGradient"
                    x1="0"
                    y1="0"
                    x2="0"
                    y2="1"
                  >
                    <stop
                      offset="0%"
                      stopColor="#38BDF8"
                      stopOpacity={0.35}
                    />

                    <stop
                      offset="100%"
                      stopColor="#2563EB"
                      stopOpacity={0.02}
                    />
                  </linearGradient>
                </defs>

                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.07)"
                  vertical={false}
                />

                <XAxis
                  dataKey="time"
                  stroke="#38BDF8"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />

                <YAxis
                  stroke="#38BDF8"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  unit={`°${temperatureUnit}`}
                />

                <Tooltip
                  contentStyle={{
                    background: "#172554",
                    border: "1px solid #38BDF8",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                  }}
                  formatter={(value) => [
                    `${value}°${temperatureUnit}`,
                    "Temperature",
                  ]}
                />

                <Area
                  type="monotone"
                  dataKey="temperature"
                  stroke="#38BDF8"
                  strokeWidth={3}
                  fill="url(#temperatureGradient)"
                  activeDot={{ r: 5 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            title="Hourly data unavailable"
            message="Hourly temperature data could not be loaded."
          />
        )}
      </section>

      <section className="content-card">
        <div className="section-heading">
          <div>
            <p className="eyebrow">UPCOMING DAYS</p>
            <h2>7-day forecast</h2>
          </div>

          <button
            className="text-button"
            onClick={() => handleNavigation("forecast")}
          >
            View details
          </button>
        </div>

        {dailyForecast.length > 0 ? (
          <>
            {renderForecastOutlook()}
            <div className="weekly-forecast">
            {dailyForecast.slice(0, 7).map((item, index) => {
              const iconTone = getWeatherIconTone(Number(item.code));

              return (
                <div
                  className={`forecast-row ${
                    selectedForecastDate === item.date ? "is-selected" : ""
                  }`}
                  key={item.date || index}
                  onClick={() => setSelectedForecastDate(item.date)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedForecastDate(item.date);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-pressed={selectedForecastDate === item.date}
                >
                  <span className="forecast-day">
                    <strong>
                      {index === 0
                        ? "Today"
                        : formatDate(item.date, { weekday: "short" })}
                    </strong>
                    <small>
                      {formatDate(item.date, { day: "numeric", month: "short" })}
                    </small>
                  </span>

                  <span className={`forecast-icon-shell ${iconTone}`}>
                    <WeatherConditionIcon code={item.code} size={25} />
                  </span>

                  <span className="forecast-condition">
                    {getWeatherDescription(Number(item.code))}
                  </span>

                  <span
                    className="forecast-rain"
                    aria-label={`${getNumber(item.rain, 0)} percent chance of rain`}
                  >
                    <span className="forecast-rain-icon">
                      <Droplets size={14} aria-hidden="true" />
                    </span>
                    <span>
                      <small>Rain</small>
                      <strong>{getNumber(item.rain, 0)}%</strong>
                    </span>
                  </span>

                  <span className="forecast-temperatures">
                    <span className="forecast-high">
                      <small>High</small>
                      <strong>{displayTemperature(item.max)}°{temperatureUnit}</strong>
                    </span>
                    <span className="forecast-low">
                      <small>Low</small>
                      <strong>{displayTemperature(item.min)}°{temperatureUnit}</strong>
                    </span>
                  </span>
                </div>
              );
            })}
            </div>
          </>
        ) : (
          <EmptyState
            title="Forecast unavailable"
            message="Daily forecast information is not available."
          />
        )}
      </section>
    </>
  );

  // --------------------------------------------------
  // FORECAST PAGE
  // --------------------------------------------------

  const renderForecast = () => (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">WEATHER PREDICTION</p>
          <h1>Weather Forecast</h1>

          <p className="muted-text">
            Upcoming weather conditions in {city}.
          </p>
        </div>
      </div>

      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>7-Day Forecast</h2>

            <p className="muted-text">
              Daily maximum and minimum temperatures
            </p>
          </div>

          <CalendarDays size={23} />
        </div>

        {dailyForecast.length > 0 ? (
          <>
            {renderForecastOutlook()}
            <div className="weekly-forecast">
            {dailyForecast.map((item, index) => {
              const iconTone = getWeatherIconTone(Number(item.code));

              return (
                <div
                  className={`forecast-row ${
                    selectedForecastDate === item.date ? "is-selected" : ""
                  }`}
                  key={item.date || index}
                  onClick={() => setSelectedForecastDate(item.date)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedForecastDate(item.date);
                    }
                  }}
                  role="button"
                  tabIndex={0}
                  aria-pressed={selectedForecastDate === item.date}
                >
                  <span className="forecast-day">
                    <strong>
                      {index === 0
                        ? "Today"
                        : formatDate(item.date, { weekday: "short" })}
                    </strong>
                    <small>
                      {formatDate(item.date, { day: "numeric", month: "short" })}
                    </small>
                  </span>

                  <span className={`forecast-icon-shell ${iconTone}`}>
                    <WeatherConditionIcon code={item.code} size={27} />
                  </span>

                  <span className="forecast-condition">
                    {getWeatherDescription(Number(item.code))}
                  </span>

                  <span
                    className="forecast-rain"
                    aria-label={`${getNumber(item.rain, 0)} percent chance of rain`}
                  >
                    <span className="forecast-rain-icon">
                      <Droplets size={14} aria-hidden="true" />
                    </span>
                    <span>
                      <small>Rain</small>
                      <strong>{getNumber(item.rain, 0)}%</strong>
                    </span>
                  </span>

                  <span className="forecast-temperatures">
                    <span className="forecast-high">
                      <small>High</small>
                      <strong>{displayTemperature(item.max)}°{temperatureUnit}</strong>
                    </span>
                    <span className="forecast-low">
                      <small>Low</small>
                      <strong>{displayTemperature(item.min)}°{temperatureUnit}</strong>
                    </span>
                  </span>
                </div>
              );
            })}
            </div>
          </>
        ) : (
          <EmptyState
            title="No forecast data"
            message="Try refreshing the weather information."
          />
        )}
      </section>

      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Hourly Forecast</h2>

            <p className="muted-text">
              Temperature over the next 24 hours
            </p>
          </div>

          <Activity size={22} />
        </div>

        {hourlyChartData.length > 0 ? (
          <div className="chart-container">
            <ResponsiveContainer
              width="100%"
              height={280}
            >
              <AreaChart data={hourlyChartData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.07)"
                />

                <XAxis
                  dataKey="time"
                  stroke="#38BDF8"
                  tick={{ fontSize: 11 }}
                />

                <YAxis
                  stroke="#38BDF8"
                  unit={`°${temperatureUnit}`}
                  tick={{ fontSize: 11 }}
                />

                <Tooltip
                  contentStyle={{
                    background: "#172554",
                    border: "1px solid #38BDF8",
                    borderRadius: "12px",
                    color: "#FFFFFF",
                  }}
                />

                <Area
                  type="monotone"
                  dataKey="temperature"
                  stroke="#EC4899"
                  fill="#EC4899"
                  fillOpacity={0.18}
                  strokeWidth={3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <EmptyState
            title="Hourly forecast unavailable"
            message="No hourly information was returned by the backend."
          />
        )}
      </section>
    </>
  );

  // --------------------------------------------------
  // COMPARISON PAGE
  // --------------------------------------------------

  const renderComparison = () => {
    const comparisonItems = Array.isArray(comparison)
      ? comparison
      : comparison?.cities ||
        comparison?.results ||
        [];
    const comparisonMetrics =
      comparison?.comparison &&
      !Array.isArray(comparison.comparison)
        ? comparison.comparison
        : null;
    const providerEntries = comparison?.providers
      ? Object.entries(comparison.providers)
      : comparison?.weather
        ? [[
            String(comparison.selected_provider || comparison.weather.source || "Weather provider")
              .toLowerCase()
              .replaceAll(" ", "_"),
            comparison.weather,
          ]]
        : [];
    const availableProviders = providerEntries.filter(
      ([, provider]) => provider && !provider.error
    );
    const failedProviders = providerEntries.filter(
      ([, provider]) => provider?.error
    );
    const diagnosticsEntries = comparison?.diagnostics
      ? Object.entries(comparison.diagnostics)
      : [];

    return (
      <>
        <div className="page-heading">
          <div>
            <p className="eyebrow">WEATHER ANALYTICS</p>
            <h1>Weather Comparison</h1>

            <p className="muted-text">
              Compare weather estimates for {city}
              {cityContext ? `, ${cityContext}` : ""}. An alternate
              forecast-model comparison is used if a provider is unavailable.
            </p>
          </div>

          <button
            className="secondary-button"
            onClick={loadComparison}
            disabled={comparisonLoading}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>

        <section className="content-card">
          <div className="section-heading">
            <div>
              <h2>Comparison Results</h2>

              <p className="muted-text">
                {comparison?.comparison_type === "model"
                  ? "Both forecast sources are checked for this location."
                  : "Available weather providers are checked independently for this location."}
              </p>
            </div>

            <BarChart3 size={22} />
          </div>

          {comparisonLoading ? (
            <div className="loading-state">
              <LoaderCircle
                className="spin"
                size={25}
              />

              <p>Loading comparison...</p>
            </div>
          ) : comparisonItems.length > 0 ? (
            <div className="comparison-grid">
              {comparisonItems.map((item, index) => (
                <div
                  className="comparison-card"
                  key={item.city || item.name || index}
                >
                  <h3>
                    {item.city ||
                      item.name ||
                      `Location ${index + 1}`}
                  </h3>

                  <div className="comparison-temperature">
                    {getNumber(
                      item.temperature ??
                      item.temperature_2m ??
                      item.current?.temperature_2m
                    )}

                    <span>°C</span>
                  </div>

                  <p>
                    {item.description ||
                      item.weather ||
                      getWeatherDescription(
                        Number(
                          item.weather_code ??
                          item.current?.weather_code
                        )
                      )}
                  </p>

                  <div className="comparison-details">
                    <span>
                      <Droplets size={15} />

                      {getNumber(
                        item.humidity ??
                        item.relative_humidity_2m ??
                        item.current?.relative_humidity_2m
                      )}%
                    </span>

                    <span>
                      <Wind size={15} />

                      {getNumber(
                        item.wind_speed ??
                        item.wind_speed_10m ??
                        item.current?.wind_speed_10m
                      )} km/h
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : !availableProviders.length ? (
            <EmptyState
              icon={BarChart3}
              title="No comparison results"
              message={
                comparisonError ||
                comparison?.message ||
                "Weather providers did not return usable data. Try refreshing."
              }
            />
          ) : null}

          {!comparisonLoading && comparison?.comparison_type === "model" && (
            <div className="comparison-notice" role="status">
              <AlertCircle size={18} />
              <div>
                <strong>Alternate model comparison</strong>
                <p>{comparison.note}</p>
              </div>
            </div>
          )}

          {!comparisonLoading && comparison?.comparison_available === false && (
            <div className="comparison-notice" role="status">
              <AlertCircle size={18} />
              <div>
                <strong>Provider comparison is incomplete</strong>
                <p>
                  {comparison.message ||
                    "Only one weather provider returned data. No provider-to-provider comparison is available."}
                  {comparison.selected_provider
                    ? ` Showing ${comparison.selected_provider} data below.`
                    : ""}
                </p>
              </div>
            </div>
          )}

          {!comparisonLoading && providerEntries.length > 0 && (
            <div className="comparison-providers">
              <div className="comparison-providers-heading">
                <h3>
                  {comparison?.comparison_type === "model"
                    ? "Weather source results"
                    : "Weather provider results"}
                </h3>
                <span>
                  {availableProviders.length} of {providerEntries.length} available
                </span>
              </div>

              <div className="comparison-grid">
                {providerEntries.map(([providerKey, provider]) => {
                  const providerName =
                    provider?.source ||
                    providerKey
                      .replaceAll("_", " ")
                      .replace(/\b\w/g, (letter) => letter.toUpperCase());
                  const providerCurrent = provider?.current || {};

                  return (
                    <div
                      className={`comparison-card ${
                        provider?.error
                          ? "comparison-card-unavailable"
                          : "comparison-card-available"
                      }`}
                      key={providerKey}
                    >
                      <div className="comparison-provider-title">
                        <h3>{providerName}</h3>
                        <span className={provider?.error ? "provider-status unavailable" : "provider-status available"}>
                          {provider?.error ? "Unavailable" : "Available"}
                        </span>
                      </div>

                      {provider?.error ? (
                        <p className="comparison-provider-error">
                          {provider.error}
                        </p>
                      ) : (
                        <>
                          <div className="comparison-temperature">
                            {getNumber(providerCurrent.temperature_2m)}
                            <span>°C</span>
                          </div>

                          <p>
                            {providerCurrent.description ||
                              getWeatherDescription(
                                Number(providerCurrent.weather_code)
                              )}
                          </p>

                          <div className="comparison-details">
                            <span>
                              <Droplets size={15} />
                              {getNumber(providerCurrent.relative_humidity_2m)}%
                            </span>
                            <span>
                              <Wind size={15} />
                              {getNumber(providerCurrent.wind_speed_10m)} km/h
                            </span>
                          </div>
                          {provider.updated_at && (
                            <small className="comparison-updated">
                              Updated {formatDate(provider.updated_at, {
                                hour: "numeric",
                                minute: "2-digit",
                              })}
                            </small>
                          )}
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {!comparisonLoading && comparisonMetrics && (
            <div className="comparison-metrics">
              <h3>
                {comparison?.comparison_type === "model"
                  ? "Forecast model differences"
                  : "Provider differences"}
              </h3>
              <div className="compare-grid">
                <div className="compare-metric">
                  <span>Temperature difference</span>
                  <b>
                    {getNumber(comparisonMetrics.temperature_difference_c)}
                    <small>°C</small>
                  </b>
                </div>
                <div className="compare-metric">
                  <span>Wind speed difference</span>
                  <b>
                    {getNumber(comparisonMetrics.wind_speed_difference_kmh)}
                    <small>km/h</small>
                  </b>
                </div>
                <div className="compare-metric">
                  <span>Humidity difference</span>
                  <b>
                    {getNumber(comparisonMetrics.humidity_difference_percent)}
                    <small>%</small>
                  </b>
                </div>
              </div>
              <p className="muted-text">
                Agreement: {comparisonMetrics.agreement_status || "Not available"}
              </p>
              {comparison?.note && (
                <p className="muted-text">{comparison.note}</p>
              )}
            </div>
          )}

          {!comparisonLoading && comparisonError && availableProviders.length > 0 && (
            <div className="comparison-notice" role="alert">
              <AlertCircle size={18} />
              <div>
                <strong>Could not refresh the comparison</strong>
                <p>{comparisonError}</p>
              </div>
            </div>
          )}

          {!comparisonLoading && (failedProviders.length > 0 || diagnosticsEntries.length > 0) && (
            <details className="comparison-diagnostics">
              <summary>Connection diagnostics</summary>
              {[...failedProviders, ...diagnosticsEntries].map(([providerKey, provider]) => (
                <p key={providerKey}>
                  <strong>{provider?.source || providerKey}:</strong>{" "}
                  {provider?.error || "Details unavailable."}
                </p>
              ))}
            </details>
          )}
        </section>

      </>
    );
  };

  // --------------------------------------------------
  // AI ASSISTANT PAGE
  // --------------------------------------------------

  const renderAssistant = () => (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">SMART WEATHER EXPERIENCE</p>
          <h1>AI Weather Assistant</h1>

          <p className="muted-text">
            Ask questions about weather and get AI-powered answers.
          </p>
        </div>

        <span className="assistant-status">
          <span className="status-dot" />
          AI Assistant
        </span>
      </div>

      <section className="content-card assistant-layout">
        <div className="assistant-info">
          <div className="assistant-avatar">
            <Bot size={27} />
          </div>

          <div>
            <h2>SkyCast AI</h2>

            <p className="muted-text">
              Your personal weather companion
            </p>
          </div>

          {assistantStatus && (
            <span className="assistant-availability">
              {assistantStatus.status ||
                assistantStatus.message ||
                "Assistant status available"}
            </span>
          )}
        </div>

        <div className="assistant-messages">
          {assistantMessages.map((message, index) => (
            <div
              className={`message-row ${
                message.role === "user"
                  ? "user-message"
                  : "bot-message"
              }`}
              key={`${message.role}-${index}`}
            >
              {message.role === "assistant" && (
                <div className="message-avatar">
                  <Bot size={17} />
                </div>
              )}

              <div className="message-bubble">
                {message.content}
              </div>
            </div>
          ))}

          {assistantLoading && (
            <div className="message-row bot-message">
              <div className="message-avatar">
                <Bot size={17} />
              </div>

              <div
                className="message-bubble assistant-working"
                role="status"
                aria-live="polite"
              >
                <LoaderCircle size={15} className="spin" />
                <span>{assistantWorkingMessage || "Preparing your answer..."}</span>
              </div>
            </div>
          )}
        </div>

        <form
          className="assistant-input-area"
          onSubmit={sendAssistantMessage}
        >
          <input
            type="text"
            value={assistantInput}
            onChange={(event) =>
              setAssistantInput(event.target.value)
            }
            placeholder="Ask something about the weather..."
            disabled={assistantLoading}
          />

          <button
            type="submit"
            className="send-button"
            disabled={
              !assistantInput.trim() ||
              assistantLoading
            }
            aria-label="Send message"
          >
            <Send size={18} />
          </button>
        </form>

        <p className="assistant-disclaimer">
          AI-generated answers may occasionally be inaccurate.
          Verify important weather and safety information with
          official sources.
        </p>
      </section>

      {/* MCP TOOLS SECTION */}

      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>MCP Tools</h2>

            <p className="muted-text">
              Discover and execute tools from your MCP backend.
            </p>
          </div>

          <Settings size={21} />
        </div>

        <div className="mcp-arguments-section">
          <label htmlFor="mcp-arguments">
            City name
          </label>

          <input
            type="text"
            id="mcp-arguments"
            value={mcpArgumentsInput}
            onChange={(event) =>
              setMcpArgumentsInput(event.target.value)
            }
            placeholder={`Type any city name (blank uses ${city})`}
            disabled={Boolean(mcpExecutingTool)}
          />

          <p className="muted-text">
            Type just the place name—no JSON or code needed. Leave it
            blank to use {city}. Advanced JSON arguments are also accepted.
          </p>

          <button
            type="button"
            className="secondary-button"
            onClick={() => {
              setMcpArgumentsInput(city);
              setMcpError("");
            }}
            disabled={Boolean(mcpExecutingTool)}
          >
            Use selected city
          </button>
        </div>

        {mcpError && (
          <div className="error-banner">
            <AlertCircle size={17} />
            <span>{mcpError}</span>

            <button
              onClick={() => setMcpError("")}
              aria-label="Dismiss MCP error"
            >
              <X size={16} />
            </button>
          </div>
        )}

        {mcpLoading ? (
          <div className="loading-state">
            <LoaderCircle
              size={23}
              className="spin"
            />

            <p>Loading MCP tools...</p>
          </div>
        ) : mcpTools.length > 0 ? (
          <div className="mcp-tools-list">
            {mcpTools.map((tool, index) => {
              const toolName =
                tool.name || `Tool ${index + 1}`;

              const isExecuting =
                mcpExecutingTool === toolName;

              return (
                <div
                  className="mcp-tool-item"
                  key={toolName}
                >
                  <div>
                    <strong>{toolName}</strong>

                    <p>
                      {tool.description ||
                        "No description available"}
                    </p>
                  </div>

                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => runMcpTool(tool)}
                    disabled={Boolean(mcpExecutingTool)}
                  >
                    {isExecuting ? (
                      <>
                        <LoaderCircle
                          size={16}
                          className="spin"
                        />
                        Running...
                      </>
                    ) : (
                      <>
                        <Send size={15} />
                        Execute
                      </>
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState
            icon={Settings}
            title="No MCP tools found"
            message={
              mcpError ||
              "No tools were returned by the MCP endpoint."
            }
          />
        )}

        {mcpResult && (
          <div className="mcp-result-section">
            <div className="section-heading">
              <div>
                <h3>MCP Execution Result</h3>

                <p className="muted-text">
                  Tool: {mcpResult.toolName}
                </p>
              </div>

              <CheckCircle2 size={20} />
            </div>

            <pre className="json-output">
              {JSON.stringify(
                mcpResult.response,
                null,
                2
              )}
            </pre>
          </div>
        )}
      </section>
    </>
  );

  // --------------------------------------------------
  // HISTORY PAGE
  // --------------------------------------------------

  const renderHistory = () => (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">PAST WEATHER RECORDS</p>
          <h1>Weather History</h1>

          <p className="muted-text">
            Review previously stored weather information.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={loadHistory}
          disabled={historyLoading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <section className="content-card">
        <div className="section-heading">
          <div>
            <h2>Saved Records</h2>

            <p className="muted-text">
              {history.length} records available
            </p>
          </div>

          <History size={22} />
        </div>

        {historyLoading ? (
          <div className="loading-state">
            <LoaderCircle
              className="spin"
              size={25}
            />

            <p>Loading history...</p>
          </div>
        ) : history.length > 0 ? (
          <div className="history-table-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>City</th>
                  <th>Temperature</th>
                  <th>Date</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {history.map((item, index) => {
                  const id = getHistoryId(item);

                  return (
                    <tr key={id ?? index}>
                      <td>
                        <span className="history-city">
                          <MapPin size={15} />
                          {getHistoryCity(item)}
                        </span>
                      </td>

                      <td>
                        {getHistoryTemperature(item)}

                        {getHistoryTemperature(item) !== "--"
                          ? "°C"
                          : ""}
                      </td>

                      <td>
                        {formatDate(
                          item.created_at ||
                          item.timestamp ||
                          item.date ||
                          item.recorded_at
                        )}
                      </td>

                      <td>
                        <button
                          className="delete-button"
                          onClick={() =>
                            handleDeleteHistory(id)
                          }
                          disabled={
                            id === null ||
                            id === undefined
                          }
                          title="Delete record"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={History}
            title="No history available"
            message="Weather records will appear here when they are saved by the backend."
          />
        )}
      </section>
    </>
  );

  // --------------------------------------------------
  // PAGE ROUTING
  // --------------------------------------------------

  const pageContent = {
    dashboard: renderDashboard,
    forecast: renderForecast,
    compare: renderComparison,
    assistant: renderAssistant,
    history: renderHistory,
  };

  // --------------------------------------------------
  // MAIN APPLICATION UI
  // --------------------------------------------------

  return (
    <div className="app-shell">
      {mobileMenuOpen && (
        <button
          className="mobile-overlay"
          onClick={() => setMobileMenuOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <aside
        className={`sidebar ${
          mobileMenuOpen ? "sidebar-open" : ""
        }`}
      >
        <div className="brand">
          <div className="brand-icon">
            <CloudSun size={25} />
          </div>

          <div className="brand-text">
            <strong>SkyCast</strong>
            <span>WEATHER STUDIO</span>
          </div>

          <button
            className="mobile-close"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <div className="sidebar-section-label">
          WORKSPACE
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;

            return (
              <button
                key={item.id}
                className={`nav-item ${
                  activePage === item.id
                    ? "nav-item-active"
                    : ""
                }`}
                aria-current={activePage === item.id ? "page" : undefined}
                onClick={() =>
                  handleNavigation(item.id)
                }
              >
                <Icon size={19} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <div className="backend-status">
            <span
              className={`status-dot ${
                backendStatus === "online"
                  ? "status-online"
                  : backendStatus === "offline"
                    ? "status-offline"
                    : ""
              }`}
            />

            <div>
              <strong>Backend</strong>

              <span>
                {backendStatus === "online"
                  ? "Connected"
                  : backendStatus === "offline"
                    ? "Disconnected"
                    : "Checking..."}
              </span>
            </div>
          </div>

          <div className="sidebar-footer">
            <Cloud size={17} />
            <span>SkyCast Weather App</span>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="mobile-menu-button"
              onClick={() =>
                setMobileMenuOpen(true)
              }
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>

            <div className="breadcrumb">
              <span>SkyCast</span>

              <span className="breadcrumb-divider">
                /
              </span>

              <strong>
                {
                  NAV_ITEMS.find(
                    (item) => item.id === activePage
                  )?.label
                }
              </strong>
            </div>
          </div>

          <div className="topbar-right">
            <form
              className="search-wrap"
              onSubmit={handleSearch}
            >
              <Search size={17} />

              <input
                type="text"
                value={searchInput}
                onChange={(event) =>
                  handleCitySuggestions(
                    event.target.value
                  )
                }
                placeholder="Search city..."
                aria-label="Search city"
                aria-autocomplete="list"
                aria-expanded={
                  searchInput.trim().length >= 2 &&
                  (suggestionsLoading || citySuggestions.length > 0 || Boolean(citySearchError))
                }
                aria-controls="city-suggestions"
                autoComplete="off"
              />

              {searchInput && (
                <button
                  type="button"
                  className="clear-search"
                  onClick={() => {
                    suggestionRequestId.current += 1;

                    setSearchInput("");
                    setCitySuggestions([]);
                    setSuggestionsLoading(false);
                    setCitySearchError("");
                  }}
                  aria-label="Clear search"
                >
                  <X size={15} />
                </button>
              )}

              <button
                type="submit"
                className="search-submit"
                disabled={!searchInput.trim() || loading}
                aria-label={loading ? "Loading weather" : "Search weather"}
              >
                {loading ? (
                  <>
                    <LoaderCircle size={15} className="spin" />
                    <span>Loading</span>
                  </>
                ) : (
                  <>
                    <Search size={15} aria-hidden="true" />
                    <span>Search</span>
                  </>
                )}
              </button>

              {searchInput.trim().length >= 2 && (
                <div
                  className="suggestions"
                  id="city-suggestions"
                  role="listbox"
                  aria-label="City search results"
                >
                  {suggestionsLoading && (
                    <div className="suggestion-loading">
                      <LoaderCircle
                        size={15}
                        className="spin"
                      />

                      <span>Searching cities...</span>
                    </div>
                  )}

                  {!suggestionsLoading && citySearchError && (
                    <div className="suggestion-loading" role="status">
                      {citySearchError}
                    </div>
                  )}

                  {!suggestionsLoading &&
                    !citySearchError &&
                    citySuggestions
                      .slice(0, 6)
                      .map((suggestion, index) => {
                        const name =
                          getSuggestionName(suggestion);

                        if (!name) return null;

                        return (
                          <button
                            type="button"
                            key={`${name}-${index}`}
                            role="option"
                            aria-selected="false"
                            onMouseDown={(event) => event.preventDefault()}
                            onClick={() =>
                              selectSuggestion(suggestion)
                            }
                          >
                            <MapPin size={16} aria-hidden="true" />
                            <span className="suggestion-copy">
                              <strong>{name}</strong>
                              {getSuggestionDetails(suggestion) && (
                                <small>{getSuggestionDetails(suggestion)}</small>
                              )}
                            </span>
                          </button>
                        );
                      })}

                  {!suggestionsLoading &&
                    !citySearchError &&
                    citySuggestions.length === 0 &&
                    (
                      <div className="suggestion-loading">
                        No matching cities found.
                      </div>
                    )}
                </div>
              )}
            </form>

            <div className="topbar-date">
              {formatDate(
                new Date().toISOString(),
                {
                  weekday: "short",
                  day: "numeric",
                  month: "short",
                }
              )}
            </div>
          </div>
        </header>

        <div className="page-content">
          {error && (
            <div className="error-banner">
              <AlertCircle size={18} />

              <span>{error}</span>

              <button
                onClick={() => setError("")}
                aria-label="Dismiss error"
              >
                <X size={17} />
              </button>
            </div>
          )}

          {loading ? (
            <div className="page-loading">
              <LoaderCircle
                size={36}
                className="spin"
              />

              <h2>Loading weather...</h2>

              <p>
                Getting the latest information for {city}.
              </p>
            </div>
          ) : (
            pageContent[activePage]?.()
          )}
        </div>

        <footer className="app-footer">
          <div className="footer-brand">
            <span className="footer-brand-icon">
              <CloudSun size={20} />
            </span>
            <span className="footer-brand-copy">
              <strong>SkyCast</strong>
              <small>Weather Studio</small>
            </span>
          </div>

          <div className="footer-details">
            <span className="footer-service-status">
              <span
                className={`footer-status-dot ${
                  backendStatus === "online"
                    ? "is-online"
                    : backendStatus === "offline"
                      ? "is-offline"
                      : ""
                }`}
              />
              {backendStatus === "online"
                ? "Weather services connected"
                : backendStatus === "offline"
                  ? "Weather services unavailable"
                  : "Connecting to weather services"}
            </span>
            <span className="footer-divider" aria-hidden="true" />
            <span className="footer-data-source">
              <Compass size={15} />
              Provider-based weather data
            </span>
            <small className="footer-disclaimer">
              Forecasts and readings are estimates.
            </small>
          </div>
        </footer>
      </main>
    </div>
  );
}

export default App;