#!/usr/bin/env python3
"""
Android Automation API Server for JARVIS
Provides REST API for Android emulator automation and testing
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import psutil
from appium import webdriver
from appium.options.android import UiAutomator2Options
import adb_shell

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/automation-api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="JARVIS Android Automation API",
    description="API for Android emulator automation and testing",
    version="1.0.0"
)

# Data Models
class EmulatorConfig(BaseModel):
    device_name: str = "test_device"
    api_level: int = 33
    ram_size: int = 4096
    storage_size: int = 8192
    gpu_acceleration: bool = True

class AppConfig(BaseModel):
    app_path: Optional[str] = None
    app_package: Optional[str] = None
    app_activity: Optional[str] = None
    install_timeout: int = 120
    grant_permissions: bool = True

class AutomationConfig(BaseModel):
    test_framework: str = "appium"
    implicit_wait: int = 10
    explicit_wait: int = 30
    screenshot_on_failure: bool = True
    video_recording: bool = False

class TestRequest(BaseModel):
    action: str
    emulator_config: Optional[EmulatorConfig] = None
    app_config: Optional[AppConfig] = None
    automation_config: Optional[AutomationConfig] = None

# Global variables
emulator_driver = None
emulator_status = {
    "status": "stopped",
    "device_id": None,
    "start_time": None,
    "last_health_check": None
}

class AndroidAutomationService:
    def __init__(self):
        self.driver = None
        self.adb_device = None
        self.test_results = []
        self.performance_metrics = {}
        
    async def start_emulator(self, config: EmulatorConfig) -> Dict:
        """Start Android emulator with specified configuration"""
        try:
            logger.info(f"Starting emulator: {config.device_name}")
            
            # Check if emulator is already running
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if 'emulator' in result.stdout:
                logger.info("Emulator already running")
                emulator_status["status"] = "running"
                return {"status": "success", "message": "Emulator already running"}
            
            # Start emulator (handled by supervisor, just verify)
            await asyncio.sleep(5)  # Wait for startup
            
            # Verify emulator is running
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            if 'emulator' in result.stdout:
                emulator_status.update({
                    "status": "running",
                    "device_id": "emulator-5554",
                    "start_time": datetime.now().isoformat(),
                    "last_health_check": datetime.now().isoformat()
                })
                return {"status": "success", "message": "Emulator started successfully"}
            else:
                raise Exception("Failed to start emulator")
                
        except Exception as e:
            logger.error(f"Error starting emulator: {str(e)}")
            emulator_status["status"] = "error"
            return {"status": "error", "message": str(e)}
    
    async def install_app(self, config: AppConfig) -> Dict:
        """Install APK on emulator"""
        try:
            if not config.app_path:
                raise ValueError("app_path is required")
            
            logger.info(f"Installing app: {config.app_path}")
            
            # Install APK
            result = subprocess.run(
                ['adb', 'install', '-r', config.app_path],
                capture_output=True,
                text=True,
                timeout=config.install_timeout
            )
            
            if result.returncode == 0:
                # Grant permissions if requested
                if config.grant_permissions and config.app_package:
                    await self._grant_permissions(config.app_package)
                
                return {
                    "status": "success",
                    "message": "App installed successfully",
                    "package": config.app_package
                }
            else:
                raise Exception(f"Installation failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Error installing app: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def start_automation(self, config: AutomationConfig) -> Dict:
        """Start Appium automation session"""
        try:
            logger.info("Starting automation session")
            
            # Appium capabilities
            options = UiAutomator2Options()
            options.platform_name = "Android"
            options.automation_name = "UiAutomator2"
            options.device_name = "emulator-5554"
            options.new_command_timeout = config.explicit_wait
            
            # Connect to Appium server
            self.driver = webdriver.Remote(
                command_executor='http://localhost:4723',
                options=options
            )
            
            # Set implicit wait
            self.driver.implicitly_wait(config.implicit_wait)
            
            return {
                "status": "success",
                "message": "Automation session started",
                "session_id": self.driver.session_id
            }
            
        except Exception as e:
            logger.error(f"Error starting automation: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def run_test_suite(self, test_config: Dict) -> Dict:
        """Run automated test suite"""
        try:
            logger.info("Running test suite")
            
            if not self.driver:
                raise Exception("Automation session not started")
            
            # Basic test example
            test_results = {
                "suite_id": f"test_{int(time.time())}",
                "start_time": datetime.now().isoformat(),
                "tests": []
            }
            
            # Example: Take screenshot
            screenshot_path = f"/app/screenshots/test_{int(time.time())}.png"
            self.driver.save_screenshot(screenshot_path)
            
            test_results["tests"].append({
                "name": "screenshot_test",
                "status": "passed",
                "screenshot": screenshot_path
            })
            
            test_results["end_time"] = datetime.now().isoformat()
            test_results["total_tests"] = len(test_results["tests"])
            test_results["passed_tests"] = sum(1 for t in test_results["tests"] if t["status"] == "passed")
            
            self.test_results.append(test_results)
            
            return {
                "status": "success",
                "results": test_results
            }
            
        except Exception as e:
            logger.error(f"Error running tests: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def get_performance_metrics(self) -> Dict:
        """Get system and emulator performance metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # ADB device metrics (if available)
            adb_metrics = {}
            try:
                # Battery level
                result = subprocess.run(['adb', 'shell', 'dumpsys', 'battery'], 
                                      capture_output=True, text=True)
                if 'level:' in result.stdout:
                    for line in result.stdout.split('\n'):
                        if 'level:' in line:
                            adb_metrics['battery_level'] = int(line.split(':')[1].strip())
                            break
                
                # Memory info
                result = subprocess.run(['adb', 'shell', 'dumpsys', 'meminfo'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    adb_metrics['memory_info'] = "available"
                    
            except Exception as e:
                logger.warning(f"Could not get ADB metrics: {e}")
            
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available": memory.available,
                    "disk_percent": (disk.used / disk.total) * 100,
                    "disk_free": disk.free
                },
                "emulator": adb_metrics,
                "status": emulator_status
            }
            
            self.performance_metrics = metrics
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _grant_permissions(self, package_name: str):
        """Grant common permissions to app"""
        permissions = [
            'android.permission.CAMERA',
            'android.permission.RECORD_AUDIO',
            'android.permission.ACCESS_FINE_LOCATION',
            'android.permission.ACCESS_COARSE_LOCATION',
            'android.permission.READ_EXTERNAL_STORAGE',
            'android.permission.WRITE_EXTERNAL_STORAGE'
        ]
        
        for permission in permissions:
            try:
                subprocess.run([
                    'adb', 'shell', 'pm', 'grant', package_name, permission
                ], capture_output=True, check=False)
            except Exception:
                pass  # Permission might not be needed or already granted

