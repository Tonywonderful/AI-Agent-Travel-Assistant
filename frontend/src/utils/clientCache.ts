import type { Itinerary, WeatherForecastResponse } from "../types";

const ITINERARY_KEY = "zhilv:latest-itinerary";
const VIEW_KEY = "zhilv:current-view";
const WEATHER_KEY_PREFIX = "zhilv:weather:forecast:";

/** 与后端 REDIS_WEATHER_TTL_SECONDS 默认 1800s 对齐 */
export const WEATHER_CACHE_TTL_MS = 30 * 60 * 1000;

export type AppView = "home" | "result" | "history";

function normalizeCity(city: string): string {
  return city.trim().toLowerCase();
}

function safeParseJson<T>(raw: string | null): T | null {
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export function loadLatestItinerary(): Itinerary | null {
  if (typeof localStorage === "undefined") return null;
  const parsed = safeParseJson<Itinerary>(localStorage.getItem(ITINERARY_KEY));
  if (!parsed?.trip_id || !parsed.destination || !Array.isArray(parsed.days)) {
    return null;
  }
  return parsed;
}

export function saveLatestItinerary(itinerary: Itinerary | null): void {
  if (typeof localStorage === "undefined") return;
  try {
    if (!itinerary) {
      localStorage.removeItem(ITINERARY_KEY);
      return;
    }
    localStorage.setItem(ITINERARY_KEY, JSON.stringify(itinerary));
  } catch {
    // quota / private mode：静默失败，不影响主流程
  }
}

export function loadCurrentView(): AppView | null {
  if (typeof localStorage === "undefined") return null;
  const value = localStorage.getItem(VIEW_KEY);
  if (value === "home" || value === "result" || value === "history") return value;
  return null;
}

export function saveCurrentView(view: AppView): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(VIEW_KEY, view);
  } catch {
    // ignore
  }
}

interface WeatherCacheEntry {
  expireAt: number;
  data: WeatherForecastResponse;
}

export function getCachedWeather(city: string): WeatherForecastResponse | null {
  if (typeof localStorage === "undefined" || !city.trim()) return null;
  const key = `${WEATHER_KEY_PREFIX}${normalizeCity(city)}`;
  const entry = safeParseJson<WeatherCacheEntry>(localStorage.getItem(key));
  if (!entry?.data || typeof entry.expireAt !== "number") return null;
  if (Date.now() > entry.expireAt) {
    try {
      localStorage.removeItem(key);
    } catch {
      // ignore
    }
    return null;
  }
  return entry.data;
}

export function setCachedWeather(city: string, data: WeatherForecastResponse): void {
  if (typeof localStorage === "undefined" || !city.trim()) return;
  const key = `${WEATHER_KEY_PREFIX}${normalizeCity(city)}`;
  const entry: WeatherCacheEntry = {
    expireAt: Date.now() + WEATHER_CACHE_TTL_MS,
    data,
  };
  try {
    localStorage.setItem(key, JSON.stringify(entry));
  } catch {
    // ignore
  }
}

/** 同城并发请求去重（跨组件实例） */
const weatherInflight = new Map<string, Promise<WeatherForecastResponse>>();

export function getWeatherInflight(
  city: string
): Promise<WeatherForecastResponse> | undefined {
  return weatherInflight.get(normalizeCity(city));
}

export function setWeatherInflight(
  city: string,
  request: Promise<WeatherForecastResponse>
): void {
  weatherInflight.set(normalizeCity(city), request);
}

export function clearWeatherInflight(city: string): void {
  weatherInflight.delete(normalizeCity(city));
}

/** 行程自动保存去重（跨组件实例） */
const autoSavedTripIds = new Set<string>();

export function hasAutoSavedTrip(tripId: string): boolean {
  return autoSavedTripIds.has(tripId);
}

export function markTripAutoSaved(tripId: string): void {
  autoSavedTripIds.add(tripId);
}
