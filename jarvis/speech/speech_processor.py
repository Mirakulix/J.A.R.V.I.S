"""
Hauptklasse für Sprachverarbeitung in J.A.R.V.I.S.
=================================================

Zentrale Orchestrierung aller Sprachfunktionen:
- Speech-to-Text (OpenAI Whisper)
- Text-to-Speech (OpenAI TTS, lokale Engines)
- Natural Language Processing
- Spracherkennung und Benutzeridentifikation
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
import os
from pathlib import Path
import tempfile

from ..core.event_bus import EventBus, Event, EventPriority
from .stt_engine import STTEngine
from .tts_engine import TTSEngine
from .nlp_processor import NLPProcessor
from .voice_recognition import VoiceRecognition

logger = logging.getLogger(__name__)


@dataclass
class SpeechInput:
    """Spracheingabe-Daten."""
    audio_data: bytes
    format: str = "wav"  # wav, mp3, m4a, etc.
    sample_rate: int = 16000
    user_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class SpeechOutput:
    """Sprachausgabe-Daten."""
    text: str
    audio_data: Optional[bytes] = None
    voice: str = "alloy"
    format: str = "mp3"
    speed: float = 1.0


@dataclass 
class ProcessedSpeech:
    """Verarbeitete Spracheingabe."""
    transcription: str
    intent: Dict[str, Any]
    entities: List[Dict[str, Any]]
    confidence: float
    user_id: Optional[str] = None
    language: str = "de"


class SpeechProcessor:
    """
    Hauptklasse für alle Sprachverarbeitungsoperationen.
    
    Features:
    - Mehrsprachige Sprach-zu-Text Konvertierung
    - Kontextuelle Text-zu-Sprach Synthese
    - Intent-Erkennung und Entity-Extraktion
    - Benutzer-Spracherkennung
    - Noise Cancellation und Audio-Preprocessing
    """
    
    def __init__(self, event_bus: EventBus, openai_api_key: str):
        self.event_bus = event_bus
        
        # Komponenten initialisieren
        self.stt_engine = STTEngine(openai_api_key)
        self.tts_engine = TTSEngine(openai_api_key)
        self.nlp_processor = NLPProcessor(openai_api_key)
        self.voice_recognition = VoiceRecognition()
        
        # Konfiguration
        self.supported_languages = ["de", "en", "fr", "es", "it"]
        self.default_voice = "alloy"
        self.audio_temp_dir = Path(tempfile.gettempdir()) / "jarvis_audio"
        self.audio_temp_dir.mkdir(exist_ok=True)
        
        # Event-Handler registrieren
        self._register_event_handlers()
        
    async def start(self):
        """Startet alle Sprachverarbeitungskomponenten."""
        await self.stt_engine.start()
        await self.tts_engine.start()
        await self.nlp_processor.start()
        await self.voice_recognition.start()
        
        logger.info("Speech Processor started")
        
    async def stop(self):
        """Stoppt alle Komponenten."""
        await self.stt_engine.stop()
        await self.tts_engine.stop() 
        await self.nlp_processor.stop()
        await self.voice_recognition.stop()
        
        logger.info("Speech Processor stopped")
        
    def _register_event_handlers(self):
        """Registriert Event-Handler."""
        self.event_bus.subscribe("speech.input", self._handle_speech_input)
        self.event_bus.subscribe("speech.synthesize", self._handle_speech_synthesis)
        self.event_bus.subscribe("speech.recognize_user", self._handle_user_recognition)
        
    async def process_speech_input(self, speech_input: SpeechInput) -> ProcessedSpeech:
        """
        Verarbeitet komplette Spracheingabe.
        
        Args:
            speech_input: Spracheingabe-Daten
            
        Returns:
            Verarbeitete Sprachdaten mit Intent und Entities
        """
        try:
            # 1. Benutzer-Spracherkennung (optional)
            detected_user = None
            if speech_input.user_id is None:
                detected_user = await self.voice_recognition.identify_speaker(
                    speech_input.audio_data
                )
                
            # 2. Speech-to-Text
            transcription_result = await self.stt_engine.transcribe(
                speech_input.audio_data,
                format=speech_input.format
            )
            
            if not transcription_result.success:
                raise Exception(f"STT failed: {transcription_result.error}")
                
            # 3. NLP-Verarbeitung
            nlp_result = await self.nlp_processor.process(
                transcription_result.text,
                user_id=speech_input.user_id or detected_user,
                session_id=speech_input.session_id
            )
            
            # 4. Ergebnis zusammenstellen
            processed = ProcessedSpeech(
                transcription=transcription_result.text,
                intent=nlp_result.intent,
                entities=nlp_result.entities,
                confidence=min(transcription_result.confidence, nlp_result.confidence),
                user_id=speech_input.user_id or detected_user,
                language=transcription_result.language
            )
            
            # Event senden
            await self.event_bus.publish(Event(
                type="speech.processed",
                data={
                    "processed_speech": processed,
                    "session_id": speech_input.session_id
                },
                priority=EventPriority.HIGH,
                source_module="speech_processor"
            ))
            
            logger.info(f"Processed speech: '{transcription_result.text[:50]}...'")
            return processed
            
        except Exception as e:
            logger.error(f"Error processing speech input: {e}")
            
            # Fehler-Event senden
            await self.event_bus.publish(Event(
                type="speech.processing_error",
                data={
                    "error": str(e),
                    "session_id": speech_input.session_id
                },
                priority=EventPriority.HIGH,
                source_module="speech_processor"
            ))
            
            raise
            
    async def synthesize_speech(self, speech_output: SpeechOutput) -> bytes:
        """
        Synthestisiert Sprache aus Text.
        
        Args:
            speech_output: Text und Sprachparameter
            
        Returns:
            Audio-Daten als bytes
        """
        try:
            # Text-zu-Sprache Konvertierung
            audio_data = await self.tts_engine.synthesize(
                text=speech_output.text,
                voice=speech_output.voice,
                speed=speech_output.speed,
                format=speech_output.format
            )
            
            # Event senden
            await self.event_bus.publish(Event(
                type="speech.synthesized",
                data={
                    "text": speech_output.text,
                    "voice": speech_output.voice,
                    "audio_size": len(audio_data)
                },
                priority=EventPriority.NORMAL,
                source_module="speech_processor"
            ))
            
            logger.info(f"Synthesized speech: '{speech_output.text[:50]}...'")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            raise
            
    async def train_voice_recognition(self, user_id: str, 
                                    audio_samples: List[bytes]) -> bool:
        """
        Trainiert Spracherkennung für einen Benutzer.
        
        Args:
            user_id: Benutzer-ID
            audio_samples: Liste von Audio-Samples
            
        Returns:
            True wenn Training erfolgreich
        """
        try:
            success = await self.voice_recognition.train_user_voice(
                user_id, audio_samples
            )
            
            if success:
                await self.event_bus.publish(Event(
                    type="speech.voice_trained",
                    data={
                        "user_id": user_id,
                        "sample_count": len(audio_samples)
                    },
                    priority=EventPriority.NORMAL,
                    source_module="speech_processor"
                ))
                
            return success
            
        except Exception as e:
            logger.error(f"Error training voice recognition: {e}")
            return False
            
    async def _handle_speech_input(self, event: Event):
        """Handler für Spracheingabe-Events."""
        try:
            data = event.data
            speech_input = SpeechInput(**data.get("speech_input", {}))
            
            processed = await self.process_speech_input(speech_input)
            
            # Weiterleitung an Intent-Handler
            await self.event_bus.publish(Event(
                type="intent.detected",
                data={
                    "intent": processed.intent,
                    "entities": processed.entities,
                    "user_id": processed.user_id,
                    "session_id": data.get("session_id"),
                    "original_text": processed.transcription
                },
                priority=EventPriority.HIGH,
                source_module="speech_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling speech input event: {e}")
            
    async def _handle_speech_synthesis(self, event: Event):
        """Handler für Sprachsynthese-Events."""
        try:
            data = event.data
            speech_output = SpeechOutput(**data.get("speech_output", {}))
            
            audio_data = await self.synthesize_speech(speech_output)
            
            # Audio-Daten zurücksenden
            await self.event_bus.publish(Event(
                type="speech.audio_ready",
                data={
                    "audio_data": audio_data,
                    "format": speech_output.format,
                    "session_id": data.get("session_id")
                },
                priority=EventPriority.HIGH,
                source_module="speech_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling speech synthesis event: {e}")
            
    async def _handle_user_recognition(self, event: Event):
        """Handler für Benutzer-Spracherkennung."""
        try:
            data = event.data
            audio_data = data.get("audio_data")
            
            if audio_data:
                user_id = await self.voice_recognition.identify_speaker(audio_data)
                
                await self.event_bus.publish(Event(
                    type="user.identified",
                    data={
                        "user_id": user_id,
                        "confidence": 0.85,  # TODO: Echte Konfidenz
                        "method": "voice_recognition"
                    },
                    priority=EventPriority.NORMAL,
                    source_module="speech_processor"
                ))
                
        except Exception as e:
            logger.error(f"Error handling user recognition event: {e}")
            
    def get_supported_languages(self) -> List[str]:
        """Gibt unterstützte Sprachen zurück."""
        return self.supported_languages.copy()
        
    def get_available_voices(self) -> List[str]:
        """Gibt verfügbare TTS-Stimmen zurück."""
        return self.tts_engine.get_available_voices()
        
    async def get_stats(self) -> Dict[str, Any]:
        """Gibt Sprachverarbeitungs-Statistiken zurück."""
        stt_stats = await self.stt_engine.get_stats()
        tts_stats = await self.tts_engine.get_stats()
        nlp_stats = await self.nlp_processor.get_stats()
        
        return {
            "stt": stt_stats,
            "tts": tts_stats,
            "nlp": nlp_stats,
            "supported_languages": len(self.supported_languages),
            "available_voices": len(self.get_available_voices())
        }