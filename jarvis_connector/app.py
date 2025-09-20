#!/usr/bin/env python3
"""JARVIS Connector Service"""
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    logger.info("JARVIS Connector Service starting...")
    
    try:
        # Keep the service running
        while True:
            logger.info("JARVIS Connector Service running")
            time.sleep(30)  # Wait 30 seconds before next log
    except KeyboardInterrupt:
        logger.info("JARVIS Connector Service stopping...")
    except Exception as e:
        logger.error(f"JARVIS Connector Service error: {e}")
        raise

if __name__ == "__main__":
    main()
