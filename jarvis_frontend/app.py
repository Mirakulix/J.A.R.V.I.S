#!/usr/bin/env python3
"""JARVIS Frontend Application with German Conversation Interface"""
from flask import Flask, render_template, jsonify, request, send_from_directory, send_file
import os
import io

app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    """Main J.A.R.V.I.S interface"""
    return render_template('index.html')

@app.route('/german-conversation')
def german_conversation():
    """German conversation interface with audio visualization"""
    return render_template('german_conversation.html')

@app.route('/analytics')
def analytics():
    """Analytics and monitoring dashboard"""
    return render_template('analytics.html')

@app.route('/settings')
def settings():
    """System settings and configuration"""
    return render_template('settings.html')

@app.route('/smart-home')
def smart_home():
    """Smart home control interface"""
    return render_template('smart_home.html')

@app.route('/meeting-notes')
def meeting_notes():
    """Meeting Notes Assistant with AI transcription"""
    return render_template('meeting_notes.html')

@app.route('/ideas')
def ideas():
    """Ideas Lab for submitting and managing new feature ideas"""
    return render_template('ideas.html')

@app.route('/api/tts', methods=['POST'])
def text_to_speech_proxy():
    """Proxy TTS requests to core service"""
    import requests
    try:
        # Forward request to core service
        data = request.get_json()
        response = requests.post('http://jarvis-core:8000/text-to-speech', 
                               json=data, timeout=10)
        
        if response.status_code == 200:
            return send_file(
                io.BytesIO(response.content),
                mimetype='audio/wav',
                as_attachment=True,
                download_name='speech.wav'
            )
        else:
            return jsonify({'error': 'TTS service unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stt', methods=['POST'])
def speech_to_text_proxy():
    """Proxy Speech-to-Text requests to core service"""
    import requests
    try:
        # Handle file upload and forward to core service
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        files = {'audio': (audio_file.filename, audio_file, 'audio/wav')}
        
        response = requests.post('http://jarvis-core:8000/speech-to-text', 
                               files=files, timeout=15)
        
        if response.status_code == 200:
            return response.json()
        else:
            return jsonify({'error': 'STT service unavailable'}), 503
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
