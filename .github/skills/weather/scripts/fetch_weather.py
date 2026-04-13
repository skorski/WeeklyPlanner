#!/usr/bin/env python3
"""Fetch weekly weather forecast for Reston, VA from Open-Meteo and output as markdown."""

import argparse
from datetime import date, timedelta, datetime
from pathlib import Path
import sys

import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from jinja2 import Environment, FileSystemLoader

# Reston, VA coordinates
LATITUDE = 38.9687
LONGITUDE = -77.3411
LOCATION = "Reston, VA"

# WMO Weather interpretation codes
WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def classify_sunshine(pct):
    """Classify a day based on % of daylight hours with sunshine."""
    if pct >= 85:
        return "Sunny"
    elif pct >= 60:
        return "Mostly Sunny"
    elif pct >= 40:
        return "Mostly Cloudy"
    else:
        return "Cloudy"


def get_sunday_range(ref_date=None):
    """Return the Sunday-to-Sunday range for the forecast week.

    On Friday (weekday 4) or Saturday (weekday 5), return next week's range
    (the upcoming Sunday). Otherwise return the current week's range.
    """
    if ref_date is None:
        ref_date = date.today()
    days_since_sunday = (ref_date.weekday() + 1) % 7
    start_sunday = ref_date - timedelta(days=days_since_sunday)
    # On Friday or Saturday, shift forward to next Sunday
    if ref_date.weekday() in (4, 5):
        start_sunday += timedelta(days=7)
    end_sunday = start_sunday + timedelta(days=6)
    return start_sunday, end_sunday


