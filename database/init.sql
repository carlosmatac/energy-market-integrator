-- Energy Trading Connectivity Monitor - Database Schema
-- ======================================================
-- This script creates all tables required for the system.
-- It runs automatically when PostgreSQL container starts.

-- Enable UUID extension (useful for future enhancements)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===========================================
-- Table: energy_prices
-- ===========================================
-- Stores dynamic energy prices at 15-minute (quarter-hourly) intervals.
-- Each row represents a single tariff type value for a time slot.

CREATE TABLE IF NOT EXISTS energy_prices (
    id SERIAL PRIMARY KEY,
    
    -- When this price data was published by the source
    publication_timestamp TIMESTAMPTZ NOT NULL,
    
    -- Time slot boundaries (15-minute intervals)
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    
    -- Tariff classification
    tariff_type VARCHAR(20) NOT NULL CHECK (tariff_type IN ('grid', 'electricity', 'integrated', 'grid_usage')),
    tariff_name VARCHAR(30) NOT NULL DEFAULT 'home_dynamic',
    
    -- Price data
    unit VARCHAR(10) NOT NULL DEFAULT 'CHF_kWh',
    value DECIMAL(10, 6) NOT NULL,
    
    -- Metadata
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate entries for the same time slot and tariff type
    CONSTRAINT unique_price_slot UNIQUE (start_timestamp, end_timestamp, tariff_type, tariff_name)
);

-- Index for time-based queries (common in Grafana dashboards)
CREATE INDEX IF NOT EXISTS idx_energy_prices_time 
    ON energy_prices (start_timestamp DESC);

-- Index for filtering by tariff type
CREATE INDEX IF NOT EXISTS idx_energy_prices_tariff 
    ON energy_prices (tariff_type, start_timestamp DESC);

COMMENT ON TABLE energy_prices IS 'Dynamic energy prices at quarter-hourly resolution from CKW API';


-- ===========================================
-- Table: plant_status
-- ===========================================
-- Stores real-time telemetry from power plants.
-- Currently configured for the Lutersarni wind plant.

CREATE TABLE IF NOT EXISTS plant_status (
    id SERIAL PRIMARY KEY,
    
    -- Plant identification
    plant_id VARCHAR(50) NOT NULL DEFAULT 'lutersarni',
    
    -- Measurement timestamp from the source
    timestamp TIMESTAMPTZ NOT NULL,
    
    -- Operational state
    operational_status VARCHAR(50) NOT NULL,
    
    -- Electrical measurements
    voltage_kv DECIMAL(10, 6),
    active_power_mw DECIMAL(10, 6),
    reactive_power_mvar DECIMAL(10, 6),
    
    -- Environmental conditions (for wind plants)
    wind_speed_kmh DECIMAL(10, 6),
    
    -- Metadata
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for time-based queries
CREATE INDEX IF NOT EXISTS idx_plant_status_time 
    ON plant_status (timestamp DESC);

-- Index for plant filtering (when multiple plants are added)
CREATE INDEX IF NOT EXISTS idx_plant_status_plant 
    ON plant_status (plant_id, timestamp DESC);

COMMENT ON TABLE plant_status IS 'Real-time telemetry from power plants (SCADA-like data)';


-- ===========================================
-- Table: control_signals
-- ===========================================
-- Stores TRA (Tonfrequenz-Rundsteuer-Anlage) control signals.
-- These are demand-side management signals that activate/deactivate loads.

CREATE TABLE IF NOT EXISTS control_signals (
    id SERIAL PRIMARY KEY,
    
    -- Signal identification
    signal_name VARCHAR(20) NOT NULL,
    description VARCHAR(100),
    
    -- Signal timing
    signal_date DATE NOT NULL,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    
    -- Metadata
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Prevent duplicate signals
    CONSTRAINT unique_control_signal UNIQUE (signal_name, signal_date, start_timestamp)
);

-- Index for date-based queries
CREATE INDEX IF NOT EXISTS idx_control_signals_date 
    ON control_signals (signal_date DESC);

COMMENT ON TABLE control_signals IS 'TRA demand-side control signals for load management';


-- ===========================================
-- Table: api_health_logs
-- ===========================================
-- Stores health check results for all monitored API endpoints.
-- Used for connectivity monitoring and alerting in Grafana.

CREATE TABLE IF NOT EXISTS api_health_logs (
    id SERIAL PRIMARY KEY,
    
    -- Endpoint identification
    endpoint VARCHAR(100) NOT NULL,
    
    -- Response details
    status_code INTEGER,
    response_time_ms INTEGER,
    
    -- Success/failure tracking
    success BOOLEAN NOT NULL,
    error_message TEXT,
    
    -- Timestamp of the health check
    checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for time-based queries (dashboard refresh)
CREATE INDEX IF NOT EXISTS idx_api_health_time 
    ON api_health_logs (checked_at DESC);

-- Index for endpoint filtering
CREATE INDEX IF NOT EXISTS idx_api_health_endpoint 
    ON api_health_logs (endpoint, checked_at DESC);

-- Index for failure analysis
CREATE INDEX IF NOT EXISTS idx_api_health_failures 
    ON api_health_logs (success, checked_at DESC) 
    WHERE success = FALSE;

COMMENT ON TABLE api_health_logs IS 'API connectivity health logs for monitoring and alerting';


-- ===========================================
-- Useful Views for Grafana
-- ===========================================

-- View: Latest price for each tariff type
CREATE OR REPLACE VIEW v_latest_prices AS
SELECT DISTINCT ON (tariff_type)
    tariff_type,
    value,
    unit,
    start_timestamp,
    end_timestamp
FROM energy_prices
ORDER BY tariff_type, start_timestamp DESC;

COMMENT ON VIEW v_latest_prices IS 'Latest price for each tariff type - useful for Grafana stat panels';


-- View: Latest plant status
CREATE OR REPLACE VIEW v_latest_plant_status AS
SELECT DISTINCT ON (plant_id)
    plant_id,
    timestamp,
    operational_status,
    voltage_kv,
    active_power_mw,
    reactive_power_mvar,
    wind_speed_kmh
FROM plant_status
ORDER BY plant_id, timestamp DESC;

COMMENT ON VIEW v_latest_plant_status IS 'Latest status for each plant - useful for Grafana gauges';


-- View: API health summary (last 24 hours)
CREATE OR REPLACE VIEW v_api_health_summary AS
SELECT 
    endpoint,
    COUNT(*) as total_checks,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_checks,
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate,
    ROUND(AVG(response_time_ms), 2) as avg_response_time_ms,
    MAX(checked_at) as last_check
FROM api_health_logs
WHERE checked_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint;

COMMENT ON VIEW v_api_health_summary IS 'API health summary for the last 24 hours';


-- ===========================================
-- Grant permissions (if using separate app user)
-- ===========================================
-- Uncomment if you create a separate application user
-- GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO energy_app_user;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO energy_app_user;


-- ===========================================
-- Confirmation message
-- ===========================================
DO $$
BEGIN
    RAISE NOTICE '✅ Energy Trading database schema created successfully!';
    RAISE NOTICE '   Tables: energy_prices, plant_status, control_signals, api_health_logs';
    RAISE NOTICE '   Views: v_latest_prices, v_latest_plant_status, v_api_health_summary';
END $$;
