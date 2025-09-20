#!/usr/bin/env python3
"""JARVIS Frontend Application"""
from flask import Flask, render_template
import os

app = Flask(__name__)

@app.route('/')
def index():
    return {"message": "JARVIS Frontend", "status": "running"}

@app.route('/health')
def health():
    return {"status": "healthy"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
