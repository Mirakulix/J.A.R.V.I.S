"""
J.A.R.V.I.S. Computer Vision Module
=================================

Umfassendes Computer Vision System mit:
- Bilderkennung und -analyse
- Objektdetektion und -verfolgung
- Gesichtserkennung und Emotionsanalyse
- OCR und Dokumentenverarbeitung
- Echtzeit-Video-Analyse
"""

from .vision_processor import VisionProcessor
from .image_analyzer import ImageAnalyzer
from .object_detector import ObjectDetector
from .face_recognition import FaceRecognition
from .ocr_engine import OCREngine
from .video_analyzer import VideoAnalyzer

__version__ = "1.0.0"

__all__ = [
    "VisionProcessor",
    "ImageAnalyzer",
    "ObjectDetector", 
    "FaceRecognition",
    "OCREngine",
    "VideoAnalyzer"
]