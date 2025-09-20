#!/usr/bin/env python3
"""
Android Performance Monitor for JARVIS
Monitors emulator performance and exposes metrics
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Any

import psutil
import subprocess
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Prometheus metrics
cpu_usage = Gauge('android_emulator_cpu_usage_percent', 'CPU usage percentage')
memory_usage = Gauge('android_emulator_memory_usage_percent', 'Memory usage percentage')
battery_level = Gauge('android_emulator_battery_level', 'Battery level percentage')
adb_commands = Counter('android_adb_commands_total', 'Total ADB commands executed')
test_duration = Histogram('android_test_duration_seconds', 'Test execution duration')

class AndroidPerformanceMonitor:
    def __init__(self):
        self.metrics = {}
        self.running = True
    
    async def collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage.set(memory.percent)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free_gb": disk.free / (1024**3)
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {}
    
    async def collect_android_metrics(self) -> Dict[str, Any]:
        """Collect Android emulator specific metrics"""
        try:
            metrics = {}
            
            # Check if emulator is running
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if 'emulator' not in result.stdout:
                return {"emulator_status": "not_running"}
            
            metrics["emulator_status"] = "running"
            adb_commands.inc()
            
            # Battery level
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'dumpsys', 'battery'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'level:' in line:
                            level = int(line.split(':')[1].strip())
                            metrics["battery_level"] = level
                            battery_level.set(level)
                            break
                adb_commands.inc()
            except Exception as e:
                logger.warning(f"Could not get battery level: {e}")
            
            # Memory info
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'cat', '/proc/meminfo'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    meminfo = {}
                    for line in result.stdout.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            if 'kB' in value:
                                meminfo[key.strip()] = int(value.replace('kB', '').strip())
                    
                    if 'MemTotal' in meminfo and 'MemAvailable' in meminfo:
                        total = meminfo['MemTotal']
                        available = meminfo['MemAvailable']
                        used_percent = ((total - available) / total) * 100
                        metrics["android_memory_percent"] = used_percent
                        metrics["android_memory_total_mb"] = total / 1024
                        metrics["android_memory_available_mb"] = available / 1024
                adb_commands.inc()
            except Exception as e:
                logger.warning(f"Could not get memory info: {e}")
            
            # CPU info
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'cat', '/proc/stat'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    cpu_line = result.stdout.split('\n')[0]
                    if cpu_line.startswith('cpu '):
                        values = [int(x) for x in cpu_line.split()[1:8]]
                        total = sum(values)
                        idle = values[3]
                        used_percent = ((total - idle) / total) * 100 if total > 0 else 0
                        metrics["android_cpu_percent"] = used_percent
                adb_commands.inc()
            except Exception as e:
                logger.warning(f"Could not get CPU info: {e}")
            
            # Storage info
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'df', '/data'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 2:
                        data_line = lines[1].split()
                        if len(data_line) >= 6:
                            total = int(data_line[1])
                            used = int(data_line[2])
                            available = int(data_line[3])
                            used_percent = (used / total) * 100 if total > 0 else 0
                            
                            metrics["android_storage_total_mb"] = total / 1024
                            metrics["android_storage_used_mb"] = used / 1024
                            metrics["android_storage_available_mb"] = available / 1024
                            metrics["android_storage_percent"] = used_percent
                adb_commands.inc()
            except Exception as e:
                logger.warning(f"Could not get storage info: {e}")
            
            # Network stats
            try:
                result = subprocess.run(
                    ['adb', 'shell', 'cat', '/proc/net/dev'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    network_stats = {}
                    for line in result.stdout.split('\n')[2:]:  # Skip headers
                        if ':' in line:
                            parts = line.split(':')
                            if len(parts) == 2:
                                interface = parts[0].strip()
                                stats = parts[1].split()
                                if len(stats) >= 16 and interface != 'lo':
                                    network_stats[interface] = {
                                        "rx_bytes": int(stats[0]),
                                        "tx_bytes": int(stats[8])
                                    }
                    metrics["network_stats"] = network_stats
                adb_commands.inc()
            except Exception as e:
                logger.warning(f"Could not get network stats: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting Android metrics: {e}")
            return {}
    
    async def collect_app_metrics(self) -> Dict[str, Any]:
        """Collect metrics for running apps"""
        try:
            metrics = {}
            
            # List running packages
            result = subprocess.run(
                ['adb', 'shell', 'ps', '-A'],
                capture_output=True, text=True, timeout=15
            )
            
            if result.returncode == 0:
                running_apps = []
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 9:
                            app_name = parts[8]
                            if not app_name.startswith('[') and '.' in app_name:
                                running_apps.append(app_name)
                
                metrics["running_apps_count"] = len(running_apps)
                metrics["running_apps"] = running_apps[:10]  # Limit to first 10
            
            adb_commands.inc()
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting app metrics: {e}")
            return {}
    
    async def save_metrics(self, metrics: Dict[str, Any]):
        """Save metrics to file"""
        try:
            metrics["timestamp"] = datetime.now().isoformat()
            
            # Save to JSON file
            with open("/app/logs/metrics.json", "w") as f:
                json.dump(metrics, f, indent=2)
            
            # Append to metrics log
            with open("/app/logs/metrics.log", "a") as f:
                f.write(f"{datetime.now().isoformat()} {json.dumps(metrics)}\n")
                
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
    
    async def monitoring_loop(self):
        """Main monitoring loop"""
        logger.info("Starting Android performance monitoring")
        
        while self.running:
            try:
                # Collect all metrics
                system_metrics = await self.collect_system_metrics()
                android_metrics = await self.collect_android_metrics()
                app_metrics = await self.collect_app_metrics()
                
                # Combine metrics
                all_metrics = {
                    "system": system_metrics,
                    "android": android_metrics,
                    "apps": app_metrics
                }
                
                # Save metrics
                await self.save_metrics(all_metrics)
                self.metrics = all_metrics
                
                # Log summary
                if android_metrics.get("emulator_status") == "running":
                    logger.info(
                        f"Metrics - CPU: {system_metrics.get('cpu_percent', 0):.1f}%, "
                        f"Memory: {system_metrics.get('memory_percent', 0):.1f}%, "
                        f"Battery: {android_metrics.get('battery_level', 0)}%, "
                        f"Apps: {app_metrics.get('running_apps_count', 0)}"
                    )
                else:
                    logger.info("Emulator not running")
                
                # Wait before next collection
                await asyncio.sleep(30)  # Collect metrics every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    def stop(self):
        """Stop monitoring"""
        self.running = False

async def main():
    """Main function"""
    # Start Prometheus metrics server
    start_http_server(9090)
    logger.info("Prometheus metrics server started on port 9090")
    
    # Create and start monitor
    monitor = AndroidPerformanceMonitor()
    
    try:
        await monitor.monitoring_loop()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring error: {e}")
    finally:
        monitor.stop()

if __name__ == "__main__":
    asyncio.run(main())