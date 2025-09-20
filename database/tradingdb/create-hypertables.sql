-- JARVIS Trading Database - TimescaleDB Hypertables
-- Optimized time-series tables for financial data

-- Create extension for TimescaleDB (if available)
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create main trading tables first
CREATE TABLE IF NOT EXISTS crypto_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price_usd DECIMAL(20,8) NOT NULL,
    volume_24h BIGINT,
    market_cap BIGINT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(15,4) NOT NULL,
    volume BIGINT,
    market_cap BIGINT,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trading_signals (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    signal_type VARCHAR(4) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    prediction DECIMAL(20,8) NOT NULL,
    rsi DECIMAL(5,2),
    ma_20 DECIMAL(20,8),
    ma_50 DECIMAL(20,8),
    validation_score DECIMAL(3,2),
    accuracy_score DECIMAL(3,2),
    signal_score DECIMAL(3,2),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS portfolio_holdings (
    id SERIAL PRIMARY KEY,
    currency VARCHAR(10) NOT NULL UNIQUE,
    available DECIMAL(20,8) NOT NULL DEFAULT 0,
    locked DECIMAL(20,8) NOT NULL DEFAULT 0,
    total DECIMAL(20,8) NOT NULL DEFAULT 0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trading_history (
    id SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL UNIQUE,
    instrument VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    amount DECIMAL(20,8) NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    status VARCHAR(20) NOT NULL,
    executed_at TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    total_value_eur DECIMAL(15,2) NOT NULL,
    breakdown JSONB NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Convert to hypertables (TimescaleDB feature)
-- Note: This will only work if TimescaleDB extension is available
DO $$
BEGIN
    -- Try to create hypertables, ignore errors if TimescaleDB is not available
    BEGIN
        PERFORM create_hypertable('crypto_prices', 'timestamp', if_not_exists => TRUE);
        RAISE NOTICE 'Created hypertable: crypto_prices';
    EXCEPTION 
        WHEN OTHERS THEN
            RAISE NOTICE 'TimescaleDB not available, using regular table for crypto_prices';
    END;
    
    BEGIN
        PERFORM create_hypertable('stock_prices', 'timestamp', if_not_exists => TRUE);
        RAISE NOTICE 'Created hypertable: stock_prices';
    EXCEPTION 
        WHEN OTHERS THEN
            RAISE NOTICE 'TimescaleDB not available, using regular table for stock_prices';
    END;
    
    BEGIN
        PERFORM create_hypertable('trading_signals', 'timestamp', if_not_exists => TRUE);
        RAISE NOTICE 'Created hypertable: trading_signals';
    EXCEPTION 
        WHEN OTHERS THEN
            RAISE NOTICE 'TimescaleDB not available, using regular table for trading_signals';
    END;
    
    BEGIN
        PERFORM create_hypertable('portfolio_snapshots', 'timestamp', if_not_exists => TRUE);
        RAISE NOTICE 'Created hypertable: portfolio_snapshots';
    EXCEPTION 
        WHEN OTHERS THEN
            RAISE NOTICE 'TimescaleDB not available, using regular table for portfolio_snapshots';
    END;
END
$$;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_crypto_prices_symbol_timestamp ON crypto_prices(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_timestamp ON stock_prices(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol_timestamp ON trading_signals(symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_trading_signals_validation ON trading_signals(validation_score) WHERE validation_score IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_trading_history_instrument ON trading_history(instrument, executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_timestamp ON portfolio_snapshots(timestamp DESC);

-- Create materialized view for latest prices
CREATE MATERIALIZED VIEW IF NOT EXISTS latest_crypto_prices AS
SELECT DISTINCT ON (symbol) 
    symbol, 
    price_usd, 
    volume_24h, 
    market_cap, 
    timestamp
FROM crypto_prices
ORDER BY symbol, timestamp DESC;

CREATE MATERIALIZED VIEW IF NOT EXISTS latest_stock_prices AS
SELECT DISTINCT ON (symbol) 
    symbol, 
    price, 
    volume, 
    market_cap, 
    timestamp
FROM stock_prices
ORDER BY symbol, timestamp DESC;

-- Create unique indexes on materialized views
CREATE UNIQUE INDEX IF NOT EXISTS idx_latest_crypto_prices_symbol ON latest_crypto_prices(symbol);
CREATE UNIQUE INDEX IF NOT EXISTS idx_latest_stock_prices_symbol ON latest_stock_prices(symbol);

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_latest_prices()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY latest_crypto_prices;
    REFRESH MATERIALIZED VIEW CONCURRENTLY latest_stock_prices;
END;
$$ LANGUAGE plpgsql;

-- Create function for automatic data retention
CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Keep only 1 year of detailed price data
    DELETE FROM crypto_prices WHERE timestamp < NOW() - INTERVAL '1 year';
    DELETE FROM stock_prices WHERE timestamp < NOW() - INTERVAL '1 year';
    
    -- Keep trading signals for 2 years
    DELETE FROM trading_signals WHERE timestamp < NOW() - INTERVAL '2 years';
    
    -- Keep trading history for 7 years (regulatory requirement)
    DELETE FROM trading_history WHERE executed_at < NOW() - INTERVAL '7 years';
    
    -- Keep portfolio snapshots for 3 years
    DELETE FROM portfolio_snapshots WHERE timestamp < NOW() - INTERVAL '3 years';
    
    -- Refresh materialized views after cleanup
    PERFORM refresh_latest_prices();
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO jarvis_trading;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO jarvis_trading;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO jarvis_readonly;

-- Insert initial sample data for testing
INSERT INTO crypto_prices (symbol, price_usd, volume_24h, market_cap, timestamp) VALUES
('BTC', 45000.00, 25000000000, 850000000000, NOW() - INTERVAL '1 hour'),
('ETH', 3200.00, 15000000000, 380000000000, NOW() - INTERVAL '1 hour'),
('ADA', 1.20, 2000000000, 40000000000, NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

INSERT INTO stock_prices (symbol, price, volume, market_cap, timestamp) VALUES
('AAPL', 175.50, 85000000, 2800000000000, NOW() - INTERVAL '1 hour'),
('GOOGL', 2750.00, 1200000, 1850000000000, NOW() - INTERVAL '1 hour'),
('TSLA', 245.80, 120000000, 780000000000, NOW() - INTERVAL '1 hour')
ON CONFLICT DO NOTHING;

-- Refresh materialized views
SELECT refresh_latest_prices();

-- Log successful initialization
INSERT INTO trading_history (order_id, instrument, side, amount, price, status, executed_at) VALUES
('INIT_001', 'SYSTEM_INIT', 'BUY', 0, 0, 'SYSTEM_INITIALIZED', NOW())
ON CONFLICT DO NOTHING;

RAISE NOTICE 'JARVIS Trading Database hypertables and indexes created successfully!';