# Global service instance
automation_service = AndroidAutomationService()

# API Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status")
async def get_status():
    """Get emulator and service status"""
    return {
        "emulator": emulator_status,
        "service": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/emulator/start")
async def start_emulator(config: EmulatorConfig):
    """Start Android emulator"""
    result = await automation_service.start_emulator(config)
    return JSONResponse(content=result)

@app.post("/app/install")
async def install_app(config: AppConfig):
    """Install APK on emulator"""
    result = await automation_service.install_app(config)
    return JSONResponse(content=result)

@app.post("/automation/start")
async def start_automation(config: AutomationConfig):
    """Start automation session"""
    result = await automation_service.start_automation(config)
    return JSONResponse(content=result)

@app.post("/tests/run")
async def run_tests(test_config: Dict):
    """Run test suite"""
    result = await automation_service.run_test_suite(test_config)
    return JSONResponse(content=result)

@app.get("/metrics")
async def get_metrics():
    """Get performance metrics"""
    result = await automation_service.get_performance_metrics()
    return JSONResponse(content=result)

@app.get("/tests/results")
async def get_test_results():
    """Get test results"""
    return {
        "results": automation_service.test_results,
        "count": len(automation_service.test_results)
    }

@app.post("/execute")
async def execute_automation(request: TestRequest):
    """Main automation execution endpoint"""
    try:
        results = {"action": request.action, "results": []}
        
        if request.action == "create_emulator":
            if request.emulator_config:
                result = await automation_service.start_emulator(request.emulator_config)
                results["results"].append(result)
        
        elif request.action == "app_installation":
            if request.app_config:
                result = await automation_service.install_app(request.app_config)
                results["results"].append(result)
        
        elif request.action == "start_automation":
            if request.automation_config:
                result = await automation_service.start_automation(request.automation_config)
                results["results"].append(result)
        
        elif request.action == "run_test_suite":
            result = await automation_service.run_test_suite({})
            results["results"].append(result)
        
        elif request.action == "performance_monitoring":
            result = await automation_service.get_performance_metrics()
            results["results"].append(result)
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
        
        return JSONResponse(content=results)
        
    except Exception as e:
        logger.error(f"Error executing automation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Ensure log directory exists
    os.makedirs("/app/logs", exist_ok=True)
    os.makedirs("/app/screenshots", exist_ok=True)
    os.makedirs("/app/videos", exist_ok=True)
    
    # Start the server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
                "file": {
                    "formatter": "default",
                    "class": "logging.FileHandler",
                    "filename": "/app/logs/automation-api.log",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default", "file"],
            },
        }
    )