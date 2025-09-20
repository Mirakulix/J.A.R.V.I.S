#!/bin/bash
# ADB Server Setup Script for Android Emulator

set -e

echo "Starting ADB Server setup..."

# Wait for emulator to be ready
wait_for_emulator() {
    local timeout=300
    local count=0
    
    echo "Waiting for emulator to start..."
    
    while [ $count -lt $timeout ]; do
        if adb devices | grep -q "emulator"; then
            echo "Emulator detected!"
            return 0
        fi
        sleep 2
        count=$((count + 2))
        echo "Waiting... ($count/$timeout seconds)"
    done
    
    echo "Timeout waiting for emulator"
    return 1
}

# Start ADB server
echo "Starting ADB server..."
adb start-server

# Wait for emulator
if wait_for_emulator; then
    echo "ADB setup completed successfully"
    
    # Enable development options
    adb shell settings put global development_settings_enabled 1
    adb shell settings put global stay_on_while_plugged_in 3
    adb shell settings put global auto_time 0
    adb shell settings put global auto_time_zone 0
    
    # Disable animations for faster testing
    adb shell settings put global window_animation_scale 0.0
    adb shell settings put global transition_animation_scale 0.0
    adb shell settings put global animator_duration_scale 0.0
    
    # Configure accessibility settings for automation
    adb shell settings put secure accessibility_enabled 1
    
    # Grant necessary permissions for automation tools
    adb shell pm grant io.appium.uiautomator2.server android.permission.ACCESS_FINE_LOCATION 2>/dev/null || true
    adb shell pm grant io.appium.uiautomator2.server android.permission.CAMERA 2>/dev/null || true
    adb shell pm grant io.appium.uiautomator2.server android.permission.RECORD_AUDIO 2>/dev/null || true
    
    echo "Android development settings configured"
else
    echo "Failed to setup ADB - emulator not responding"
    exit 1
fi

# Keep the script running to maintain ADB connection
while true; do
    if ! adb devices | grep -q "emulator"; then
        echo "Emulator connection lost, attempting to reconnect..."
        adb start-server
    fi
    sleep 30
done