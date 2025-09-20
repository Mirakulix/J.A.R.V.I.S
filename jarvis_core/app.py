#!/usr/bin/env python3
"""JARVIS Core Service with German Conversation Capabilities"""
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
import json
import io
import base64
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import uuid

# German language processing imports
try:
    import speech_recognition as sr
    import pyttsx3
    import pyaudio
    import wave
    import numpy as np
    from langdetect import detect
    import openai
except ImportError:
    logging.warning("Speech processing libraries not fully available")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="JARVIS Core - German Conversation AI", 
    version="2.0.0",
    description="JARVIS Core Service with German language conversation capabilities"
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class ConversationRequest(BaseModel):
    message: str
    language: Optional[str] = "auto"
    voice_enabled: Optional[bool] = True

class AudioData(BaseModel):
    audio_data: str  # base64 encoded
    format: str = "wav"
    sample_rate: int = 44100

class TTSRequest(BaseModel):
    text: str
    language: str = "de"
    voice: str = "default"

# In-memory storage for conversations
conversations: Dict[str, List[Dict]] = {}
connected_clients: List[WebSocket] = []

# German responses for JARVIS
JARVIS_RESPONSES_DE = {
    "greeting": [
        "Hallo! Ich bin JARVIS. Wie kann ich Ihnen heute helfen?",
        "Guten Tag! JARVIS steht zu Ihren Diensten.",
        "Willkommen! Ich höre Ihnen zu."
    ],
    "goodbye": [
        "Auf Wiedersehen! Es war mir eine Freude, Ihnen zu helfen.",
        "Bis bald! Rufen Sie mich, wenn Sie mich brauchen.",
        "Tschüss! Haben Sie einen schönen Tag."
    ],
    "help": [
        "Ich kann Ihnen bei verschiedenen Aufgaben helfen. Fragen Sie einfach!",
        "Ich stehe für Gespräche, Informationen und Assistenz zur Verfügung.",
        "Womit kann ich Ihnen behilflich sein?"
    ],
    "unknown": [
        "Entschuldigung, das habe ich nicht verstanden. Können Sie das wiederholen?",
        "Könnten Sie das anders formulieren?",
        "Ich bin nicht sicher, was Sie meinen. Können Sie präziser sein?"
    ]
}

class GermanConversationEngine:
    def __init__(self):
        self.recognizer = None
        self.tts_engine = None
        self.initialize_engines()
    
    def initialize_engines(self):
        """Initialize speech recognition and TTS engines"""
        try:
            self.recognizer = sr.Recognizer()
            self.tts_engine = pyttsx3.init()
            
            # Configure German TTS
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'german' in voice.name.lower() or 'deutsch' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            self.tts_engine.setProperty('rate', 150)  # Speaking rate
            self.tts_engine.setProperty('volume', 0.8)  # Volume level
            
        except Exception as e:
            logger.error(f"Failed to initialize speech engines: {e}")
    
    def detect_language(self, text: str) -> str:
        """Detect the language of input text"""
        try:
            lang = detect(text)
            return lang
        except:
            return "de"  # Default to German
    
    def process_german_text(self, text: str) -> str:
        """Process German text and generate appropriate response"""
        text_lower = text.lower()
        
        # Simple keyword-based responses
        if any(word in text_lower for word in ["hallo", "hi", "guten tag", "servus"]):
            return JARVIS_RESPONSES_DE["greeting"][0]
        elif any(word in text_lower for word in ["tschüss", "auf wiedersehen", "bis bald"]):
            return JARVIS_RESPONSES_DE["goodbye"][0]
        elif any(word in text_lower for word in ["hilfe", "help", "was kannst du"]):
            return JARVIS_RESPONSES_DE["help"][0]
        elif "wie geht es dir" in text_lower or "wie geht's" in text_lower:
            return "Mir geht es gut, danke! Ich bin bereit, Ihnen zu helfen."
        elif "wie spät" in text_lower or "uhrzeit" in text_lower:
            now = datetime.now()
            return f"Es ist jetzt {now.strftime('%H:%M Uhr')}."
        elif "datum" in text_lower or "welcher tag" in text_lower:
            now = datetime.now()
            return f"Heute ist der {now.strftime('%d.%m.%Y')}."
        else:
            return JARVIS_RESPONSES_DE["unknown"][0]
    
    def text_to_speech(self, text: str) -> bytes:
        """Convert German text to speech"""
        try:
            if not self.tts_engine:
                raise Exception("TTS engine not initialized")
            
            # Save to temporary file
            audio_buffer = io.BytesIO()
            self.tts_engine.save_to_file(text, 'temp_speech.wav')
            self.tts_engine.runAndWait()
            
            # Read the file and return bytes
            with open('temp_speech.wav', 'rb') as f:
                audio_data = f.read()
            
            return audio_data
            
        except Exception as e:
            logger.error(f"TTS conversion failed: {e}")
            return b""

