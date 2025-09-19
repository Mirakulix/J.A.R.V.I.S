"""
J.A.R.V.I.S. Speech Processing Module
===================================

Umfassendes Sprachverarbeitungsmodul mit STT, TTS, NLP und Spracherkennung.
Integriert OpenAI APIs und lokale Alternativen für optimale Performance.
"""

from .speech_processor import SpeechProcessor
from .tts_engine import TTSEngine
from .stt_engine import STTEngine
from .voice_recognition import VoiceRecognition
from .nlp_processor import NLPProcessor

__version__ = "1.0.0"

__all__ = [
    "SpeechProcessor",
    "TTSEngine", 
    "STTEngine",
    "VoiceRecognition",
    "NLPProcessor"
]