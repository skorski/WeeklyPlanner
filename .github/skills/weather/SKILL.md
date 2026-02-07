---
name: weather
description: >
  Fetch the weekly weather forecast for Reston, VA and format it as a structured
  markdown file for use by other agents. Use this skill when the user asks for the
  weather, weekly forecast, or weather planning information for Reston, VA.
  Default range is Sunday-to-Sunday. Outputs a markdown file with a summary table
  and daily details including high/low temperatures, precipitation, wind, conditions,
  sunshine hours, cloud cover, and a sunshine classification (Sunny, Mostly Sunny,
  Mostly Cloudy, Cloudy).
---

# Weather Forecast Skill

Fetch and format the weekly weather for Reston, VA using the Open-Meteo API (free, no API key).

## Usage

Run the bundled script to generate the forecast:

```bash
python scripts/fetch_weather.py -o <output-path>
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-o`, `--output` | Output file path | stdout |
| `--start` | Start date (YYYY-MM-DD) | Most recent Sunday |
| `--end` | End date (YYYY-MM-DD) | Following Sunday |

### Default Behavior

When invoked with no date arguments, the script computes the Sunday-to-Sunday range
containing today and fetches the forecast for that full week.

### Output Format

The generated markdown contains:

1. **Header** with location, date range, and generation timestamp
2. **Summary table** with day, conditions, high/low temp, precipitation %, rainfall, and wind
3. **Daily details** section with expanded info per day (including wind gusts)

### Example

```bash
# Default Sunday-to-Sunday forecast, saved to weather.md
python scripts/fetch_weather.py -o weather.md

# Custom date range
python scripts/fetch_weather.py --start 2026-02-08 --end 2026-02-15 -o weather.md
```

## Notes

- Uses Open-Meteo API — no API key required, no rate-limit concerns for normal use
- Temperatures in Fahrenheit, wind in mph, precipitation in inches
- Coordinates hardcoded to Reston, VA (38.9687, -77.3411)
- Requires Python 3.7+ and `jinja2 openmeteo-requests requests-cache retry-requests pandas`
- The markdown layout is defined in `templates/weekly_forecast.md.j2` — edit the template to customize output format
- Sunshine classification: Sunny (≥75%), Mostly Sunny (50-74%), Mostly Cloudy (25-49%), Cloudy (<25%) based on % of daylight hours with sunshine