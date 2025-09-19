"""
Event Bus System für J.A.R.V.I.S.
================================

Zentrale Event-basierte Kommunikation zwischen allen Systemmodulen.
Ermöglicht lose Kopplung und asynchrone Verarbeitung.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class Event:
    """Basis Event-Klasse für alle Systemereignisse."""
    type: str
    data: Dict[str, Any]
    timestamp: datetime
    priority: EventPriority = EventPriority.NORMAL
    source_module: Optional[str] = None
    correlation_id: Optional[str] = None


class EventBus:
    """
    Zentraler Event Bus für Systemkommunikation.
    
    Features:
    - Asynchrone Event-Verarbeitung
    - Prioritäts-basierte Event-Behandlung
    - Event-Filterung und Routing
    - Fehlerbehandlung und Logging
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue = asyncio.PriorityQueue()
        self._running = False
        self._processor_task = None
        self._event_history: List[Event] = []
        self._max_history = 1000
        
    async def start(self):
        """Startet den Event-Processor."""
        if self._running:
            return
            
        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event Bus started")
        
    async def stop(self):
        """Stoppt den Event-Processor."""
        if not self._running:
            return
            
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Event Bus stopped")
        
    def subscribe(self, event_type: str, handler: Callable) -> bool:
        """
        Abonniert Events eines bestimmten Typs.
        
        Args:
            event_type: Typ des Events
            handler: Async Callback-Funktion
            
        Returns:
            True wenn erfolgreich abonniert
        """
        try:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
                
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)
                logger.debug(f"Subscribed to event type: {event_type}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error subscribing to {event_type}: {e}")
            return False
            
    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """
        Beendet Abonnement für Events eines bestimmten Typs.
        
        Args:
            event_type: Typ des Events
            handler: Callback-Funktion die entfernt werden soll
            
        Returns:
            True wenn erfolgreich entfernt
        """
        try:
            if event_type in self._subscribers:
                if handler in self._subscribers[event_type]:
                    self._subscribers[event_type].remove(handler)
                    logger.debug(f"Unsubscribed from event type: {event_type}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error unsubscribing from {event_type}: {e}")
            return False
            
    async def publish(self, event: Event) -> bool:
        """
        Veröffentlicht ein Event im System.
        
        Args:
            event: Event-Objekt
            
        Returns:
            True wenn erfolgreich veröffentlicht
        """
        try:
            if not self._running:
                await self.start()
                
            # Event zur Queue hinzufügen (niedriger Priority-Wert = höhere Priorität)
            await self._event_queue.put((event.priority.value, event))
            
            # Event-Historie aktualisieren
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history.pop(0)
                
            logger.debug(f"Published event: {event.type}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event {event.type}: {e}")
            return False
            
    async def _process_events(self):
        """Verarbeitet Events aus der Queue."""
        while self._running:
            try:
                # Warte auf nächstes Event mit Timeout
                try:
                    priority, event = await asyncio.wait_for(
                        self._event_queue.get(), 
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                    
                # Event an alle Subscriber verteilen
                await self._distribute_event(event)
                
            except Exception as e:
                logger.error(f"Error processing events: {e}")
                
    async def _distribute_event(self, event: Event):
        """Verteilt Event an alle relevanten Subscriber."""
        if event.type not in self._subscribers:
            logger.debug(f"No subscribers for event type: {event.type}")
            return
            
        subscribers = self._subscribers[event.type].copy()
        
        # Parallele Verarbeitung aller Subscriber
        tasks = []
        for handler in subscribers:
            task = asyncio.create_task(self._call_handler(handler, event))
            tasks.append(task)
            
        if tasks:
            # Warte auf alle Handler, aber logge Fehler
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Handler error for {event.type}: {result}")
                    
    async def _call_handler(self, handler: Callable, event: Event):
        """Ruft einen Event-Handler sicher auf."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Handler exception: {e}")
            raise
            
    def get_event_history(self, event_type: Optional[str] = None, 
                         limit: int = 100) -> List[Event]:
        """
        Gibt Event-Historie zurück.
        
        Args:
            event_type: Optional - filtert nach Event-Typ
            limit: Maximale Anzahl Events
            
        Returns:
            Liste von Events
        """
        history = self._event_history.copy()
        
        if event_type:
            history = [e for e in history if e.type == event_type]
            
        return history[-limit:] if limit else history
        
    def get_subscriber_count(self, event_type: str) -> int:
        """Gibt Anzahl Subscriber für einen Event-Typ zurück."""
        return len(self._subscribers.get(event_type, []))
        
    def get_all_event_types(self) -> List[str]:
        """Gibt alle registrierten Event-Typen zurück."""
        return list(self._subscribers.keys())