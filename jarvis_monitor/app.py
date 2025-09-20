#!/usr/bin/env python3
"""
JARVIS Monitor Application
Prometheus-based monitoring system for JARVIS multi-container environment
"""

import os
import time
import psutil
import docker
from flask import Flask, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('jarvis_http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('jarvis_http_request_duration_seconds', 'HTTP request duration')
SYSTEM_CPU_USAGE = Gauge('jarvis_system_cpu_usage_percent', 'System CPU usage percentage')
SYSTEM_MEMORY_USAGE = Gauge('jarvis_system_memory_usage_percent', 'System memory usage percentage')
SYSTEM_DISK_USAGE = Gauge('jarvis_system_disk_usage_percent', 'System disk usage percentage')
CONTAINER_CPU_USAGE = Gauge('jarvis_container_cpu_usage_percent', 'Container CPU usage', ['container_name'])
CONTAINER_MEMORY_USAGE = Gauge('jarvis_container_memory_usage_bytes', 'Container memory usage', ['container_name'])
CONTAINER_STATUS = Gauge('jarvis_container_status', 'Container status (1=running, 0=stopped)', ['container_name'])

class JarvisMonitor:
    def __init__(self):
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
    
    def collect_system_metrics(self):
        """Collect system-level metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            SYSTEM_CPU_USAGE.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            SYSTEM_MEMORY_USAGE.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            SYSTEM_DISK_USAGE.set(disk_percent)
            
            logger.debug(f"System metrics - CPU: {cpu_percent}%, Memory: {memory.percent}%, Disk: {disk_percent}%")
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def collect_container_metrics(self):
        """Collect Docker container metrics"""
        if not self.docker_client:
            return
            
        try:
            containers = self.docker_client.containers.list(all=True)
            
            for container in containers:
                if container.name.startswith('jarvis-'):
                    # Container status
                    status = 1 if container.status == 'running' else 0
                    CONTAINER_STATUS.labels(container_name=container.name).set(status)
                    
                    if container.status == 'running':
                        try:
                            # Get container stats
                            stats = container.stats(stream=False)
                            
                            # CPU usage calculation
                            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                                       stats['precpu_stats']['cpu_usage']['total_usage']
                            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                          stats['precpu_stats']['system_cpu_usage']
                            
                            if system_delta > 0:
                                cpu_percent = (cpu_delta / system_delta) * \
                                            len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
                                CONTAINER_CPU_USAGE.labels(container_name=container.name).set(cpu_percent)
                            
                            # Memory usage
                            memory_usage = stats['memory_stats']['usage']
                            CONTAINER_MEMORY_USAGE.labels(container_name=container.name).set(memory_usage)
                            
                        except Exception as e:
                            logger.warning(f"Error getting stats for container {container.name}: {e}")
                            
        except Exception as e:
            logger.error(f"Error collecting container metrics: {e}")
    
    def collect_all_metrics(self):
        """Collect all metrics"""
        self.collect_system_metrics()
        self.collect_container_metrics()

# Initialize monitor
monitor = JarvisMonitor()

@app.before_request
def before_request():
    REQUEST_COUNT.labels(method=request.method, endpoint=request.endpoint).inc()

@app.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    with REQUEST_DURATION.time():
        monitor.collect_all_metrics()
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

@app.route('/health')
def health():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0',
        'service': 'jarvis-monitor'
    }

@app.route('/')
def index():
    """Index page with basic info"""
    return {
        'service': 'JARVIS Monitor',
        'version': '1.0.0',
        'endpoints': {
            '/metrics': 'Prometheus metrics',
            '/health': 'Health check',
            '/': 'This page'
        }
    }

if __name__ == '__main__':
    logger.info("Starting JARVIS Monitor service")
    app.run(host='0.0.0.0', port=9090, debug=os.getenv('DEBUG', 'false').lower() == 'true')