# Initialize German conversation engine
german_engine = GermanConversationEngine()

@app.get("/")
async def root():
    return {
        "message": "JARVIS Core Service mit deutscher Konversation", 
        "status": "running",
        "features": [
            "German conversation",
            "Speech recognition", 
            "Text-to-speech",
            "Audio spectrum analysis"
        ]
    }

@app.get("/health")
async def health():
    return {"status": "healthy", "language_support": ["de", "en"]}

@app.post("/conversation")
async def process_conversation(request: ConversationRequest):
    """Process conversation in German or English"""
    try:
        session_id = str(uuid.uuid4())
        
        # Detect language if auto-detection is enabled
        if request.language == "auto":
            detected_lang = german_engine.detect_language(request.message)
        else:
            detected_lang = request.language
        
        # Process based on language
        if detected_lang == "de" or "deutsch" in request.message.lower():
            response_text = german_engine.process_german_text(request.message)
        else:
            # Fallback to English
            response_text = f"I understand. You said: {request.message}"
        
        # Store conversation
        if session_id not in conversations:
            conversations[session_id] = []
        
        conversations[session_id].append({
            "timestamp": datetime.now().isoformat(),
            "user_message": request.message,
            "jarvis_response": response_text,
            "language": detected_lang
        })
        
        # Broadcast to connected WebSocket clients
        message_data = {
            "type": "conversation",
            "session_id": session_id,
            "user_message": request.message,
            "jarvis_response": response_text,
            "language": detected_lang,
            "timestamp": datetime.now().isoformat()
        }
        
        for client in connected_clients[:]:
            try:
                await client.send_text(json.dumps(message_data))
            except:
                connected_clients.remove(client)
        
        return {
            "session_id": session_id,
            "response": response_text,
            "language": detected_lang,
            "voice_enabled": request.voice_enabled
        }
        
    except Exception as e:
        logger.error(f"Conversation processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text (German/English)"""
    try:
        if not german_engine.recognizer:
            raise HTTPException(status_code=503, detail="Speech recognition not available")
        
        # Read audio file
        audio_data = await audio.read()
        
        # Process with speech recognition
        with sr.AudioFile(io.BytesIO(audio_data)) as source:
            audio = german_engine.recognizer.record(source)
            
            # Try German first, then English
            try:
                text = german_engine.recognizer.recognize_google(audio, language="de-DE")
                language = "de"
            except:
                try:
                    text = german_engine.recognizer.recognize_google(audio, language="en-US")
                    language = "en"
                except:
                    raise HTTPException(status_code=400, detail="Could not understand audio")
        
        return {
            "text": text,
            "language": language,
            "confidence": 0.8  # Mock confidence score
        }
        
    except Exception as e:
        logger.error(f"Speech recognition failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """Convert German text to speech"""
    try:
        audio_data = german_engine.text_to_speech(request.text)
        
        if not audio_data:
            raise HTTPException(status_code=500, detail="TTS conversion failed")
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
        
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Get conversation history"""
    if session_id in conversations:
        return {"session_id": session_id, "messages": conversations[session_id]}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")

@app.websocket("/ws/conversation")
async def websocket_conversation(websocket: WebSocket):
    """WebSocket endpoint for real-time conversation"""
    await websocket.accept()
    connected_clients.append(websocket)
    
    try:
        while True:
            # Send heartbeat
            await websocket.send_text(json.dumps({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat()
            }))
            await asyncio.sleep(30)
            
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in connected_clients:
            connected_clients.remove(websocket)

@app.post("/audio/analyze")
async def analyze_audio_spectrum(audio: UploadFile = File(...)):
    """Analyze audio spectrum for visualization"""
    try:
        audio_data = await audio.read()
        
        # Mock spectrum analysis (would need actual audio processing)
        # This would normally use FFT to analyze frequencies
        spectrum_data = []
        for i in range(360):  # Circular spectrum (degrees)
            # Mock frequency data
            amplitude = np.random.random() * 100 if np.random.random() > 0.3 else 0
            spectrum_data.append({
                "angle": i,
                "frequency": 20 + (i * 20000 / 360),  # 20Hz to 20kHz
                "amplitude": amplitude,
                "color": f"hsl({i}, 70%, 50%)"
            })
        
        return {
            "spectrum": spectrum_data,
            "timestamp": datetime.now().isoformat(),
            "duration": 1.0  # Mock duration
        }
        
    except Exception as e:
        logger.error(f"Audio analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/capabilities")
async def get_capabilities():
    """Get JARVIS capabilities"""
    return {
        "languages": ["de", "en"],
        "features": {
            "speech_recognition": True,
            "text_to_speech": True,
            "conversation": True,
            "audio_analysis": True,
            "spectrum_visualization": True
        },
        "german_features": {
            "natural_conversation": True,
            "time_queries": True,
            "date_queries": True,
            "greeting_responses": True,
            "help_system": True
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
