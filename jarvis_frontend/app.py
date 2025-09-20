#!/usr/bin/env python3
"""JARVIS Frontend Application with German Conversation Interface"""
from flask import Flask, render_template, jsonify, request, send_from_directory
import os

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    """Main J.A.R.V.I.S interface"""
    return render_template('index.html')

@app.route('/german-conversation')
def german_conversation():
    """German conversation interface with audio visualization"""
    return render_template('german_conversation.html')

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({
        "message": "JARVIS Frontend mit deutscher Konversation", 
        "status": "running",
        "features": ["German conversation", "Audio visualization", "Real-time chat"]
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

# Serve static files
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
