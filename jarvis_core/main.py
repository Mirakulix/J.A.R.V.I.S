#!/usr/bin/env python3
"""JARVIS Core Main Entry Point"""

if __name__ == "__main__":
    from jarvis_core.app import app
    import uvicorn
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info",
        reload=False
    )