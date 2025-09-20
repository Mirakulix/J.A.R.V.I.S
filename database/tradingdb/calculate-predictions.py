#!/usr/bin/env python3
"""
JARVIS Trading Database - Prediction Calculator
AI-powered price prediction and trading signal generation
"""

import os
import sys
import psycopg2
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

class PredictionCalculator:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'tradingdb',
            'user': 'jarvis_trading',
            'password': os.getenv('POSTGRES_TRADING_PASSWORD', 'default_pass')
        }
    
    def get_historical_data(self, symbol: str, table: str, days: int = 30) -> List[Dict]:
        """Retrieve historical price data for analysis"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            query = f"""
                SELECT * FROM {table}
                WHERE symbol = %s AND timestamp >= %s
                ORDER BY timestamp ASC
            """
            
            since_date = datetime.now() - timedelta(days=days)
            cursor.execute(query, (symbol, since_date))
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            print(f"Error retrieving data for {symbol}: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def calculate_moving_average(self, prices: List[float], window: int = 20) -> float:
        """Calculate simple moving average"""
        if len(prices) < window:
            return np.mean(prices) if prices else 0
        return np.mean(prices[-window:])
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index"""
        if len(prices) < period + 1:
            return 50.0  # Neutral RSI
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_prediction(self, symbol: str, data: List[Dict]) -> Dict:
        """Generate AI-powered price prediction"""
        if not data:
            return {
                'symbol': symbol,
                'prediction': 0.0,
                'confidence': 0.0,
                'signal': 'HOLD'
            }
        
        # Extract prices
        if 'price_usd' in data[0]:
            prices = [item['price_usd'] for item in data]
        else:
            prices = [item['price'] for item in data]
        
        current_price = prices[-1]
        
        # Calculate technical indicators
        ma_20 = self.calculate_moving_average(prices, 20)
        ma_50 = self.calculate_moving_average(prices, 50)
        rsi = self.calculate_rsi(prices)
        
        # Simple prediction algorithm
        trend_factor = 1.0
        if ma_20 > ma_50:
            trend_factor = 1.02  # Uptrend
        elif ma_20 < ma_50:
            trend_factor = 0.98  # Downtrend
        
        # RSI influence
        rsi_factor = 1.0
        if rsi > 70:
            rsi_factor = 0.99  # Overbought
        elif rsi < 30:
            rsi_factor = 1.01  # Oversold
        
        # Calculate prediction
        predicted_price = current_price * trend_factor * rsi_factor
        
        # Determine signal
        price_change = (predicted_price - current_price) / current_price
        if price_change > 0.02:
            signal = 'BUY'
            confidence = min(0.9, 0.5 + abs(price_change) * 10)
        elif price_change < -0.02:
            signal = 'SELL'
            confidence = min(0.9, 0.5 + abs(price_change) * 10)
        else:
            signal = 'HOLD'
            confidence = 0.6
        
        return {
            'symbol': symbol,
            'prediction': predicted_price,
            'confidence': confidence,
            'signal': signal,
            'rsi': rsi,
            'ma_20': ma_20,
            'ma_50': ma_50
        }
    
    def store_prediction(self, prediction: Dict):
        """Store prediction in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trading_signals (symbol, signal_type, confidence, prediction, rsi, ma_20, ma_50, timestamp)
                VALUES (%(symbol)s, %(signal)s, %(confidence)s, %(prediction)s, %(rsi)s, %(ma_20)s, %(ma_50)s, %s)
            """, {
                **prediction,
                'signal': prediction['signal'],
                'timestamp': datetime.now()
            })
            
            conn.commit()
            print(f"Stored prediction for {prediction['symbol']}: {prediction['signal']} @ {prediction['prediction']:.2f}")
            
        except Exception as e:
            print(f"Error storing prediction: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def run_predictions(self):
        """Run predictions for all tracked symbols"""
        print("Calculating trading predictions...")
        
        symbols = [
            ('BTC', 'crypto_prices'),
            ('ETH', 'crypto_prices'),
            ('AAPL', 'stock_prices'),
            ('GOOGL', 'stock_prices'),
            ('TSLA', 'stock_prices')
        ]
        
        for symbol, table in symbols:
            try:
                print(f"Processing {symbol}...")
                
                # Get historical data
                data = self.get_historical_data(symbol, table)
                
                # Generate prediction
                prediction = self.generate_prediction(symbol, data)
                
                # Store prediction
                self.store_prediction(prediction)
                
            except Exception as e:
                print(f"Error processing {symbol}: {e}")
        
        print("Prediction calculations completed")

if __name__ == "__main__":
    calculator = PredictionCalculator()
    calculator.run_predictions()