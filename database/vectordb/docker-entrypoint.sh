#!/bin/bash
# JARVIS Vector Database (ChromaDB) Entrypoint
set -e

echo "🤖 Starting JARVIS Vector Database (ChromaDB)..."

# Set environment variables
export CHROMA_HOST=${CHROMA_HOST:-0.0.0.0}
export CHROMA_PORT=${CHROMA_PORT:-8000}
export CHROMA_LOG_LEVEL=${CHROMA_LOG_LEVEL:-INFO}
export PERSIST_DIRECTORY=${PERSIST_DIRECTORY:-/opt/chroma/data}
export CHROMA_EMBEDDING_FUNCTION=${CHROMA_EMBEDDING_FUNCTION:-sentence-transformers/all-MiniLM-L6-v2}

# Create necessary directories
echo "📁 Setting up directories..."
mkdir -p /opt/chroma/data
mkdir -p /opt/chroma/embeddings
mkdir -p /opt/chroma/backups
mkdir -p /opt/embeddings
mkdir -p /opt/init

# Set ownership (ignore errors for mounted files)
chown -R chroma:chroma /opt/chroma 2>/dev/null || echo "Warning: Could not change ownership of /opt/chroma"
chown -R chroma:chroma /opt/embeddings 2>/dev/null || echo "Warning: Could not change ownership of /opt/embeddings"

# Initialize collections if first run
if [ ! -f "/opt/chroma/data/.initialized" ]; then
    echo "🔄 First time setup - initializing collections..."
    
    # Wait a moment for any setup
    sleep 2
    
    # Run initialization script
    if [ -f "/opt/init/init_collections.py" ]; then
        echo "📚 Initializing vector collections..."
        python3 /opt/init/init_collections.py
    fi
    
    # Mark as initialized
    touch /opt/chroma/data/.initialized
    chown chroma:chroma /opt/chroma/data/.initialized
    
    echo "✅ Vector database initialization completed"
else
    echo "✅ Vector database already initialized"
fi

# Health check function
health_check() {
    echo "🏥 Running health check..."
    
    # Check if ChromaDB is responding
    if curl -f -s "http://localhost:${CHROMA_PORT}/api/v1/heartbeat" > /dev/null 2>&1; then
        echo "✅ ChromaDB health check passed"
        return 0
    else
        echo "❌ ChromaDB health check failed"
        return 1
    fi
}

# Wait for dependencies
echo "⏳ Waiting for dependencies..."
sleep 5

# Start ChromaDB server
echo "🚀 Starting ChromaDB server..."
echo "   Host: ${CHROMA_HOST}"
echo "   Port: ${CHROMA_PORT}"
echo "   Data Directory: ${PERSIST_DIRECTORY}"
echo "   Embedding Function: ${CHROMA_EMBEDDING_FUNCTION}"

# Switch to chroma user and start server
exec gosu chroma python3 -m chromadb.cli.cli run \
    --host "${CHROMA_HOST}" \
    --port "${CHROMA_PORT}" \
    --log-config /opt/chroma/logging.yaml \
    --log-level "${CHROMA_LOG_LEVEL}"