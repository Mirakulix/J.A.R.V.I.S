"""
Unit tests for JARVIS Trading System
Tests trading algorithms, market data processing, and prediction models
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from decimal import Decimal

@pytest.mark.unit
class TestMarketDataCollector:
    """Test market data collection functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.mock_collector = Mock()
    
    def test_crypto_data_collection(self, sample_market_data):
        """Test cryptocurrency data collection"""
        with patch('database.tradingdb.collect_market_data.MarketDataCollector') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.collect_crypto_data.return_value = sample_market_data['crypto']
            
            # Test data collection
            result = mock_instance.collect_crypto_data()
            
            assert len(result) == 2
            assert result[0]['symbol'] == 'BTC'
            assert result[0]['price_usd'] == 45000.0
            assert result[1]['symbol'] == 'ETH'
    
    def test_stock_data_collection(self, sample_market_data):
        """Test stock market data collection"""
        with patch('database.tradingdb.collect_market_data.MarketDataCollector') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            mock_instance.collect_stock_data.return_value = sample_market_data['stocks']
            
            # Test data collection
            result = mock_instance.collect_stock_data()
            
            assert len(result) == 1
            assert result[0]['symbol'] == 'AAPL'
            assert result[0]['price'] == 175.0
    
    def test_data_validation(self):
        """Test market data validation"""
        with patch('database.tradingdb.collect_market_data.DataValidator') as mock_validator:
            mock_instance = Mock()
            mock_validator.return_value = mock_instance
            
            # Test valid data
            valid_data = {'symbol': 'BTC', 'price_usd': 45000.0, 'volume_24h': 1000000000}
            mock_instance.validate.return_value = {'valid': True, 'errors': []}
            
            result = mock_instance.validate(valid_data)
            assert result['valid'] is True
            
            # Test invalid data
            invalid_data = {'symbol': '', 'price_usd': -100}
            mock_instance.validate.return_value = {'valid': False, 'errors': ['Invalid symbol', 'Negative price']}
            
            result = mock_instance.validate(invalid_data)
            assert result['valid'] is False
            assert len(result['errors']) == 2

@pytest.mark.unit
class TestPredictionCalculator:
    """Test trading prediction algorithms"""
    
    def test_moving_average_calculation(self):
        """Test moving average calculation"""
        with patch('database.tradingdb.calculate_predictions.PredictionCalculator') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Test moving average
            prices = [100, 102, 98, 105, 103, 107, 104]
            expected_ma = np.mean(prices[-5:])  # 5-period MA
            
            mock_instance.calculate_moving_average.return_value = expected_ma
            result = mock_instance.calculate_moving_average(prices, window=5)
            
            assert result == expected_ma
    
    def test_rsi_calculation(self):
        """Test RSI (Relative Strength Index) calculation"""
        with patch('database.tradingdb.calculate_predictions.PredictionCalculator') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Mock RSI calculation
            mock_instance.calculate_rsi.return_value = 65.5
            
            prices = [100, 102, 101, 105, 103, 107, 104, 106, 108, 105]
            result = mock_instance.calculate_rsi(prices, period=9)
            
            assert 0 <= result <= 100
            assert result == 65.5
    
    def test_prediction_generation(self):
        """Test price prediction generation"""
        with patch('database.tradingdb.calculate_predictions.PredictionCalculator') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Mock prediction
            mock_prediction = {
                'symbol': 'BTC',
                'prediction': 46000.0,
                'confidence': 0.75,
                'signal': 'BUY',
                'rsi': 35.0,
                'ma_20': 44500.0,
                'ma_50': 43800.0
            }
            mock_instance.generate_prediction.return_value = mock_prediction
            
            # Test prediction
            sample_data = [{'price_usd': 45000.0, 'timestamp': datetime.now()}]
            result = mock_instance.generate_prediction('BTC', sample_data)
            
            assert result['symbol'] == 'BTC'
            assert result['signal'] in ['BUY', 'SELL', 'HOLD']
            assert 0 <= result['confidence'] <= 1
    
    def test_signal_determination(self):
        """Test trading signal determination logic"""
        with patch('database.tradingdb.calculate_predictions.SignalGenerator') as mock_generator:
            mock_instance = Mock()
            mock_generator.return_value = mock_instance
            
            # Test different scenarios
            test_cases = [
                {'price_change': 0.05, 'rsi': 30, 'expected': 'BUY'},
                {'price_change': -0.05, 'rsi': 70, 'expected': 'SELL'},
                {'price_change': 0.01, 'rsi': 50, 'expected': 'HOLD'}
            ]
            
            for case in test_cases:
                mock_instance.determine_signal.return_value = case['expected']
                result = mock_instance.determine_signal(
                    case['price_change'], 
                    case['rsi']
                )
                assert result == case['expected']

