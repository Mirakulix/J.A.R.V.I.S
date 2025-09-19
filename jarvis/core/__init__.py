"""
J.A.R.V.I.S. Core AI Module
==========================

Central orchestration and coordination layer for the J.A.R.V.I.S. AI system.
Provides event-driven communication, context management, and module coordination.
"""

from .event_bus import EventBus
from .context_manager import ContextManager
from .task_scheduler import TaskScheduler
from .safety_controller import SafetyController
from .jarvis_core import JarvisCore

__version__ = "1.0.0"
__author__ = "J.A.R.V.I.S. Development Team"

__all__ = [
    "EventBus",
    "ContextManager", 
    "TaskScheduler",
    "SafetyController",
    "JarvisCore"
]