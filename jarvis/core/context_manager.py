"""
Context Manager für J.A.R.V.I.S.
===============================

Verwaltet Konversationskontexte, Benutzersitzungen und Systemzustände.
Ermöglicht kontextuelle Intelligenz und personalisierte Interaktionen.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ContextScope(Enum):
    """Definiert verschiedene Kontext-Bereiche."""
    SESSION = "session"          # Aktuelle Sitzung
    USER = "user"               # Benutzerspezifisch
    GLOBAL = "global"           # Systemweit
    TASK = "task"               # Aufgabenspezifisch


@dataclass
class ContextEntry:
    """Einzelner Kontexteintrag."""
    key: str
    value: Any
    scope: ContextScope
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Prüft ob der Kontexteintrag abgelaufen ist."""
        if self.expires_at is None:
            return False
        return datetime.now() > self.expires_at


@dataclass 
class UserContext:
    """Benutzerspezifischer Kontext."""
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    
    def update_activity(self):
        """Aktualisiert letzte Aktivität."""
        self.last_activity = datetime.now()


class ContextManager:
    """
    Zentraler Context Manager für das J.A.R.V.I.S. System.
    
    Features:
    - Hierarchische Kontextverwaltung
    - Automatische Bereinigung abgelaufener Kontexte
    - Benutzer- und sitzungsspezifische Kontexte
    - Thread-sichere Operationen
    """
    
    def __init__(self, cleanup_interval: int = 300):
        self._contexts: Dict[str, Dict[str, ContextEntry]] = {
            ContextScope.SESSION.value: {},
            ContextScope.USER.value: {},
            ContextScope.GLOBAL.value: {},
            ContextScope.TASK.value: {}
        }
        self._user_contexts: Dict[str, UserContext] = {}
        self._sessions: Dict[str, str] = {}  # session_id -> user_id
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    async def start(self):
        """Startet den Context Manager."""
        if self._cleanup_task is not None:
            return
            
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Context Manager started")
        
    async def stop(self):
        """Stoppt den Context Manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Context Manager stopped")
        
    async def create_session(self, user_id: str) -> str:
        """
        Erstellt eine neue Sitzung.
        
        Args:
            user_id: Benutzer-ID
            
        Returns:
            Session-ID
        """
        async with self._lock:
            session_id = str(uuid.uuid4())
            self._sessions[session_id] = user_id
            
            # User Context erstellen falls nicht vorhanden
            if user_id not in self._user_contexts:
                self._user_contexts[user_id] = UserContext(user_id=user_id)
                
            self._user_contexts[user_id].update_activity()
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session_id
            
    async def end_session(self, session_id: str):
        """
        Beendet eine Sitzung.
        
        Args:
            session_id: Session-ID
        """
        async with self._lock:
            if session_id in self._sessions:
                user_id = self._sessions[session_id]
                del self._sessions[session_id]
                
                # Session-spezifische Kontexte löschen
                session_contexts = [
                    key for key in self._contexts[ContextScope.SESSION.value]
                    if key.startswith(f"{session_id}:")
                ]
                
                for key in session_contexts:
                    del self._contexts[ContextScope.SESSION.value][key]
                    
                logger.info(f"Ended session {session_id} for user {user_id}")
                
    async def set_context(self, key: str, value: Any, scope: ContextScope,
                         session_id: Optional[str] = None,
                         expires_in: Optional[timedelta] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Setzt einen Kontextwert.
        
        Args:
            key: Kontext-Schlüssel
            value: Wert
            scope: Kontext-Bereich
            session_id: Optional - Session-ID für session-spezifische Kontexte
            expires_in: Optional - Ablaufzeit
            metadata: Optional - Zusätzliche Metadaten
            
        Returns:
            True wenn erfolgreich gesetzt
        """
        try:
            async with self._lock:
                # Session-spezifische Schlüssel
                if scope == ContextScope.SESSION and session_id:
                    full_key = f"{session_id}:{key}"
                else:
                    full_key = key
                    
                expires_at = None
                if expires_in:
                    expires_at = datetime.now() + expires_in
                    
                entry = ContextEntry(
                    key=full_key,
                    value=value,
                    scope=scope,
                    expires_at=expires_at,
                    metadata=metadata or {}
                )
                
                self._contexts[scope.value][full_key] = entry
                
                logger.debug(f"Set context: {full_key} in scope {scope.value}")
                return True
                
        except Exception as e:
            logger.error(f"Error setting context {key}: {e}")
            return False
            
    async def get_context(self, key: str, scope: ContextScope,
                         session_id: Optional[str] = None,
                         default: Any = None) -> Any:
        """
        Holt einen Kontextwert.
        
        Args:
            key: Kontext-Schlüssel
            scope: Kontext-Bereich
            session_id: Optional - Session-ID
            default: Standard-Wert falls nicht gefunden
            
        Returns:
            Kontextwert oder default
        """
        try:
            async with self._lock:
                # Session-spezifische Schlüssel
                if scope == ContextScope.SESSION and session_id:
                    full_key = f"{session_id}:{key}"
                else:
                    full_key = key
                    
                scope_contexts = self._contexts.get(scope.value, {})
                entry = scope_contexts.get(full_key)
                
                if entry is None:
                    return default
                    
                if entry.is_expired():
                    # Abgelaufenen Eintrag löschen
                    del scope_contexts[full_key]
                    return default
                    
                return entry.value
                
        except Exception as e:
            logger.error(f"Error getting context {key}: {e}")
            return default
            
    async def remove_context(self, key: str, scope: ContextScope,
                           session_id: Optional[str] = None) -> bool:
        """
        Entfernt einen Kontexteintrag.
        
        Args:
            key: Kontext-Schlüssel
            scope: Kontext-Bereich
            session_id: Optional - Session-ID
            
        Returns:
            True wenn erfolgreich entfernt
        """
        try:
            async with self._lock:
                if scope == ContextScope.SESSION and session_id:
                    full_key = f"{session_id}:{key}"
                else:
                    full_key = key
                    
                scope_contexts = self._contexts.get(scope.value, {})
                if full_key in scope_contexts:
                    del scope_contexts[full_key]
                    logger.debug(f"Removed context: {full_key}")
                    return True
                    
                return False
                
        except Exception as e:
            logger.error(f"Error removing context {key}: {e}")
            return False
            
    async def get_user_context(self, user_id: str) -> Optional[UserContext]:
        """
        Holt den Benutzerkontext.
        
        Args:
            user_id: Benutzer-ID
            
        Returns:
            UserContext oder None
        """
        async with self._lock:
            return self._user_contexts.get(user_id)
            
    async def update_user_preference(self, user_id: str, 
                                   preference_key: str, 
                                   preference_value: Any) -> bool:
        """
        Aktualisiert eine Benutzereinstellung.
        
        Args:
            user_id: Benutzer-ID
            preference_key: Einstellungsschlüssel
            preference_value: Einstellungswert
            
        Returns:
            True wenn erfolgreich aktualisiert
        """
        try:
            async with self._lock:
                if user_id not in self._user_contexts:
                    self._user_contexts[user_id] = UserContext(user_id=user_id)
                    
                user_context = self._user_contexts[user_id]
                user_context.preferences[preference_key] = preference_value
                user_context.update_activity()
                
                logger.debug(f"Updated preference {preference_key} for user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating user preference: {e}")
            return False
            
    async def add_to_conversation_history(self, user_id: str, 
                                        message: Dict[str, Any]) -> bool:
        """
        Fügt Nachricht zur Konversationshistorie hinzu.
        
        Args:
            user_id: Benutzer-ID
            message: Nachrichten-Daten
            
        Returns:
            True wenn erfolgreich hinzugefügt
        """
        try:
            async with self._lock:
                if user_id not in self._user_contexts:
                    self._user_contexts[user_id] = UserContext(user_id=user_id)
                    
                user_context = self._user_contexts[user_id]
                message['timestamp'] = datetime.now().isoformat()
                user_context.conversation_history.append(message)
                
                # Historie begrenzen
                max_history = 1000
                if len(user_context.conversation_history) > max_history:
                    user_context.conversation_history = \
                        user_context.conversation_history[-max_history:]
                        
                user_context.update_activity()
                return True
                
        except Exception as e:
            logger.error(f"Error adding to conversation history: {e}")
            return False
            
    async def _cleanup_loop(self):
        """Bereinigung-Loop für abgelaufene Kontexte."""
        while True:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self._cleanup_expired_contexts()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
                
    async def _cleanup_expired_contexts(self):
        """Bereinigt abgelaufene Kontexte."""
        async with self._lock:
            total_removed = 0
            
            for scope_name, scope_contexts in self._contexts.items():
                expired_keys = [
                    key for key, entry in scope_contexts.items()
                    if entry.is_expired()
                ]
                
                for key in expired_keys:
                    del scope_contexts[key]
                    total_removed += 1
                    
            if total_removed > 0:
                logger.info(f"Cleaned up {total_removed} expired context entries")
                
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Context-Statistiken zurück."""
        stats = {
            'active_sessions': len(self._sessions),
            'user_contexts': len(self._user_contexts),
            'context_counts': {}
        }
        
        for scope_name, scope_contexts in self._contexts.items():
            stats['context_counts'][scope_name] = len(scope_contexts)
            
        return stats