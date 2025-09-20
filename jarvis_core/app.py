#!/usr/bin/env python3
"""JARVIS Core Service with German Conversation Capabilities"""
from fastapi import FastAPI, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect, Depends
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
import os
import sys

# Add shared module to path
sys.path.append('/app/shared')
from azure_ai_service import AzureAIService, process_idea_with_azure_ai, validate_azure_ai_config

# Database connection imports
try:
    import asyncpg
    import psycopg2
except ImportError:
    logging.warning("PostgreSQL libraries not available")

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

class IdeaSubmissionRequest(BaseModel):
    idea_prompt: str
    submitted_by: Optional[str] = None
    user_context: Optional[str] = None

class IdeaResponse(BaseModel):
    id: int
    status: str
    message: str
    generated_content: Optional[Dict] = None

# In-memory storage for conversations
conversations: Dict[str, List[Dict]] = {}
connected_clients: List[WebSocket] = []

# Database connection
class DatabaseManager:
    def __init__(self):
        self.org_db_url = os.getenv('POSTGRES_ORG_URL')
        
    async def get_org_connection(self):
        """Get connection to organization database"""
        if not self.org_db_url:
            raise HTTPException(status_code=500, detail="Database connection not configured")
        return await asyncpg.connect(self.org_db_url)
    
    async def insert_idea(self, idea_data: Dict) -> int:
        """Insert new idea into database"""
        conn = await self.get_org_connection()
        try:
            query = """
                INSERT INTO ideas (
                    original_prompt, submitted_by, generated_title,
                    description_bullet_1, description_bullet_2, description_bullet_3,
                    detailed_concept, optimized_claude_prompt, category,
                    complexity, tags, requirements_notes, azure_processing_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """
            
            result = await conn.fetchval(
                query,
                idea_data['original_prompt'],
                idea_data.get('submitted_by'),
                idea_data.get('generated_title'),
                idea_data.get('bullet_points', [None, None, None])[0],
                idea_data.get('bullet_points', [None, None, None])[1],
                idea_data.get('bullet_points', [None, None, None])[2],
                idea_data.get('detailed_concept'),
                idea_data.get('optimized_prompt'),
                idea_data.get('category'),
                idea_data.get('complexity'),
                idea_data.get('tags', []),
                idea_data.get('requirements_notes'),
                idea_data.get('azure_processing_status', 'completed')
            )
            return result
        finally:
            await conn.close()
    
    async def update_idea_status(self, idea_id: int, status: str, processing_data: Optional[Dict] = None):
        """Update idea processing status"""
        conn = await self.get_org_connection()
        try:
            if processing_data:
                query = """
                    UPDATE ideas SET 
                        status = $2,
                        generated_title = $3,
                        description_bullet_1 = $4,
                        description_bullet_2 = $5,
                        description_bullet_3 = $6,
                        detailed_concept = $7,
                        optimized_claude_prompt = $8,
                        category = $9,
                        complexity = $10,
                        tags = $11,
                        requirements_notes = $12,
                        azure_processing_status = $13,
                        processed_date = CURRENT_TIMESTAMP,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = $1
                """
                await conn.execute(
                    query, idea_id, status,
                    processing_data.get('title'),
                    processing_data.get('bullet_points', [None, None, None])[0],
                    processing_data.get('bullet_points', [None, None, None])[1],
                    processing_data.get('bullet_points', [None, None, None])[2],
                    processing_data.get('detailed_concept'),
                    processing_data.get('optimized_prompt'),
                    processing_data.get('category'),
                    processing_data.get('complexity'),
                    processing_data.get('tags', []),
                    processing_data.get('requirements_notes'),
                    'completed'
                )
            else:
                query = "UPDATE ideas SET status = $2, last_updated = CURRENT_TIMESTAMP WHERE id = $1"
                await conn.execute(query, idea_id, status)
        finally:
            await conn.close()

    async def get_ideas(self, limit: int = 50, status_filter: Optional[str] = None) -> List[Dict]:
        """Retrieve ideas from database"""
        conn = await self.get_org_connection()
        try:
            if status_filter:
                query = """
                    SELECT * FROM ideas 
                    WHERE status = $1 
                    ORDER BY submission_date DESC 
                    LIMIT $2
                """
                rows = await conn.fetch(query, status_filter, limit)
            else:
                query = """
                    SELECT * FROM ideas 
                    ORDER BY submission_date DESC 
                    LIMIT $1
                """
                rows = await conn.fetch(query, limit)
            
            return [dict(row) for row in rows]
        finally:
            await conn.close()

db_manager = DatabaseManager()

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

