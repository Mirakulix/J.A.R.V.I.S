#!/bin/bash
# Health Check Script for Android Emulator Container

# Check if ADB server is running
if ! pgrep -x "adb" > /dev/null; then
    echo "ADB server not running"
    exit 1
fi

# Check if emulator is running
if ! adb devices | grep -q "emulator"; then
    echo "No emulator connected"
    exit 1
fi

# Check if Appium server is responding
if ! curl -f http://localhost:4723/status > /dev/null 2>&1; then
    echo "Appium server not responding"
    exit 1
fi

# Check if VNC is accessible
if ! curl -f http://localhost:6080 > /dev/null 2>&1; then
    echo "VNC/noVNC not accessible"
    exit 1
fi

# Check if automation API is running
if ! curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "Automation API not responding"
    exit 1
fi

echo "All services healthy"
exit 0