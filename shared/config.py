"""Shared configuration for JARVIS services"""
import os
from typing import Optional

class Config:
    POSTGRES_PERSONS_PASSWORD = os.getenv("POSTGRES_PERSONS_PASSWORD")
    POSTGRES_ORG_PASSWORD = os.getenv("POSTGRES_ORG_PASSWORD")
    POSTGRES_MEDICAL_PASSWORD = os.getenv("POSTGRES_MEDICAL_PASSWORD")
    POSTGRES_TRADING_PASSWORD = os.getenv("POSTGRES_TRADING_PASSWORD")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