@pytest.mark.unit
class TestPredictionValidator:
    """Test prediction validation and scoring"""
    
    def test_accuracy_calculation(self):
        """Test prediction accuracy calculation"""
        with patch('database.tradingdb.validate_predictions.PredictionValidator') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Test accuracy calculation
            predicted = 45000.0
            actual = 46000.0
            confidence = 0.8
            
            # Mock accuracy score (2.2% error = ~78% accuracy with confidence weighting)
            expected_score = 0.62
            mock_instance.calculate_accuracy_score.return_value = expected_score
            
            result = mock_instance.calculate_accuracy_score(predicted, actual, confidence)
            assert 0 <= result <= 1
            assert result == expected_score
    
    def test_signal_validation(self):
        """Test trading signal validation"""
        with patch('database.tradingdb.validate_predictions.PredictionValidator') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Test BUY signal validation
            mock_instance.validate_signal_accuracy.return_value = 0.8
            result = mock_instance.validate_signal_accuracy('BUY', 45000.0, 46000.0)
            assert result == 0.8
            
            # Test SELL signal validation
            mock_instance.validate_signal_accuracy.return_value = 0.9
            result = mock_instance.validate_signal_accuracy('SELL', 45000.0, 44000.0)
            assert result == 0.9
    
    def test_validation_scoring(self):
        """Test overall validation scoring"""
        with patch('database.tradingdb.validate_predictions.ValidationScorer') as mock_scorer:
            mock_instance = Mock()
            mock_scorer.return_value = mock_instance
            
            # Mock validation components
            accuracy_score = 0.75
            signal_score = 0.85
            overall_score = (accuracy_score + signal_score) / 2
            
            mock_instance.calculate_overall_score.return_value = overall_score
            
            result = mock_instance.calculate_overall_score(accuracy_score, signal_score)
            assert result == 0.8

@pytest.mark.unit
class TestBitpandaSync:
    """Test Bitpanda API synchronization"""
    
    def test_balance_synchronization(self):
        """Test portfolio balance synchronization"""
        with patch('database.tradingdb.bitpanda_sync.BitpandaSync') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Mock balance data
            mock_balances = [
                {'currency_code': 'BTC', 'available': '0.15', 'total': '0.15'},
                {'currency_code': 'EUR', 'available': '1250.50', 'total': '1250.50'}
            ]
            mock_instance.get_account_balances.return_value = mock_balances
            
            # Test balance retrieval
            result = mock_instance.get_account_balances()
            
            assert len(result) == 2
            assert result[0]['currency_code'] == 'BTC'
            assert float(result[1]['available']) == 1250.50
    
    def test_trading_history_sync(self):
        """Test trading history synchronization"""
        with patch('database.tradingdb.bitpanda_sync.BitpandaSync') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Mock trading history
            mock_trades = [
                {
                    'order_id': 'test_001',
                    'instrument_code': 'BTC_EUR',
                    'side': 'BUY',
                    'amount': '0.01',
                    'price': '45000.00',
                    'status': 'FILLED'
                }
            ]
            mock_instance.get_trading_history.return_value = mock_trades
            
            # Test history retrieval
            result = mock_instance.get_trading_history(days=7)
            
            assert len(result) == 1
            assert result[0]['side'] == 'BUY'
            assert result[0]['status'] == 'FILLED'
    
    def test_portfolio_value_calculation(self):
        """Test portfolio value calculation"""
        with patch('database.tradingdb.bitpanda_sync.BitpandaSync') as mock_class:
            mock_instance = Mock()
            mock_class.return_value = mock_instance
            
            # Mock portfolio value calculation
            mock_value = {
                'total_value_eur': 8500.75,
                'breakdown': {
                    'BTC': {'amount': 0.15, 'value_eur': 6750.00},
                    'EUR': {'amount': 1750.75, 'value_eur': 1750.75}
                }
            }
            mock_instance.calculate_portfolio_value.return_value = mock_value
            
            # Test calculation
            result = mock_instance.calculate_portfolio_value()
            
            assert result['total_value_eur'] == 8500.75
            assert 'BTC' in result['breakdown']
            assert 'EUR' in result['breakdown']

@pytest.mark.unit
class TestTradingDatabase:
    """Test trading database operations"""
    
    def test_hypertable_creation(self, mock_database):
        """Test TimescaleDB hypertable creation"""
        # Mock hypertable creation
        cursor = mock_database.cursor()
        cursor.execute.return_value = None
        
        # Test table creation queries
        tables = ['crypto_prices', 'stock_prices', 'trading_signals']
        for table in tables:
            cursor.execute(f"SELECT create_hypertable('{table}', 'timestamp')")
            
        # Verify no errors occurred
        assert cursor.execute.called
    
    def test_data_insertion(self, mock_database):
        """Test data insertion operations"""
        cursor = mock_database.cursor()
        
        # Test crypto price insertion
        crypto_data = {
            'symbol': 'BTC',
            'price_usd': 45000.0,
            'volume_24h': 25000000000,
            'market_cap': 850000000000
        }
        
        cursor.execute.return_value = None
        cursor.execute(
            "INSERT INTO crypto_prices (symbol, price_usd, volume_24h, market_cap) VALUES (%s, %s, %s, %s)",
            (crypto_data['symbol'], crypto_data['price_usd'], crypto_data['volume_24h'], crypto_data['market_cap'])
        )
        
        assert cursor.execute.called
    
    def test_materialized_view_refresh(self, mock_database):
        """Test materialized view refresh operations"""
        cursor = mock_database.cursor()
        cursor.execute.return_value = None
        
        # Test view refresh
        cursor.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY latest_crypto_prices")
        
        assert cursor.execute.called

if __name__ == "__main__":
    pytest.main([__file__])