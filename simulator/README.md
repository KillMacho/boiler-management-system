# Boiler Telemetry Simulator

Simulates 15 boiler units sending real-time telemetry to the backend REST API.

## Quick Start

```bash
cd simulator

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Copy and edit configuration
copy .env.example .env
# Edit .env: set BACKEND_URL if the backend is not on localhost:8000

# Run simulator (reads .env automatically)
python -m app.main
```

## CLI Options

```
python -m app.main [OPTIONS]

  --boilers N            Number of boilers to simulate (default: 15)
  --interval SECONDS     Seconds between readings per boiler (default: 30)
  --no-alarms            Disable random alarm injection
  --trigger-alarm ID:SCENARIO
                         Trigger an alarm immediately at startup,
                         e.g. --trigger-alarm 3:overheat
  --duration SECONDS     Stop automatically after N seconds
  --log-level LEVEL      DEBUG | INFO | WARNING | ERROR (default: INFO)
```

### Examples

```bash
# 1-minute smoke test, 3 boilers, 5-second interval
python -m app.main --boilers 3 --interval 5 --duration 60

# Force an overheat alarm on boiler 1 immediately
python -m app.main --trigger-alarm 1:overheat --interval 10 --duration 60

# No alarms, useful for load testing
python -m app.main --no-alarms --interval 10

# Verbose output
python -m app.main --log-level DEBUG --duration 30
```

## Alarm Scenarios

| Scenario | Parameters affected | Expected backend reaction |
|---|---|---|
| `overheat` | temperature_heat > 110°C | status=critical, auto-request Авария |
| `leak` | pressure < 0.09 MPa, low water_level | status=critical, auto-request Авария |
| `co_spike` | co_level > 55 mg/m³ | status=critical, auto-request Авария |
| `draft_failure` | furnace_draft ≈ 0 Pa | status=critical, auto-request Авария |
| `low_water` | water_level < 145 mm | status=critical, auto-request Авария |

Alarms are triggered randomly every 30–90 minutes per boiler (configurable via `ALARM_MIN_INTERVAL` / `ALARM_MAX_INTERVAL` in `.env`). Each alarm lasts 2–5 reading intervals, then auto-resets.

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | Backend base URL |
| `ADMIN_USERNAME` | `admin` | Auth credentials |
| `ADMIN_PASSWORD` | `admin123` | Auth credentials |
| `NUM_BOILERS` | `15` | Boilers to simulate |
| `SEND_INTERVAL` | `30` | Seconds between readings |
| `ALARM_MIN_INTERVAL` | `1800` | Min seconds between alarms (30 min) |
| `ALARM_MAX_INTERVAL` | `5400` | Max seconds between alarms (90 min) |
| `ENABLE_ALARMS` | `true` | Master alarm toggle |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Running Tests

```bash
cd simulator
python -m pytest tests/ -v
```

Tests use mocked HTTP — no running backend required.

## Architecture

```
simulator/
├── app/
│   ├── config.py             # pydantic-settings from .env
│   ├── parameter_models.py   # normal ranges + critical thresholds per parameter
│   ├── scenarios.py          # 5 alarm scenario functions
│   ├── boiler_simulator.py   # BoilerSimulator (normal + alarm mode)
│   ├── telemetry_sender.py   # httpx AsyncClient + tenacity retry
│   └── main.py               # asyncio event loop, argparse CLI
├── tests/
│   └── test_boiler_simulator.py
├── .env                      # local config (gitignored)
├── .env.example
├── requirements.txt
└── README.md
```

## Verifying Against the Backend

After a 1-minute run:

```sql
-- Count telemetry rows created
SELECT COUNT(*) FROM telemetry WHERE [timestamp] > DATEADD(MINUTE, -2, GETUTCDATE());

-- Check for auto-created alarm requests
SELECT * FROM requests WHERE source = 'monitoring' ORDER BY created_at DESC;

-- View current boiler statuses
-- GET /api/v1/monitoring/status
```
