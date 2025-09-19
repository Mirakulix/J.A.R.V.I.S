"""
Hauptklasse für visuelle Verarbeitung in J.A.R.V.I.S.
====================================================

Zentrale Orchestrierung aller Computer Vision Funktionen:
- OpenAI GPT-4V Integration für Bildanalyse
- Lokale CV-Models für Echtzeitverarbeitung
- Multimodale Fusion mit Sprachverarbeitung
- Sicherheit und Privacy-bewusste Verarbeitung
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass
import base64
import io
from pathlib import Path
import tempfile
import cv2
import numpy as np
from PIL import Image
import openai

from ..core.event_bus import EventBus, Event, EventPriority
from .image_analyzer import ImageAnalyzer
from .object_detector import ObjectDetector
from .face_recognition import FaceRecognition
from .ocr_engine import OCREngine
from .video_analyzer import VideoAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class ImageInput:
    """Bild-Eingabedaten."""
    image_data: Union[bytes, np.ndarray, str]  # bytes, numpy array oder base64
    format: str = "jpeg"  # jpeg, png, webp
    source: str = "upload"  # upload, camera, screenshot, url
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class VisionResult:
    """Ergebnis der visuellen Verarbeitung."""
    description: str
    objects: List[Dict[str, Any]]
    faces: List[Dict[str, Any]]
    text: List[Dict[str, Any]]
    scene_analysis: Dict[str, Any]
    emotions: List[Dict[str, Any]]
    confidence: float
    processing_time: float


@dataclass
class VideoInput:
    """Video-Eingabedaten."""
    video_data: Union[bytes, str]  # bytes oder Pfad
    format: str = "mp4"
    fps_limit: int = 1  # Frames pro Sekunde verarbeiten
    duration_limit: int = 60  # Maximale Länge in Sekunden


class VisionProcessor:
    """
    Hauptklasse für alle Computer Vision Operationen.
    
    Features:
    - GPT-4V Integration für natürlichsprachliche Bildbeschreibungen
    - Lokale CV-Models für Performance-kritische Aufgaben
    - Echtzeit-Objekt- und Gesichtserkennung
    - OCR für Textextraktion
    - Video-Analyse und Motion Detection
    - Privacy-bewusste Verarbeitung
    """
    
    def __init__(self, event_bus: EventBus, openai_api_key: str):
        self.event_bus = event_bus
        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        
        # Komponenten initialisieren
        self.image_analyzer = ImageAnalyzer(openai_api_key)
        self.object_detector = ObjectDetector()
        self.face_recognition = FaceRecognition()
        self.ocr_engine = OCREngine()
        self.video_analyzer = VideoAnalyzer()
        
        # Konfiguration
        self.temp_dir = Path(tempfile.gettempdir()) / "jarvis_vision"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Unterstützte Formate
        self.supported_image_formats = ["jpeg", "jpg", "png", "webp", "bmp"]
        self.supported_video_formats = ["mp4", "avi", "mov", "mkv"]
        
        # Performance-Einstellungen
        self.max_image_size = (1920, 1080)
        self.image_quality = 85
        
        # Event-Handler registrieren
        self._register_event_handlers()
        
    async def start(self):
        """Startet alle Vision-Komponenten."""
        await self.image_analyzer.start()
        await self.object_detector.start()
        await self.face_recognition.start()
        await self.ocr_engine.start()
        await self.video_analyzer.start()
        
        logger.info("Vision Processor started")
        
    async def stop(self):
        """Stoppt alle Komponenten."""
        await self.image_analyzer.stop()
        await self.object_detector.stop()
        await self.face_recognition.stop()
        await self.ocr_engine.stop()
        await self.video_analyzer.stop()
        
        logger.info("Vision Processor stopped")
        
    def _register_event_handlers(self):
        """Registriert Event-Handler."""
        self.event_bus.subscribe("vision.analyze_image", self._handle_image_analysis)
        self.event_bus.subscribe("vision.analyze_video", self._handle_video_analysis)
        self.event_bus.subscribe("vision.detect_objects", self._handle_object_detection)
        self.event_bus.subscribe("vision.recognize_faces", self._handle_face_recognition)
        self.event_bus.subscribe("vision.extract_text", self._handle_text_extraction)
        
    async def analyze_image(self, image_input: ImageInput, 
                          analysis_options: Optional[Dict[str, Any]] = None) -> VisionResult:
        """
        Umfassende Bildanalyse.
        
        Args:
            image_input: Bild-Eingabedaten
            analysis_options: Optionale Analyse-Parameter
            
        Returns:
            Umfassendes Analyse-Ergebnis
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Bild preprocessing
            processed_image = await self._preprocess_image(image_input)
            
            # Parallele Analyse verschiedener Aspekte
            tasks = []
            
            # GPT-4V für natürlichsprachliche Beschreibung
            if analysis_options is None or analysis_options.get("description", True):
                tasks.append(self._get_gpt4v_description(processed_image))
                
            # Lokale Objektdetektion
            if analysis_options is None or analysis_options.get("objects", True):
                tasks.append(self.object_detector.detect_objects(processed_image))
                
            # Gesichtserkennung und Emotionsanalyse
            if analysis_options is None or analysis_options.get("faces", True):
                tasks.append(self.face_recognition.detect_faces(processed_image))
                
            # OCR für Textextraktion
            if analysis_options is None or analysis_options.get("text", True):
                tasks.append(self.ocr_engine.extract_text(processed_image))
                
            # Scene Analysis
            if analysis_options is None or analysis_options.get("scene", True):
                tasks.append(self._analyze_scene(processed_image))
                
            # Alle Analysen parallel ausführen
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Ergebnisse zusammenführen
            description = results[0] if len(results) > 0 and not isinstance(results[0], Exception) else ""
            objects = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else []
            faces = results[2] if len(results) > 2 and not isinstance(results[2], Exception) else []
            text_data = results[3] if len(results) > 3 and not isinstance(results[3], Exception) else []
            scene_analysis = results[4] if len(results) > 4 and not isinstance(results[4], Exception) else {}
            
            # Emotionsanalyse aus Gesichtern extrahieren
            emotions = []
            for face in faces:
                if "emotions" in face:
                    emotions.extend(face["emotions"])
                    
            processing_time = asyncio.get_event_loop().time() - start_time
            
            # Konfidenz berechnen (Durchschnitt aller verfügbaren Konfidenz-Werte)
            confidences = []
            if objects:
                confidences.extend([obj.get("confidence", 0) for obj in objects])
            if faces:
                confidences.extend([face.get("confidence", 0) for face in faces])
            if text_data:
                confidences.extend([text.get("confidence", 0) for text in text_data])
                
            avg_confidence = np.mean(confidences) if confidences else 0.5
            
            result = VisionResult(
                description=description,
                objects=objects,
                faces=faces,
                text=text_data,
                scene_analysis=scene_analysis,
                emotions=emotions,
                confidence=float(avg_confidence),
                processing_time=processing_time
            )
            
            # Event senden
            await self.event_bus.publish(Event(
                type="vision.image_analyzed",
                data={
                    "result": result,
                    "processing_time": processing_time,
                    "image_source": image_input.source
                },
                priority=EventPriority.NORMAL,
                source_module="vision_processor"
            ))
            
            logger.info(f"Analyzed image: {len(objects)} objects, {len(faces)} faces, processing time: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            raise
            
    async def analyze_video(self, video_input: VideoInput,
                          analysis_options: Optional[Dict[str, Any]] = None) -> List[VisionResult]:
        """
        Video-Analyse mit Frame-by-Frame Verarbeitung.
        
        Args:
            video_input: Video-Eingabedaten
            analysis_options: Analyse-Parameter
            
        Returns:
            Liste von Analyse-Ergebnissen pro Frame
        """
        try:
            # Video-Frames extrahieren
            frames = await self.video_analyzer.extract_frames(
                video_input.video_data,
                fps=video_input.fps_limit,
                duration_limit=video_input.duration_limit
            )
            
            results = []
            
            # Frames parallel analysieren (in Batches)
            batch_size = 4
            for i in range(0, len(frames), batch_size):
                batch_frames = frames[i:i+batch_size]
                
                tasks = []
                for frame in batch_frames:
                    image_input = ImageInput(
                        image_data=frame,
                        source="video_frame"
                    )
                    tasks.append(self.analyze_image(image_input, analysis_options))
                    
                batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Nur erfolgreiche Ergebnisse hinzufügen
                for result in batch_results:
                    if not isinstance(result, Exception):
                        results.append(result)
                        
            # Video-Events senden
            await self.event_bus.publish(Event(
                type="vision.video_analyzed",
                data={
                    "frame_count": len(results),
                    "video_source": video_input.format,
                    "fps_analyzed": video_input.fps_limit
                },
                priority=EventPriority.NORMAL,
                source_module="vision_processor"
            ))
            
            logger.info(f"Analyzed video: {len(results)} frames processed")
            return results
            
        except Exception as e:
            logger.error(f"Error analyzing video: {e}")
            raise
            
    async def _preprocess_image(self, image_input: ImageInput) -> np.ndarray:
        """
        Bereitet Bild für Verarbeitung vor.
        
        Args:
            image_input: Eingabebild
            
        Returns:
            Vorverarbeitetes Bild als numpy array
        """
        try:
            # Bild laden basierend auf Eingabetyp
            if isinstance(image_input.image_data, bytes):
                image = Image.open(io.BytesIO(image_input.image_data))
            elif isinstance(image_input.image_data, str):
                if image_input.image_data.startswith('data:image'):
                    # Base64 encoded image
                    header, encoded = image_input.image_data.split(',', 1)
                    image_bytes = base64.b64decode(encoded)
                    image = Image.open(io.BytesIO(image_bytes))
                else:
                    # Dateipfad
                    image = Image.open(image_input.image_data)
            elif isinstance(image_input.image_data, np.ndarray):
                # Numpy array direkt verwenden
                return image_input.image_data
            else:
                raise ValueError(f"Unsupported image data type: {type(image_input.image_data)}")
                
            # RGB konvertieren falls nötig
            if image.mode != 'RGB':
                image = image.convert('RGB')
                
            # Größe anpassen falls nötig
            if image.size[0] > self.max_image_size[0] or image.size[1] > self.max_image_size[1]:
                image.thumbnail(self.max_image_size, Image.Resampling.LANCZOS)
                
            # Zu numpy array konvertieren
            return np.array(image)
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            raise
            
    async def _get_gpt4v_description(self, image: np.ndarray) -> str:
        """
        Holt natürlichsprachliche Beschreibung via GPT-4V.
        
        Args:
            image: Bild als numpy array
            
        Returns:
            Textuelle Beschreibung des Bildes
        """
        try:
            # Bild zu base64 konvertieren
            pil_image = Image.fromarray(image)
            buffer = io.BytesIO()
            pil_image.save(buffer, format="JPEG", quality=self.image_quality)
            image_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            # GPT-4V API Call
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text", 
                                "text": """Analysiere dieses Bild detailliert und beschreibe:
                                1. Was siehst du in dem Bild?
                                2. Welche Objekte, Personen oder Szenen sind zu sehen?
                                3. Was ist der Kontext oder die Situation?
                                4. Gibt es besondere Details oder Auffälligkeiten?
                                
                                Antworte auf Deutsch und sei präzise aber natürlich."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error getting GPT-4V description: {e}")
            return f"Fehler bei der Bildanalyse: {str(e)}"
            
    async def _analyze_scene(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Analysiert Szene und Umgebung.
        
        Args:
            image: Bild als numpy array
            
        Returns:
            Szenenanalysis-Daten
        """
        try:
            # Grundlegende Bildstatistiken
            height, width = image.shape[:2]
            
            # Farbanalyse
            mean_color = np.mean(image, axis=(0, 1))
            
            # Helligkeit und Kontrast
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Edge Detection für Komplexität
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (height * width)
            
            return {
                "dimensions": {"width": width, "height": height},
                "color_analysis": {
                    "mean_rgb": mean_color.tolist(),
                    "brightness": float(brightness),
                    "contrast": float(contrast)
                },
                "complexity": {
                    "edge_density": float(edge_density)
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing scene: {e}")
            return {}
            
    async def _handle_image_analysis(self, event: Event):
        """Handler für Bildanalyse-Events."""
        try:
            data = event.data
            image_input = ImageInput(**data.get("image_input", {}))
            analysis_options = data.get("analysis_options")
            
            result = await self.analyze_image(image_input, analysis_options)
            
            # Ergebnis zurücksenden
            await self.event_bus.publish(Event(
                type="vision.analysis_complete",
                data={
                    "result": result,
                    "request_id": data.get("request_id")
                },
                priority=EventPriority.HIGH,
                source_module="vision_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling image analysis event: {e}")
            
    async def _handle_video_analysis(self, event: Event):
        """Handler für Video-Analyse-Events."""
        try:
            data = event.data
            video_input = VideoInput(**data.get("video_input", {}))
            analysis_options = data.get("analysis_options")
            
            results = await self.analyze_video(video_input, analysis_options)
            
            # Ergebnisse zurücksenden
            await self.event_bus.publish(Event(
                type="vision.video_analysis_complete",
                data={
                    "results": results,
                    "request_id": data.get("request_id")
                },
                priority=EventPriority.HIGH,
                source_module="vision_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling video analysis event: {e}")
            
    async def _handle_object_detection(self, event: Event):
        """Handler für Objektdetektion-Events."""
        try:
            data = event.data
            image_input = ImageInput(**data.get("image_input", {}))
            
            image = await self._preprocess_image(image_input)
            objects = await self.object_detector.detect_objects(image)
            
            await self.event_bus.publish(Event(
                type="vision.objects_detected",
                data={
                    "objects": objects,
                    "request_id": data.get("request_id")
                },
                priority=EventPriority.NORMAL,
                source_module="vision_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling object detection event: {e}")
            
    async def _handle_face_recognition(self, event: Event):
        """Handler für Gesichtserkennung-Events."""
        try:
            data = event.data
            image_input = ImageInput(**data.get("image_input", {}))
            
            image = await self._preprocess_image(image_input)
            faces = await self.face_recognition.detect_faces(image)
            
            await self.event_bus.publish(Event(
                type="vision.faces_detected",
                data={
                    "faces": faces,
                    "request_id": data.get("request_id")
                },
                priority=EventPriority.NORMAL,
                source_module="vision_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling face recognition event: {e}")
            
    async def _handle_text_extraction(self, event: Event):
        """Handler für Textextraktion-Events."""
        try:
            data = event.data
            image_input = ImageInput(**data.get("image_input", {}))
            
            image = await self._preprocess_image(image_input)
            text_data = await self.ocr_engine.extract_text(image)
            
            await self.event_bus.publish(Event(
                type="vision.text_extracted",
                data={
                    "text_data": text_data,
                    "request_id": data.get("request_id")
                },
                priority=EventPriority.NORMAL,
                source_module="vision_processor"
            ))
            
        except Exception as e:
            logger.error(f"Error handling text extraction event: {e}")
            
    async def get_stats(self) -> Dict[str, Any]:
        """Gibt Vision-Verarbeitungsstatistiken zurück."""
        return {
            "supported_image_formats": self.supported_image_formats,
            "supported_video_formats": self.supported_video_formats,
            "max_image_size": self.max_image_size,
            "temp_files": len(list(self.temp_dir.glob("*"))),
            "components": {
                "image_analyzer": await self.image_analyzer.get_stats(),
                "object_detector": await self.object_detector.get_stats(),
                "face_recognition": await self.face_recognition.get_stats(),
                "ocr_engine": await self.ocr_engine.get_stats()
            }
        }