@app.post("/ideas/submit")
async def submit_idea(request: IdeaSubmissionRequest) -> IdeaResponse:
    """Submit a new idea for AI processing and enhancement"""
    try:
        logger.info(f"Received new idea submission: {request.idea_prompt[:100]}...")
        
        # First, store the basic idea in database
        basic_idea_data = {
            'original_prompt': request.idea_prompt,
            'submitted_by': request.submitted_by,
            'azure_processing_status': 'processing'
        }
        
        idea_id = await db_manager.insert_idea(basic_idea_data)
        logger.info(f"Created idea record with ID: {idea_id}")
        
        try:
            # Process with Azure AI
            if validate_azure_ai_config():
                logger.info("Processing idea with Azure AI...")
                enhancement = await process_idea_with_azure_ai(
                    request.idea_prompt, 
                    request.user_context
                )
                
                # Prepare enhanced data for database
                enhanced_data = {
                    'title': enhancement.title,
                    'bullet_points': enhancement.bullet_points,
                    'detailed_concept': enhancement.detailed_concept,
                    'optimized_prompt': enhancement.optimized_prompt,
                    'category': enhancement.category,
                    'complexity': enhancement.complexity,
                    'tags': enhancement.tags,
                    'requirements_notes': enhancement.requirements_notes
                }
                
                # Update database with enhanced content
                await db_manager.update_idea_status(idea_id, 'processed', enhanced_data)
                
                # Broadcast to connected clients
                idea_message = {
                    "type": "new_idea",
                    "idea_id": idea_id,
                    "title": enhancement.title,
                    "category": enhancement.category,
                    "complexity": enhancement.complexity,
                    "timestamp": datetime.now().isoformat()
                }
                
                for client in connected_clients[:]:
                    try:
                        await client.send_text(json.dumps(idea_message))
                    except:
                        connected_clients.remove(client)
                
                return IdeaResponse(
                    id=idea_id,
                    status="processed",
                    message="Idea successfully processed and enhanced with AI",
                    generated_content={
                        "title": enhancement.title,
                        "bullet_points": enhancement.bullet_points,
                        "category": enhancement.category,
                        "complexity": enhancement.complexity,
                        "claude_prompt": enhancement.optimized_prompt
                    }
                )
                
            else:
                # Azure AI not configured, use fallback
                logger.warning("Azure AI not configured, using fallback processing")
                await db_manager.update_idea_status(idea_id, 'submitted')
                
                return IdeaResponse(
                    id=idea_id,
                    status="submitted",
                    message="Idea submitted successfully. Manual review required (Azure AI not configured)."
                )
                
        except Exception as ai_error:
            logger.error(f"AI processing failed for idea {idea_id}: {ai_error}")
            await db_manager.update_idea_status(idea_id, 'processing_failed')
            
            return IdeaResponse(
                id=idea_id,
                status="processing_failed", 
                message=f"Idea submitted but AI processing failed: {str(ai_error)}"
            )
            
    except Exception as e:
        logger.error(f"Failed to submit idea: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ideas")
async def get_ideas(limit: int = 50, status: Optional[str] = None):
    """Retrieve stored ideas"""
    try:
        ideas = await db_manager.get_ideas(limit, status)
        return {
            "ideas": ideas,
            "count": len(ideas),
            "status_filter": status
        }
    except Exception as e:
        logger.error(f"Failed to retrieve ideas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ideas/{idea_id}")
async def get_idea(idea_id: int):
    """Get a specific idea by ID"""
    try:
        ideas = await db_manager.get_ideas(1, None)
        idea = next((i for i in ideas if i['id'] == idea_id), None)
        
        if not idea:
            raise HTTPException(status_code=404, detail="Idea not found")
        
        return idea
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve idea {idea_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ideas/stats")
async def get_ideas_stats():
    """Get statistics about submitted ideas"""
    try:
        all_ideas = await db_manager.get_ideas(1000)  # Get more for stats
        
        stats = {
            "total_ideas": len(all_ideas),
            "by_status": {},
            "by_category": {},
            "by_complexity": {},
            "average_complexity": 0,
            "recent_submissions": 0
        }
        
        # Calculate statistics
        complexities = []
        recent_cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for idea in all_ideas:
            # Status distribution
            status = idea.get('status', 'unknown')
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            # Category distribution
            category = idea.get('category', 'uncategorized')
            stats["by_category"][category] = stats["by_category"].get(category, 0) + 1
            
            # Complexity distribution
            complexity = idea.get('complexity', 3)
            stats["by_complexity"][str(complexity)] = stats["by_complexity"].get(str(complexity), 0) + 1
            complexities.append(complexity)
            
            # Recent submissions (today)
            if idea.get('submission_date') and idea['submission_date'].date() >= recent_cutoff.date():
                stats["recent_submissions"] += 1
        
        # Average complexity
        if complexities:
            stats["average_complexity"] = round(sum(complexities) / len(complexities), 2)
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to generate ideas stats: {e}")
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
            "spectrum_visualization": True,
            "idea_submission": True,
            "ai_enhancement": validate_azure_ai_config()
        },
        "german_features": {
            "natural_conversation": True,
            "time_queries": True,
            "date_queries": True,
            "greeting_responses": True,
            "help_system": True
        },
        "idea_features": {
            "submission": True,
            "ai_processing": validate_azure_ai_config(),
            "categorization": True,
            "complexity_assessment": True,
            "claude_prompt_optimization": True
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
