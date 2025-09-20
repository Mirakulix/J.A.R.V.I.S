#!/usr/bin/env python3
"""
JARVIS Trading Database - Market Data Collector
Collects real-time market data from various APIs
"""

import os
import sys
import requests
import psycopg2
import json
import time
from datetime import datetime
from typing import Dict, List, Optional

class MarketDataCollector:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'tradingdb',
            'user': 'jarvis_trading',
            'password': os.getenv('POSTGRES_TRADING_PASSWORD', 'default_pass')
        }
        self.alpha_vantage_key = os.getenv('ALPHA_VANTAGE_API_KEY')
        self.bitpanda_key = os.getenv('BITPANDA_API_KEY')
    
    def collect_crypto_data(self) -> List[Dict]:
        """Collect cryptocurrency market data"""
        print("Collecting cryptocurrency data...")
        
        # Mock data for development
        crypto_data = [
            {
                'symbol': 'BTC',
                'price_usd': 45000.50 + (time.time() % 1000),
                'volume_24h': 28500000000,
                'market_cap': 850000000000,
                'timestamp': datetime.now()
            },
            {
                'symbol': 'ETH',
                'price_usd': 3200.75 + (time.time() % 100),
                'volume_24h': 15200000000,
                'market_cap': 385000000000,
                'timestamp': datetime.now()
            }
        ]
        
        return crypto_data
    
    def collect_stock_data(self) -> List[Dict]:
        """Collect stock market data"""
        print("Collecting stock market data...")
        
        # Mock data for development
        stock_data = [
            {
                'symbol': 'AAPL',
                'price': 175.50 + (time.time() % 10),
                'volume': 85000000,
                'market_cap': 2800000000000,
                'timestamp': datetime.now()
            },
            {
                'symbol': 'GOOGL',
                'price': 2750.25 + (time.time() % 50),
                'volume': 1200000,
                'market_cap': 1850000000000,
                'timestamp': datetime.now()
            }
        ]
        
        return stock_data
    
    def store_data(self, data: List[Dict], table: str):
        """Store collected data in database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for item in data:
                if table == 'crypto_prices':
                    cursor.execute("""
                        INSERT INTO crypto_prices (symbol, price_usd, volume_24h, market_cap, timestamp)
                        VALUES (%(symbol)s, %(price_usd)s, %(volume_24h)s, %(market_cap)s, %(timestamp)s)
                    """, item)
                elif table == 'stock_prices':
                    cursor.execute("""
                        INSERT INTO stock_prices (symbol, price, volume, market_cap, timestamp)
                        VALUES (%(symbol)s, %(price)s, %(volume)s, %(market_cap)s, %(timestamp)s)
                    """, item)
            
            conn.commit()
            print(f"Stored {len(data)} records in {table}")
            
        except Exception as e:
            print(f"Error storing data: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def run_collection(self):
        """Run the complete data collection process"""
        print("Starting market data collection...")
        
        try:
            # Collect and store crypto data
            crypto_data = self.collect_crypto_data()
            self.store_data(crypto_data, 'crypto_prices')
            
            # Collect and store stock data
            stock_data = self.collect_stock_data()
            self.store_data(stock_data, 'stock_prices')
            
            print("Market data collection completed successfully")
            
        except Exception as e:
            print(f"Error during collection: {e}")
            sys.exit(1)

if __name__ == "__main__":
    collector = MarketDataCollector()
    collector.run_collection()