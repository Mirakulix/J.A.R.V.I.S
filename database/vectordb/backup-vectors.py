#!/usr/bin/env python3
"""
JARVIS Vector Database Backup System
Backup and restore ChromaDB collections with embeddings
"""

import os
import sys
import json
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path
import chromadb
from chromadb.config import Settings

class VectorBackup:
    def __init__(self):
        self.chroma_dir = "/opt/chroma/data"
        self.backup_dir = "/opt/chroma/backups"
        self.embeddings_dir = "/opt/embeddings"
        
        # Ensure backup directory exists
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.chroma_dir,
            anonymized_telemetry=False
        ))
    
    def get_collections_metadata(self):
        """Get metadata for all collections"""
        try:
            collections = self.client.list_collections()
            metadata = {}
            
            for collection in collections:
                collection_info = {
                    "name": collection.name,
                    "metadata": collection.metadata,
                    "count": collection.count()
                }
                metadata[collection.name] = collection_info
                
            return metadata
        except Exception as e:
            print(f"Error getting collections metadata: {e}")
            return {}
    
    def export_collection_data(self, collection_name):
        """Export all data from a collection"""
        try:
            collection = self.client.get_collection(collection_name)
            
            # Get all documents
            results = collection.get(include=['documents', 'embeddings', 'metadatas'])
            
            return {
                "collection_name": collection_name,
                "metadata": collection.metadata,
                "count": collection.count(),
                "data": {
                    "ids": results['ids'],
                    "documents": results['documents'],
                    "metadatas": results['metadatas'],
                    "embeddings": results['embeddings']
                }
            }
        except Exception as e:
            print(f"Error exporting collection {collection_name}: {e}")
            return None
    
    def create_backup(self):
        """Create a complete backup of the vector database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"jarvis_vectors_backup_{timestamp}"
        backup_path = Path(self.backup_dir) / backup_name
        
        print(f"🔄 Creating vector database backup: {backup_name}")
        
        try:
            # Create backup directory
            backup_path.mkdir(exist_ok=True)
            
            # Get collections metadata
            metadata = self.get_collections_metadata()
            
            # Save metadata
            with open(backup_path / "collections_metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2, default=str)
            
            # Export each collection
            collections_data = {}
            for collection_name in metadata.keys():
                print(f"📦 Exporting collection: {collection_name}")
                collection_data = self.export_collection_data(collection_name)
                
                if collection_data:
                    collections_data[collection_name] = collection_data
                    
                    # Save individual collection data
                    with open(backup_path / f"{collection_name}.json", 'w') as f:
                        json.dump(collection_data, f, indent=2, default=str)
            
            # Copy ChromaDB files
            print("💾 Copying ChromaDB files...")
            if os.path.exists(self.chroma_dir):
                shutil.copytree(self.chroma_dir, backup_path / "chroma_data", dirs_exist_ok=True)
            
            # Copy embeddings directory
            if os.path.exists(self.embeddings_dir):
                shutil.copytree(self.embeddings_dir, backup_path / "embeddings", dirs_exist_ok=True)
            
            # Create compressed archive
            print("🗜️  Creating compressed archive...")
            archive_path = f"{backup_path}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(backup_path, arcname=backup_name)
            
            # Remove uncompressed backup
            shutil.rmtree(backup_path)
            
            # Calculate backup size
            backup_size = os.path.getsize(archive_path) / (1024 * 1024)  # MB
            
            print(f"✅ Backup completed: {archive_path}")
            print(f"📊 Backup size: {backup_size:.2f} MB")
            print(f"📈 Collections backed up: {len(metadata)}")
            
            return archive_path
            
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None
    
    def cleanup_old_backups(self, retention_days=30):
        """Remove backups older than retention period"""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            removed_count = 0
            
            for backup_file in Path(self.backup_dir).glob("jarvis_vectors_backup_*.tar.gz"):
                # Extract timestamp from filename
                try:
                    timestamp_str = backup_file.stem.split('_')[-2] + '_' + backup_file.stem.split('_')[-1]
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        backup_file.unlink()
                        removed_count += 1
                        print(f"🗑️  Removed old backup: {backup_file.name}")
                        
                except (ValueError, IndexError):
                    print(f"⚠️  Skipping file with invalid format: {backup_file.name}")
            
            print(f"🧹 Cleanup completed: {removed_count} old backups removed")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
    
    def restore_backup(self, backup_path):
        """Restore from a backup archive"""
        print(f"🔄 Restoring vector database from: {backup_path}")
        
        try:
            # Extract backup
            extract_dir = Path(self.backup_dir) / "restore_temp"
            extract_dir.mkdir(exist_ok=True)
            
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(extract_dir)
            
            # Find the backup directory
            backup_contents = list(extract_dir.iterdir())
            if not backup_contents:
                raise Exception("Empty backup archive")
            
            restore_path = backup_contents[0]
            
            # Stop ChromaDB (if running)
            print("⏸️  Stopping ChromaDB...")
            
            # Restore ChromaDB data
            if (restore_path / "chroma_data").exists():
                print("💾 Restoring ChromaDB data...")
                if os.path.exists(self.chroma_dir):
                    shutil.rmtree(self.chroma_dir)
                shutil.copytree(restore_path / "chroma_data", self.chroma_dir)
            
            # Restore embeddings
            if (restore_path / "embeddings").exists():
                print("🧠 Restoring embeddings...")
                if os.path.exists(self.embeddings_dir):
                    shutil.rmtree(self.embeddings_dir)
                shutil.copytree(restore_path / "embeddings", self.embeddings_dir)
            
            # Clean up
            shutil.rmtree(extract_dir)
            
            print("✅ Restore completed successfully")
            print("🔄 Please restart ChromaDB service")
            
        except Exception as e:
            print(f"❌ Restore failed: {e}")
    
    def run_backup(self):
        """Run the backup process"""
        try:
            # Create backup
            backup_path = self.create_backup()
            
            if backup_path:
                # Cleanup old backups
                self.cleanup_old_backups()
                print("🎉 Vector database backup completed successfully!")
            else:
                print("❌ Backup process failed")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Backup process error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='JARVIS Vector Database Backup')
    parser.add_argument('action', choices=['backup', 'restore'], help='Action to perform')
    parser.add_argument('--file', help='Backup file path for restore')
    
    args = parser.parse_args()
    
    backup_system = VectorBackup()
    
    if args.action == 'backup':
        backup_system.run_backup()
    elif args.action == 'restore':
        if not args.file:
            print("❌ Restore requires --file parameter")
            sys.exit(1)
        backup_system.restore_backup(args.file)