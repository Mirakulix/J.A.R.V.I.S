#!/usr/bin/env python3
"""
JARVIS Vector Database Initialization
Initialize ChromaDB collections for different data types
"""

import chromadb
import json
import os
from chromadb.config import Settings

def initialize_collections():
    """Initialize all required ChromaDB collections"""
    
    # Connect to ChromaDB with new client architecture
    client = chromadb.PersistentClient(
        path="/opt/chroma/data",
        settings=Settings(anonymized_telemetry=False)
    )
    
    collections = [
        {
            "name": "jarvis_codebase",
            "metadata": {
                "description": "Code files and documentation",
                "embedding_function": "all-MiniLM-L6-v2",
                "data_type": "code"
            }
        },
        {
            "name": "jarvis_skills", 
            "metadata": {
                "description": "AI skills and capabilities",
                "embedding_function": "all-MiniLM-L6-v2",
                "data_type": "skills"
            }
        },
        {
            "name": "jarvis_conversations",
            "metadata": {
                "description": "Chat history and conversations", 
                "embedding_function": "all-MiniLM-L6-v2",
                "data_type": "conversations"
            }
        },
        {
            "name": "jarvis_documents",
            "metadata": {
                "description": "Documents and knowledge base",
                "embedding_function": "all-MiniLM-L6-v2", 
                "data_type": "documents"
            }
        },
        {
            "name": "jarvis_tasks",
            "metadata": {
                "description": "Tasks and project management",
                "embedding_function": "all-MiniLM-L6-v2",
                "data_type": "tasks"
            }
        }
    ]
    
    print("Initializing JARVIS vector collections...")
    
    for collection_config in collections:
        try:
            # Try to get existing collection
            try:
                collection = client.get_collection(collection_config["name"])
                print(f"✅ Collection '{collection_config['name']}' already exists")
            except:
                # Create new collection
                collection = client.create_collection(
                    name=collection_config["name"],
                    metadata=collection_config["metadata"]
                )
                print(f"🆕 Created collection '{collection_config['name']}'")
                
                # Add sample data
                if collection_config["name"] == "jarvis_codebase":
                    collection.add(
                        documents=["# JARVIS AI Assistant\nA sophisticated multi-container AI development environment"],
                        metadatas=[{"file_type": "markdown", "source": "README.md"}],
                        ids=["readme_sample"]
                    )
                elif collection_config["name"] == "jarvis_skills":
                    collection.add(
                        documents=["Weather API skill for retrieving current weather information"],
                        metadatas=[{"skill_type": "api", "category": "weather"}],
                        ids=["weather_skill"]
                    )
                    
        except Exception as e:
            print(f"❌ Error with collection '{collection_config['name']}': {e}")
    
    print("Vector database initialization completed!")

if __name__ == "__main__":
    initialize_collections()