def fetch_forecast(start_date, end_date):
    """Fetch daily + hourly forecast from Open-Meteo API."""
    cache_session = requests_cache.CachedSession(
        str(Path(__file__).resolve().parent / ".cache"),
        expire_after=3600,
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    client = openmeteo_requests.Client(session=retry_session)

    params = {
        "latitude": LATITUDE,
        "longitude": LONGITUDE,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_probability_max",
            "precipitation_sum",
            "rain_sum",
            "showers_sum",
            "wind_speed_10m_max",
            "wind_gusts_10m_max",
            "sunshine_duration",
            "daylight_duration",
        ],
        "hourly": [
            "cloud_cover",
            "sunshine_duration",
        ],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/New_York",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }

    responses = client.weather_api("https://api.open-meteo.com/v1/forecast", params=params)
    return responses[0]


def build_template_data(response, start_date, end_date):
    """Transform API response into template-friendly context."""
    # --- Daily data ---
    daily = response.Daily()
    daily_time = pd.date_range(
        start=pd.to_datetime(daily.Time() + response.UtcOffsetSeconds(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd() + response.UtcOffsetSeconds(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left",
    )
    daily_df = pd.DataFrame({
        "date": daily_time,
        "weather_code": daily.Variables(0).ValuesAsNumpy(),
        "temp_max": daily.Variables(1).ValuesAsNumpy(),
        "temp_min": daily.Variables(2).ValuesAsNumpy(),
        "precip_prob": daily.Variables(3).ValuesAsNumpy(),
        "precip_sum": daily.Variables(4).ValuesAsNumpy(),
        "rain_sum": daily.Variables(5).ValuesAsNumpy(),
        "showers_sum": daily.Variables(6).ValuesAsNumpy(),
        "wind_max": daily.Variables(7).ValuesAsNumpy(),
        "wind_gusts": daily.Variables(8).ValuesAsNumpy(),
        "sunshine_duration_s": daily.Variables(9).ValuesAsNumpy(),
        "daylight_duration_s": daily.Variables(10).ValuesAsNumpy(),
    })

    # --- Hourly data ---
    hourly = response.Hourly()
    hourly_time = pd.date_range(
        start=pd.to_datetime(hourly.Time() + response.UtcOffsetSeconds(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd() + response.UtcOffsetSeconds(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )
    hourly_df = pd.DataFrame({
        "date": hourly_time,
        "cloud_cover": hourly.Variables(0).ValuesAsNumpy(),
        "sunshine_duration_s": hourly.Variables(1).ValuesAsNumpy(),
    })
    hourly_df["day"] = hourly_df["date"].dt.date

    # Compute hourly sunshine stats per day
    # sunshine_duration is in seconds per hour (max 3600)
    hourly_sun = hourly_df.groupby("day").agg(
        avg_cloud_cover=("cloud_cover", "mean"),
        total_sunshine_s=("sunshine_duration_s", "sum"),
        hours_with_sun=("sunshine_duration_s", lambda x: (x > 0).sum()),
        total_hours=("sunshine_duration_s", "count"),
    ).reset_index()

    # --- Build days list ---
    days = []
    for _, row in daily_df.iterrows():
        day_date = row["date"].date()
        code = int(row["weather_code"])

        # Match hourly sunshine stats for this day
        sun_row = hourly_sun[hourly_sun["day"] == day_date]

        sunshine_hrs = row["sunshine_duration_s"] / 3600.0
        daylight_hrs = row["daylight_duration_s"] / 3600.0
        sunshine_pct = (sunshine_hrs / daylight_hrs * 100) if daylight_hrs > 0 else 0
        avg_cloud = float(sun_row["avg_cloud_cover"].iloc[0]) if len(sun_row) > 0 else 0

        days.append({
            "name": day_date.strftime("%a %m/%d"),
            "long_name": day_date.strftime("%A, %B %d"),
            # For cloudiness-only codes (0-3), derive conditions from actual
            # sunshine data instead of the WMO code, which often says "Overcast"
            # even on days with 90%+ sunshine.
            "conditions": (classify_sunshine(sunshine_pct) if code <= 3
                           else WMO_CODES.get(code, f"Unknown ({code})")),
            "high": f"{row['temp_max']:.0f}",
            "low": f"{row['temp_min']:.0f}",
            "precip_pct": int(row["precip_prob"]) if not pd.isna(row["precip_prob"]) else 0,
            "precip_in": f"{(row['precip_sum'] if not pd.isna(row['precip_sum']) else 0.0):.2f}",
            "wind": f"{(row['wind_max'] if not pd.isna(row['wind_max']) else 0):.0f}",
            "gusts": f"{(row['wind_gusts'] if not pd.isna(row['wind_gusts']) else 0):.0f}",
            "sunshine_hrs": f"{sunshine_hrs:.1f}",
            "daylight_hrs": f"{daylight_hrs:.1f}",
            "sunshine_pct": int(round(sunshine_pct)),
            "sunshine_class": classify_sunshine(sunshine_pct),
            "avg_cloud_cover": int(round(avg_cloud)),
        })

    return {
        "location": LOCATION,
        "start_date": start_date.strftime("%B %d, %Y"),
        "end_date": end_date.strftime("%B %d, %Y"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "days": days,
    }


def render_markdown(context, template_name="weekly_forecast.md.j2"):
    """Render markdown from a Jinja2 template."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        keep_trailing_newline=True,
    )
    template = env.get_template(template_name)
    return template.render(context)


def main():
    parser = argparse.ArgumentParser(description="Fetch weekly weather for Reston, VA")
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--start",
        help="Start date (YYYY-MM-DD). Defaults to the most recent Sunday.",
    )
    parser.add_argument(
        "--end",
        help="End date (YYYY-MM-DD). Defaults to the following Sunday.",
    )
    args = parser.parse_args()

    if args.start and args.end:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    elif args.start:
        start_date = date.fromisoformat(args.start)
        end_date = start_date + timedelta(days=7)
    else:
        start_date, end_date = get_sunday_range()

    data = fetch_forecast(start_date, end_date)
    context = build_template_data(data, start_date, end_date)
    md = render_markdown(context)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Weather forecast written to {args.output}", file=sys.stderr)
    else:
        print(md)


if __name__ == "__main__":
    main()
