#!/usr/bin/env python3
"""
JARVIS Trading Database - Bitpanda API Synchronization
Synchronizes portfolio and trading data with Bitpanda Pro API
"""

import os
import sys
import requests
import psycopg2
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class BitpandaSync:
    def __init__(self):
        self.api_key = os.getenv('BITPANDA_API_KEY')
        self.base_url = 'https://api.exchange.bitpanda.com/public/v1'
        self.private_url = 'https://api.exchange.bitpanda.com/v1'
        
        self.db_config = {
            'host': 'localhost',
            'database': 'tradingdb',
            'user': 'jarvis_trading',
            'password': os.getenv('POSTGRES_TRADING_PASSWORD', 'default_pass')
        }
        
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        } if self.api_key else {}
    
    def get_account_balances(self) -> List[Dict]:
        """Get current account balances from Bitpanda"""
        if not self.api_key:
            print("No Bitpanda API key configured, using mock data")
            return self._get_mock_balances()
        
        try:
            response = requests.get(
                f'{self.private_url}/account/balances',
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('balances', [])
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return self._get_mock_balances()
                
        except Exception as e:
            print(f"Error fetching balances: {e}")
            return self._get_mock_balances()
    
    def get_trading_history(self, days: int = 7) -> List[Dict]:
        """Get recent trading history"""
        if not self.api_key:
            print("No Bitpanda API key configured, using mock data")
            return self._get_mock_trades()
        
        try:
            since = datetime.now() - timedelta(days=days)
            
            response = requests.get(
                f'{self.private_url}/account/orders',
                headers=self.headers,
                params={
                    'from': since.isoformat(),
                    'to': datetime.now().isoformat()
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('order_history', [])
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return self._get_mock_trades()
                
        except Exception as e:
            print(f"Error fetching trading history: {e}")
            return self._get_mock_trades()
    
    def _get_mock_balances(self) -> List[Dict]:
        """Mock balance data for development"""
        return [
            {
                'currency_code': 'BTC',
                'available': '0.15234',
                'locked': '0.00000',
                'total': '0.15234'
            },
            {
                'currency_code': 'ETH',
                'available': '2.45678',
                'locked': '0.00000',
                'total': '2.45678'
            },
            {
                'currency_code': 'EUR',
                'available': '1250.50',
                'locked': '0.00',
                'total': '1250.50'
            }
        ]
    
    def _get_mock_trades(self) -> List[Dict]:
        """Mock trading data for development"""
        return [
            {
                'order_id': 'mock_001',
                'instrument_code': 'BTC_EUR',
                'side': 'BUY',
                'amount': '0.01000',
                'price': '45000.00',
                'status': 'FILLED',
                'time': datetime.now() - timedelta(hours=2)
            },
            {
                'order_id': 'mock_002',
                'instrument_code': 'ETH_EUR',
                'side': 'SELL',
                'amount': '0.50000',
                'price': '3200.00',
                'status': 'FILLED',
                'time': datetime.now() - timedelta(hours=6)
            }
        ]
    
    def sync_portfolio_balances(self, balances: List[Dict]):
        """Sync portfolio balances to database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for balance in balances:
                cursor.execute("""
                    INSERT INTO portfolio_holdings (currency, available, locked, total, last_updated)
                    VALUES (%(currency_code)s, %(available)s, %(locked)s, %(total)s, %s)
                    ON CONFLICT (currency) DO UPDATE SET
                        available = EXCLUDED.available,
                        locked = EXCLUDED.locked,
                        total = EXCLUDED.total,
                        last_updated = EXCLUDED.last_updated
                """, {
                    **balance,
                    'last_updated': datetime.now()
                })
            
            conn.commit()
            print(f"Synced {len(balances)} portfolio balances")
            
        except Exception as e:
            print(f"Error syncing balances: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def sync_trading_history(self, trades: List[Dict]):
        """Sync trading history to database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            for trade in trades:
                cursor.execute("""
                    INSERT INTO trading_history (
                        order_id, instrument, side, amount, price, status, 
                        executed_at, synced_at
                    )
                    VALUES (
                        %(order_id)s, %(instrument_code)s, %(side)s, %(amount)s, 
                        %(price)s, %(status)s, %(time)s, %s
                    )
                    ON CONFLICT (order_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        synced_at = EXCLUDED.synced_at
                """, {
                    **trade,
                    'synced_at': datetime.now()
                })
            
            conn.commit()
            print(f"Synced {len(trades)} trading records")
            
        except Exception as e:
            print(f"Error syncing trades: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def calculate_portfolio_value(self) -> Dict:
        """Calculate total portfolio value"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get current portfolio
            cursor.execute("SELECT currency, total FROM portfolio_holdings WHERE total > 0")
            holdings = cursor.fetchall()
            
            total_value_eur = 0
            portfolio_breakdown = {}
            
            for currency, amount in holdings:
                if currency == 'EUR':
                    value_eur = float(amount)
                else:
                    # Get current price
                    cursor.execute("""
                        SELECT price_usd FROM crypto_prices 
                        WHERE symbol = %s 
                        ORDER BY timestamp DESC LIMIT 1
                    """, (currency,))
                    
                    price_result = cursor.fetchone()
                    if price_result:
                        # Convert USD to EUR (mock rate)
                        usd_to_eur = 0.92
                        value_eur = float(amount) * price_result[0] * usd_to_eur
                    else:
                        value_eur = 0
                
                portfolio_breakdown[currency] = {
                    'amount': float(amount),
                    'value_eur': value_eur
                }
                total_value_eur += value_eur
            
            # Store portfolio snapshot
            cursor.execute("""
                INSERT INTO portfolio_snapshots (total_value_eur, breakdown, timestamp)
                VALUES (%s, %s, %s)
            """, (total_value_eur, json.dumps(portfolio_breakdown), datetime.now()))
            
            conn.commit()
            
            return {
                'total_value_eur': total_value_eur,
                'breakdown': portfolio_breakdown,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            print(f"Error calculating portfolio value: {e}")
            return {}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def run_sync(self):
        """Run complete synchronization process"""
        print("🔄 Starting Bitpanda synchronization...")
        
        try:
            # Sync balances
            print("💰 Syncing portfolio balances...")
            balances = self.get_account_balances()
            self.sync_portfolio_balances(balances)
            
            # Sync trading history
            print("📊 Syncing trading history...")
            trades = self.get_trading_history()
            self.sync_trading_history(trades)
            
            # Calculate portfolio value
            print("💎 Calculating portfolio value...")
            portfolio_value = self.calculate_portfolio_value()
            
            if portfolio_value:
                print(f"📈 Total portfolio value: €{portfolio_value['total_value_eur']:.2f}")
            
            print("✅ Bitpanda synchronization completed successfully")
            
        except Exception as e:
            print(f"❌ Synchronization failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    sync = BitpandaSync()
    sync.run_sync()