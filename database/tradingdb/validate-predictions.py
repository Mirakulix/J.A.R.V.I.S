#!/usr/bin/env python3
"""
JARVIS Trading Database - Prediction Validator
Validates and scores the accuracy of trading predictions
"""

import os
import sys
import psycopg2
from datetime import datetime, timedelta
from typing import Dict, List

class PredictionValidator:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'database': 'tradingdb',
            'user': 'jarvis_trading',
            'password': os.getenv('POSTGRES_TRADING_PASSWORD', 'default_pass')
        }
    
    def get_predictions_to_validate(self) -> List[Dict]:
        """Get predictions that are ready for validation"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Get predictions from 24 hours ago that haven't been validated
            cursor.execute("""
                SELECT id, symbol, signal_type, confidence, prediction, timestamp
                FROM trading_signals
                WHERE timestamp BETWEEN %s AND %s
                AND validation_score IS NULL
            """, (
                datetime.now() - timedelta(hours=25),
                datetime.now() - timedelta(hours=23)
            ))
            
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            print(f"Error retrieving predictions: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_actual_price(self, symbol: str, timestamp: datetime) -> float:
        """Get actual price at a specific time"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Try crypto table first
            cursor.execute("""
                SELECT price_usd FROM crypto_prices
                WHERE symbol = %s AND timestamp >= %s
                ORDER BY timestamp ASC LIMIT 1
            """, (symbol, timestamp + timedelta(hours=24)))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            # Try stock table
            cursor.execute("""
                SELECT price FROM stock_prices
                WHERE symbol = %s AND timestamp >= %s
                ORDER BY timestamp ASC LIMIT 1
            """, (symbol, timestamp + timedelta(hours=24)))
            
            result = cursor.fetchone()
            if result:
                return result[0]
            
            return None
            
        except Exception as e:
            print(f"Error getting actual price for {symbol}: {e}")
            return None
        finally:
            if 'conn' in locals():
                conn.close()
    
    def calculate_accuracy_score(self, predicted: float, actual: float, confidence: float) -> float:
        """Calculate accuracy score for a prediction"""
        if actual == 0:
            return 0.0
        
        # Calculate percentage error
        error = abs(predicted - actual) / actual
        
        # Convert to accuracy (inverse of error)
        base_accuracy = max(0, 1 - (error / 0.1))  # 10% error = 0 accuracy
        
        # Weight by confidence
        weighted_accuracy = base_accuracy * confidence
        
        return min(1.0, weighted_accuracy)
    
    def validate_signal_accuracy(self, signal: str, predicted: float, actual: float) -> float:
        """Validate trading signal accuracy"""
        price_change = (actual - predicted) / predicted if predicted > 0 else 0
        
        if signal == 'BUY':
            # Good if price went up
            return max(0, min(1, price_change * 10 + 0.5))
        elif signal == 'SELL':
            # Good if price went down
            return max(0, min(1, -price_change * 10 + 0.5))
        else:  # HOLD
            # Good if price stayed relatively stable
            stability = 1 - abs(price_change) * 5
            return max(0, min(1, stability))
    
    def update_validation_score(self, prediction_id: int, accuracy_score: float, signal_score: float):
        """Update prediction with validation scores"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            overall_score = (accuracy_score + signal_score) / 2
            
            cursor.execute("""
                UPDATE trading_signals
                SET validation_score = %s,
                    accuracy_score = %s,
                    signal_score = %s,
                    validated_at = %s
                WHERE id = %s
            """, (overall_score, accuracy_score, signal_score, datetime.now(), prediction_id))
            
            conn.commit()
            
        except Exception as e:
            print(f"Error updating validation score: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
    
    def run_validation(self):
        """Run validation for all pending predictions"""
        print("Validating trading predictions...")
        
        predictions = self.get_predictions_to_validate()
        
        if not predictions:
            print("No predictions to validate")
            return
        
        validated_count = 0
        total_accuracy = 0
        total_signal_score = 0
        
        for prediction in predictions:
            try:
                symbol = prediction['symbol']
                predicted_price = prediction['prediction']
                signal = prediction['signal_type']
                confidence = prediction['confidence']
                timestamp = prediction['timestamp']
                
                # Get actual price
                actual_price = self.get_actual_price(symbol, timestamp)
                
                if actual_price is None:
                    print(f"No actual price found for {symbol} at {timestamp}")
                    continue
                
                # Calculate scores
                accuracy_score = self.calculate_accuracy_score(predicted_price, actual_price, confidence)
                signal_score = self.validate_signal_accuracy(signal, predicted_price, actual_price)
                
                # Update database
                self.update_validation_score(prediction['id'], accuracy_score, signal_score)
                
                print(f"Validated {symbol}: Accuracy={accuracy_score:.2f}, Signal={signal_score:.2f}")
                
                validated_count += 1
                total_accuracy += accuracy_score
                total_signal_score += signal_score
                
            except Exception as e:
                print(f"Error validating prediction {prediction['id']}: {e}")
        
        if validated_count > 0:
            avg_accuracy = total_accuracy / validated_count
            avg_signal = total_signal_score / validated_count
            print(f"\nValidation Summary:")
            print(f"Predictions validated: {validated_count}")
            print(f"Average accuracy: {avg_accuracy:.2f}")
            print(f"Average signal score: {avg_signal:.2f}")
        
        print("Prediction validation completed")

if __name__ == "__main__":
    validator = PredictionValidator()
    validator.run_validation()