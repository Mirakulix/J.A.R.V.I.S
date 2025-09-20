"""
JARVIS Test Configuration
Pytest configuration and shared fixtures for JARVIS test suite
"""

import pytest
import asyncio
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch
import docker
import chromadb
from chromadb.config import Settings

# Test environment setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def docker_client():
    """Docker client for container testing"""
    try:
        client = docker.from_env()
        yield client
    except Exception:
        yield None

@pytest.fixture
def temp_dir():
    """Temporary directory for test files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        "database": {
            "host": "localhost",
            "port": 5432,
            "username": "test_user",
            "password": "test_pass",
            "database": "test_db"
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "password": "test_redis_pass"
        },
        "chroma": {
            "host": "localhost",
            "port": 8000,
            "persist_directory": "/tmp/test_chroma"
        },
        "api_keys": {
            "openai": "test_openai_key",
            "claude": "test_claude_key",
            "bitpanda": "test_bitpanda_key"
        }
    }

@pytest.fixture
def mock_chroma_client():
    """Mock ChromaDB client for testing"""
    with patch('chromadb.Client') as mock_client:
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        
        # Mock collections
        mock_collection = Mock()
        mock_collection.count.return_value = 5
        mock_collection.get.return_value = {
            'ids': ['test1', 'test2'],
            'documents': ['Test doc 1', 'Test doc 2'],
            'metadatas': [{'type': 'test'}, {'type': 'test'}]
        }
        mock_collection.query.return_value = {
            'ids': [['test1']],
            'documents': [['Test doc 1']],
            'distances': [[0.1]]
        }
        
        mock_instance.get_collection.return_value = mock_collection
        mock_instance.create_collection.return_value = mock_collection
        mock_instance.list_collections.return_value = [mock_collection]
        
        yield mock_instance

@pytest.fixture
def mock_database():
    """Mock database connection for testing"""
    with patch('psycopg2.connect') as mock_connect:
        mock_conn = Mock()
        mock_cursor = Mock()
        
        mock_cursor.fetchall.return_value = [
            ('BTC', 45000.0, 1000000),
            ('ETH', 3000.0, 500000)
        ]
        mock_cursor.fetchone.return_value = ('BTC', 45000.0, 1000000)
        
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        yield mock_conn

@pytest.fixture
def sample_skills():
    """Sample skills data for testing"""
    return [
        {
            "name": "weather_api",
            "description": "Get weather information",
            "category": "simple",
            "inputs": {
                "location": {"type": "string", "required": True}
            },
            "outputs": {
                "temperature": {"type": "number"},
                "description": {"type": "string"}
            }
        },
        {
            "name": "crypto_trading",
            "description": "Cryptocurrency trading automation",
            "category": "complex",
            "inputs": {
                "symbol": {"type": "string", "required": True},
                "action": {"type": "string", "enum": ["buy", "sell", "hold"]}
            },
            "outputs": {
                "success": {"type": "boolean"},
                "order_id": {"type": "string"}
            }
        }
    ]

@pytest.fixture
def mock_docker_containers():
    """Mock Docker containers for testing"""
    containers = []
    
    for service in ['jarvis-core', 'jarvis-frontend', 'jarvis-db', 'jarvis-redis']:
        container = Mock()
        container.name = service
        container.status = 'running'
        container.stats.return_value = {
            'cpu_stats': {'cpu_usage': {'total_usage': 1000000}},
            'precpu_stats': {'cpu_usage': {'total_usage': 900000}},
            'memory_stats': {'usage': 104857600}  # 100MB
        }
        containers.append(container)
    
    return containers

@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        'crypto': [
            {
                'symbol': 'BTC',
                'price_usd': 45000.0,
                'volume_24h': 25000000000,
                'market_cap': 850000000000
            },
            {
                'symbol': 'ETH',
                'price_usd': 3000.0,
                'volume_24h': 15000000000,
                'market_cap': 360000000000
            }
        ],
        'stocks': [
            {
                'symbol': 'AAPL',
                'price': 175.0,
                'volume': 85000000,
                'market_cap': 2800000000000
            }
        ]
    }

@pytest.fixture
def mock_ai_responses():
    """Mock AI API responses"""
    return {
        'openai': {
            'choices': [{
                'message': {
                    'content': 'This is a test response from OpenAI'
                }
            }]
        },
        'claude': {
            'content': [{
                'text': 'This is a test response from Claude'
            }]
        }
    }

# Test environment markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as requiring docker"
    )

# Skip tests based on environment
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on environment"""
    if not os.getenv("DOCKER_AVAILABLE"):
        skip_docker = pytest.mark.skip(reason="Docker not available")
        for item in items:
            if "docker" in item.keywords:
                item.add_marker(skip_docker)