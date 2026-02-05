# ⚡ Energy Trading Connectivity Monitor

> A real-time monitoring solution for energy market data integration, focusing on dynamic pricing, power plant status, and demand-side management signals.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![Pandas](https://img.shields.io/badge/Pandas-2.0+-yellow.svg)](https://pandas.pydata.org)
[![Grafana](https://img.shields.io/badge/Grafana-10.0+-orange.svg)](https://grafana.com)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)

---

## 📋 Table of Contents

- [Business Context](#-business-context)
- [System Architecture](#-system-architecture)
- [Components](#-components)
- [Data Flow](#-data-flow)
- [API Endpoints](#-api-endpoints)
- [Data Model](#-data-model)
- [Tech Stack](#-tech-stack)
- [Installation & Setup](#-installation--setup)
- [Grafana Dashboards](#-grafana-dashboards)
- [Project Structure](#-project-structure)

---

## 🏢 Business Context

### The Energy Trading Challenge
Energy traders and analysts depend on multiple external APIs to:
1. Obtain **dynamic energy prices** (quarter-hourly resolution)
2. Monitor **power plant status** in real-time
3. Anticipate **demand-side management signals** (DSM/DSR)

When these integrations fail, traders lose visibility and reaction capability. This project implements a **connectivity monitor** that:
- ✅ Centralizes data ingestion from multiple endpoints
- ✅ Detects and alerts on connection failures
- ✅ Visualizes business metrics and technical health in real-time

### Data Source
This project uses the **CKW (Centralschweizerische Kraftwerke)** public API specification as reference data. CKW is a Swiss energy utility that provides:
- Dynamic grid pricing (15-minute intervals)
- Live power plant telemetry
- TRA (Tonfrequenz-Rundsteuer-Anlage) control signals

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ENERGY TRADING CONNECTIVITY MONITOR                  │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────────┐
│                  │     │                  │     │                          │
│   MOCK SERVER    │────▶│   ETL CLIENT     │────▶│   PERSISTENCE LAYER      │
│   (FastAPI)      │     │   (Python)       │     │   (PostgreSQL)           │
│                  │     │                  │     │                          │
│  ┌────────────┐  │     │  ┌────────────┐  │     │  ┌────────────────────┐  │
│  │ OAuth2     │  │     │  │ Token Mgr  │  │     │  │ energy_prices      │  │
│  │ /token     │  │     │  │ (refresh)  │  │     │  │ plant_status       │  │
│  └────────────┘  │     │  └────────────┘  │     │  │ control_signals    │  │
│                  │     │                  │     │  │ api_health_logs    │  │
│  ┌────────────┐  │     │  ┌────────────┐  │     │  └────────────────────┘  │
│  │ /prices    │  │     │  │ Pandas     │  │     │                          │
│  │ /plant     │  │     │  │ Processing │  │     └──────────────────────────┘
│  │ /signals   │  │     │  └────────────┘  │                 │
│  └────────────┘  │     │                  │                 │
│                  │     │  ┌────────────┐  │                 ▼
│  ┌────────────┐  │     │  │ Health     │  │     ┌──────────────────────────┐
│  │ /health    │  │     │  │ Checker    │  │     │                          │
│  └────────────┘  │     │  └────────────┘  │     │   VISUALIZATION LAYER    │
│                  │     │                  │     │   (Grafana)              │
└──────────────────┘     └──────────────────┘     │                          │
                                                  │  ┌────────────────────┐  │
       Port: 8000              Scheduler          │  │ Dashboard:         │  │
                               (every 5 min)      │  │ • Energy Prices    │  │
                                                  │  │ • Plant Status     │  │
                                                  │  │ • API Health       │  │
                                                  │  └────────────────────┘  │
                                                  │                          │
                                                  │      Port: 3000          │
                                                  └──────────────────────────┘
```

---

## 🧩 Components

### 1. Mock Server (FastAPI)
Simulates the CKW API with OAuth2 protection.

| Feature | Description |
|---------|-------------|
| **Framework** | FastAPI (async, OpenAPI autodoc) |
| **Authentication** | OAuth2 with Client Credentials Flow |
| **Data** | Real JSONs from CKW specification |
| **Rate Limiting** | Simulated with standard headers |

**Implemented endpoints:**
```
POST /oauth/token              → Access token generation
GET  /api/v1/energy/prices     → Dynamic prices (15 min)
GET  /api/v1/plant/live        → Live power plant status
GET  /api/v1/control/signals   → TRA signals for the day
GET  /health                   → Server health check
```

### 2. ETL Client (Python + Pandas)
Consumes the API, manages tokens, and processes data.

| Feature | Description |
|---------|-------------|
| **HTTP Client** | `httpx` (async support) |
| **Token Management** | Auto-refresh before expiration |
| **Processing** | Pandas for nested JSON normalization |
| **Scheduling** | APScheduler for periodic execution |
| **Logging** | Structured with `structlog` |

**Main flow:**
```python
# Main pipeline
1. Obtain/renew access_token (OAuth2)
2. Call each endpoint with retry logic
3. Parse JSON → Pandas DataFrame
4. Insert into PostgreSQL
5. Log health metrics (latency, errors)
```

### 3. Persistence Layer (PostgreSQL)
Relational database for time series and logs storage.

**Table schema:**

```sql
-- Dynamic energy prices (quarter-hourly)
CREATE TABLE energy_prices (
    id SERIAL PRIMARY KEY,
    publication_timestamp TIMESTAMPTZ,
    start_timestamp TIMESTAMPTZ,
    end_timestamp TIMESTAMPTZ,
    tariff_type VARCHAR(20),
    unit VARCHAR(10),
    value DECIMAL(10,6),
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Live power plant status
CREATE TABLE plant_status (
    id SERIAL PRIMARY KEY,
    plant_id VARCHAR(50),
    timestamp TIMESTAMPTZ,
    operational_status VARCHAR(50),
    voltage_kv DECIMAL(10,6),
    active_power_mw DECIMAL(10,6),
    reactive_power_mvar DECIMAL(10,6),
    wind_speed_kmh DECIMAL(10,6),
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- Demand-side control signals (TRA)
CREATE TABLE control_signals (
    id SERIAL PRIMARY KEY,
    signal_name VARCHAR(20),
    description VARCHAR(100),
    signal_date DATE,
    start_timestamp TIMESTAMPTZ,
    end_timestamp TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ DEFAULT NOW()
);

-- API health logs (for monitoring)
CREATE TABLE api_health_logs (
    id SERIAL PRIMARY KEY,
    endpoint VARCHAR(100),
    status_code INTEGER,
    response_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    checked_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. Visualization Layer (Grafana)
Dashboards for traders and support teams.

**Planned panels:**

| Panel | Type | Data Source |
|-------|------|-------------|
| **Integrated Price (15 min)** | Time series | `energy_prices` filtered by `integrated` |
| **Tariff Comparison** | Multi-line chart | 4 tariff types overlaid |
| **Plant Status** | Stat + Gauge | Latest `plant_status` |
| **Active Power (history)** | Time series | `active_power_mw` |
| **Today's TRA Signals** | Table | `control_signals` today |
| **API Health Score** | Gauge | % success last 24h |
| **Latency by Endpoint** | Bar chart | Avg `response_time_ms` |
| **Recent Alerts** | Logs panel | Errors from `api_health_logs` |

---

## 🔄 Data Flow

```
┌─────────┐    ┌─────────────┐    ┌─────────────┐    ┌────────────┐    ┌─────────┐
│  Mock   │    │   OAuth2    │    │   ETL       │    │ PostgreSQL │    │ Grafana │
│  Server │    │   Token     │    │   Client    │    │            │    │         │
└────┬────┘    └──────┬──────┘    └──────┬──────┘    └─────┬──────┘    └────┬────┘
     │                │                  │                 │                │
     │   1. POST /oauth/token            │                 │                │
     │◀───────────────────────────────────                 │                │
     │                │                  │                 │                │
     │   2. Return access_token (JWT)    │                 │                │
     │────────────────────────────────────▶                │                │
     │                │                  │                 │                │
     │   3. GET /api/v1/energy/prices    │                 │                │
     │      Authorization: Bearer <token>│                 │                │
     │◀───────────────────────────────────                 │                │
     │                │                  │                 │                │
     │   4. Return JSON (prices array)   │                 │                │
     │────────────────────────────────────▶                │                │
     │                │                  │                 │                │
     │                │   5. Pandas: json_normalize()      │                │
     │                │                  │─────────────────▶                │
     │                │                  │                 │                │
     │                │   6. INSERT INTO energy_prices     │                │
     │                │                  │─────────────────▶                │
     │                │                  │                 │                │
     │                │                  │   7. Query data │                │
     │                │                  │                 │◀───────────────│
     │                │                  │                 │                │
     │                │                  │   8. Visualize  │                │
     │                │                  │                 │────────────────▶
     │                │                  │                 │                │
```

---

## 📡 API Endpoints (Mock Server)

### OAuth2 Authentication

#### `POST /oauth/token`
Access token generation via Client Credentials Flow.

**Request:**
```bash
curl -X POST http://localhost:8000/oauth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "username=energy_trading_client" \
  -d "password=super_secret_key_2024"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

---

### Dynamic Prices

#### `GET /api/v1/energy/prices`
Returns energy prices in 15-minute intervals.

**Required headers:**
```
Authorization: Bearer <access_token>
```

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `tariff_type` | string | all | `grid`, `electricity`, `integrated`, `grid_usage` |
| `tariff_name` | string | home_dynamic | `home_dynamic`, `business_dynamic` |
| `start_timestamp` | datetime | today 00:00 | ISO 8601 format |
| `end_timestamp` | datetime | today 23:59 | ISO 8601 format |

**Response:**
```json
{
  "publication_timestamp": "2025-11-12T14:35+02:00",
  "prices": [
    {
      "start_timestamp": "2025-10-08T08:00+02:00",
      "end_timestamp": "2025-10-08T08:15+02:00",
      "grid": [{"unit": "CHF_kWh", "value": 0.1635}],
      "electricity": [{"unit": "CHF_kWh", "value": 0.12}],
      "integrated": [{"unit": "CHF_kWh", "value": 0.2835}],
      "grid_usage": [{"unit": "CHF_kWh", "value": 0.1332}]
    }
  ]
}
```

---

### Power Plant Status

#### `GET /api/v1/plant/live`
Returns real-time status of the Lutersarni power plant.

**Response:**
```json
{
  "timestamp": "2025-12-03T14:40+01:00",
  "operational_status": "running",
  "voltage_kv": 20.697998,
  "active_power_mw": 0.079999998,
  "reactive_power_mvar": -0.02,
  "wind_speed_kmh": 12.959999,
  "units": {
    "current": "A",
    "voltage": "kV",
    "active_power": "MW",
    "reactive_power": "Mvar",
    "wind_speed": "km/h"
  }
}
```

**Field mapping (German → English):**
| German | English | Usage |
|--------|---------|-------|
| `zeitstempel` | timestamp | Reading timestamp |
| `betriebsstatus` | operational_status | "in Betrieb" = running |
| `wirkleistung` | active_power | MW generated |
| `blindleistung` | reactive_power | Mvar (grid quality) |
| `windgeschwindigkeit` | wind_speed | km/h |

---

### Control Signals

#### `GET /api/v1/control/signals/{date}`
Returns TRA (demand-side control) signals for a given date.

**Path Parameters:**
| Param | Type | Example |
|-------|------|---------|
| `date` | date / "last" | `2025-07-08` or `last` |

**Response:**
```json
[
  {
    "name": "000R",
    "description": "Boiler 4 h",
    "date": "2025-07-08",
    "start": "2025-07-08T03:25:00+02:00",
    "end": "2025-07-08T06:56:00+02:00"
  }
]
```

---

### Health Check

#### `GET /health`
Health endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-02-05T17:30:00+01:00",
  "version": "1.0.0",
  "uptime_seconds": 3600
}
```

---

## 📊 Data Model

### ER Diagram

```
┌───────────────────┐       ┌───────────────────┐
│   energy_prices   │       │   plant_status    │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │
│ publication_ts    │       │ plant_id          │
│ start_timestamp   │       │ timestamp         │
│ end_timestamp     │       │ operational_status│
│ tariff_type       │       │ voltage_kv        │
│ unit              │       │ active_power_mw   │
│ value             │       │ reactive_power_mvar│
│ ingested_at       │       │ wind_speed_kmh    │
└───────────────────┘       │ ingested_at       │
                            └───────────────────┘

┌───────────────────┐       ┌───────────────────┐
│  control_signals  │       │  api_health_logs  │
├───────────────────┤       ├───────────────────┤
│ id (PK)           │       │ id (PK)           │
│ signal_name       │       │ endpoint          │
│ description       │       │ status_code       │
│ signal_date       │       │ response_time_ms  │
│ start_timestamp   │       │ success           │
│ end_timestamp     │       │ error_message     │
│ ingested_at       │       │ checked_at        │
└───────────────────┘       └───────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version | Justification |
|-------|------------|---------|---------------|
| **Mock Server** | FastAPI | 0.109+ | Async, autodoc, easy OAuth2 |
| **ETL Client** | Python | 3.11+ | Modern typing, async/await |
| **HTTP Client** | httpx | 0.26+ | Async, HTTP/2 support |
| **Data Processing** | Pandas | 2.0+ | json_normalize, time series |
| **Scheduling** | APScheduler | 3.10+ | Cron-like, in-process |
| **Database** | PostgreSQL | 15+ | Time series, JSONB support |
| **DB Driver** | psycopg | 3.1+ | Async, connection pooling |
| **Visualization** | Grafana | 10.0+ | Alerting, datasources |
| **Containerization** | Docker Compose | 2.20+ | Multi-service orchestration |

---

## 🚀 Installation & Setup

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ (for local development)
- Git

### Quick Start

```bash
# 1. Clone repository
git clone <repo_url>
cd energy-market-integrator

# 2. Start all infrastructure
docker-compose up -d

# 3. Verify services
docker-compose ps

# 4. Access services
# - Mock API: http://localhost:8000/docs
# - Grafana:  http://localhost:3000 (admin/admin)
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Run mock server
uvicorn mock_server.main:app --reload --port 8000

# Run ETL client (in another terminal)
python -m etl_client.main
```

---

## 📈 Grafana Dashboards

### Main Dashboard: "Energy Trading Monitor"

Access: `http://localhost:3000/d/energy-trading-monitor`

**Included panels:**

1. **Energy Prices (15 min)**
   - Time series chart
   - Filter by tariff type
   - Comparison: home_dynamic vs business_dynamic

2. **Lutersarni Plant Status**
   - Operational status indicator (traffic light)
   - Active power gauge (MW)
   - Generation history

3. **TRA Control Signals**
   - Today's signals table
   - Activation timeline

4. **API Health Monitor**
   - Availability score (%)
   - Average latency by endpoint
   - Recent error log

---

## 📁 Project Structure

```
energy-market-integrator/
├── README.md                    # This file
├── docker-compose.yml           # Service orchestration
├── .env.example                 # Environment variables template
│
├── data/                        # CKW specification data
│   └── e-ckw-public-data-1.0.23-raml/
│       ├── e-ckw-public-data.raml
│       ├── examples/
│       │   ├── example_energyprices.json
│       │   ├── example_lutersarni_live.json
│       │   └── example_trasignale.json
│       └── ...
│
├── mock_server/                 # Mock API (FastAPI)
│   ├── __init__.py
│   ├── main.py                  # Main application
│   ├── auth/
│   │   ├── __init__.py
│   │   └── oauth2.py            # OAuth2 logic
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── energy.py            # Energy endpoints
│   │   ├── plant.py             # Plant endpoints
│   │   └── control.py           # Control signal endpoints
│   └── data/
│       └── loader.py            # Example JSON loader
│
├── etl_client/                  # ETL Client (Python)
│   ├── __init__.py
│   ├── main.py                  # Entry point
│   ├── config.py                # Configuration
│   ├── auth/
│   │   ├── __init__.py
│   │   └── token_manager.py     # OAuth2 token management
│   ├── extractors/
│   │   ├── __init__.py
│   │   ├── base.py              # Base extractor
│   │   ├── prices.py            # Price extractor
│   │   ├── plant.py             # Plant extractor
│   │   └── signals.py           # Signal extractor
│   ├── transformers/
│   │   ├── __init__.py
│   │   └── pandas_processor.py  # Pandas normalization
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── postgres.py          # PostgreSQL writer
│   └── health/
│       ├── __init__.py
│       └── checker.py           # Health check & logging
│
├── database/                    # Database scripts
│   ├── init.sql                 # Initial schema
│   └── seed.sql                 # Test data
│
├── grafana/                     # Grafana configuration
│   ├── provisioning/
│   │   ├── dashboards/
│   │   │   ├── dashboard.yml
│   │   │   └── energy-trading-monitor.json
│   │   └── datasources/
│   │       └── postgres.yml
│   └── grafana.ini
│
├── tests/                       # Tests
│   ├── __init__.py
│   ├── test_mock_server.py
│   ├── test_etl_client.py
│   └── test_transformers.py
│
└── requirements.txt             # Python dependencies
```

---

## 📝 Changelog

### v0.2.0 (2025-02-05)
- ✅ Mock Server implemented (FastAPI + OAuth2)
- ✅ All 3 trading endpoints operational
- ✅ Docker infrastructure (PostgreSQL + Grafana)
- ✅ Database schema with 4 tables and 3 views
- 🔲 ETL Client pending
- 🔲 Grafana dashboards pending

### v0.1.0 (2025-02-05)
- ✅ Initial analysis of CKW specification
- ✅ Architecture definition
- ✅ Selection of trading-relevant endpoints

---

## 👤 Author

**Carlos** - Backend Developer & Integration Specialist

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
