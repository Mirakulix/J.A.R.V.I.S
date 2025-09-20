#!/usr/bin/env python3
"""JARVIS Core Service"""
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="JARVIS Core", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "JARVIS Core Service", "status": "running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
