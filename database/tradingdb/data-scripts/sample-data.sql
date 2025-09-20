-- Sample trading data for development and testing
-- JARVIS Trading Database Sample Data

-- Sample cryptocurrency data
INSERT INTO crypto_prices (symbol, price_usd, volume_24h, market_cap, timestamp) VALUES
('BTC', 45000.50, 28500000000, 850000000000, NOW()),
('ETH', 3200.75, 15200000000, 385000000000, NOW()),
('ADA', 1.25, 2100000000, 42000000000, NOW());

-- Sample stock data
INSERT INTO stock_prices (symbol, price, volume, market_cap, timestamp) VALUES
('AAPL', 175.50, 85000000, 2800000000000, NOW()),
('GOOGL', 2750.25, 1200000, 1850000000000, NOW()),
('TSLA', 245.80, 120000000, 780000000000, NOW());

-- Sample trading signals
INSERT INTO trading_signals (symbol, signal_type, confidence, prediction, timestamp) VALUES
('BTC', 'BUY', 0.85, 47500.00, NOW()),
('ETH', 'HOLD', 0.72, 3250.00, NOW()),
('AAPL', 'SELL', 0.68, 172.00, NOW());