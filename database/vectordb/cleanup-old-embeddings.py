#!/usr/bin/env python3
"""
JARVIS Vector Database Cleanup System
Clean up old, unused, and orphaned embeddings
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
import chromadb
from chromadb.config import Settings

class VectorCleaner:
    def __init__(self):
        self.chroma_dir = "/opt/chroma/data"
        self.embeddings_dir = "/opt/embeddings"
        self.backup_dir = "/opt/chroma/backups"
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.chroma_dir,
            anonymized_telemetry=False
        ))
    
    def find_orphaned_embeddings(self):
        """Find embedding files not referenced in any collection"""
        orphaned_files = []
        
        try:
            if not os.path.exists(self.embeddings_dir):
                return orphaned_files
            
            # Get all embedding files
            embedding_files = []
            for root, dirs, files in os.walk(self.embeddings_dir):
                for file in files:
                    if file.endswith(('.json', '.npy', '.pkl')):
                        embedding_files.append(os.path.join(root, file))
            
            # Get all collections and their referenced embeddings
            collections = self.client.list_collections()
            referenced_embeddings = set()
            
            for collection in collections:
                try:
                    results = collection.get(include=['metadatas'])
                    for metadata in results.get('metadatas', []):
                        if metadata and 'embedding_file' in metadata:
                            referenced_embeddings.add(metadata['embedding_file'])
                except Exception as e:
                    print(f"Warning: Error checking collection {collection.name}: {e}")
            
            # Find orphaned files
            for file_path in embedding_files:
                file_name = os.path.basename(file_path)
                if file_name not in referenced_embeddings:
                    orphaned_files.append(file_path)
            
            return orphaned_files
            
        except Exception as e:
            print(f"Error finding orphaned embeddings: {e}")
            return []
    
    def find_stale_documents(self, days_threshold=90):
        """Find documents that haven't been accessed recently"""
        stale_documents = []
        cutoff_date = datetime.now() - timedelta(days=days_threshold)
        
        try:
            collections = self.client.list_collections()
            
            for collection in collections:
                try:
                    results = collection.get(include=['metadatas', 'ids'])
                    
                    for i, metadata in enumerate(results.get('metadatas', [])):
                        if not metadata:
                            continue
                        
                        # Check last access time
                        last_access = metadata.get('last_accessed')
                        created_at = metadata.get('created_at')
                        
                        # Use created_at if last_accessed is not available
                        check_date = last_access or created_at
                        
                        if check_date:
                            try:
                                doc_date = datetime.fromisoformat(check_date.replace('Z', '+00:00'))
                                if doc_date < cutoff_date:
                                    stale_documents.append({
                                        'collection': collection.name,
                                        'id': results['ids'][i],
                                        'last_accessed': check_date,
                                        'age_days': (datetime.now() - doc_date.replace(tzinfo=None)).days
                                    })
                            except (ValueError, AttributeError):
                                # If date parsing fails, consider it potentially stale
                                stale_documents.append({
                                    'collection': collection.name,
                                    'id': results['ids'][i],
                                    'last_accessed': 'unknown',
                                    'age_days': 'unknown'
                                })
                
                except Exception as e:
                    print(f"Warning: Error checking collection {collection.name}: {e}")
            
            return stale_documents
            
        except Exception as e:
            print(f"Error finding stale documents: {e}")
            return []
    
    def find_duplicate_documents(self):
        """Find documents with identical content"""
        duplicates = []
        
        try:
            collections = self.client.list_collections()
            
            for collection in collections:
                try:
                    results = collection.get(include=['documents', 'ids'])
                    documents = results.get('documents', [])
                    ids = results.get('ids', [])
                    
                    # Track seen documents
                    seen_docs = {}
                    
                    for i, doc in enumerate(documents):
                        if doc in seen_docs:
                            duplicates.append({
                                'collection': collection.name,
                                'duplicate_id': ids[i],
                                'original_id': seen_docs[doc],
                                'content_hash': hash(doc)
                            })
                        else:
                            seen_docs[doc] = ids[i]
                
                except Exception as e:
                    print(f"Warning: Error checking collection {collection.name}: {e}")
            
            return duplicates
            
        except Exception as e:
            print(f"Error finding duplicate documents: {e}")
            return []
    
    def clean_orphaned_embeddings(self, orphaned_files):
        """Clean up orphaned embedding files"""
        if not orphaned_files:
            print("✅ No orphaned embedding files found")
            return 0
        
        cleaned_count = 0
        total_size_mb = 0
        
        print(f"🧹 Cleaning {len(orphaned_files)} orphaned embedding files...")
        
        for file_path in orphaned_files:
            try:
                # Calculate file size
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                total_size_mb += file_size
                
                # Remove file
                os.remove(file_path)
                cleaned_count += 1
                
                print(f"   🗑️  Removed: {os.path.basename(file_path)} ({file_size:.2f} MB)")
                
            except Exception as e:
                print(f"   ❌ Error removing {file_path}: {e}")
        
        print(f"📊 Cleaned up {cleaned_count} files, freed {total_size_mb:.2f} MB")
        return cleaned_count
    
    def clean_stale_documents(self, stale_documents, confirm=True):
        """Clean up stale documents"""
        if not stale_documents:
            print("✅ No stale documents found")
            return 0
        
        if confirm:
            print(f"⚠️  Found {len(stale_documents)} stale documents")
            response = input("Do you want to remove them? (y/N): ")
            if response.lower() != 'y':
                print("Cleanup cancelled")
                return 0
        
        cleaned_count = 0
        collections_affected = {}
        
        print(f"🧹 Cleaning {len(stale_documents)} stale documents...")
        
        for doc_info in stale_documents:
            try:
                collection = self.client.get_collection(doc_info['collection'])
                collection.delete(ids=[doc_info['id']])
                
                cleaned_count += 1
                collections_affected[doc_info['collection']] = collections_affected.get(doc_info['collection'], 0) + 1
                
                print(f"   🗑️  Removed stale document: {doc_info['id']} (age: {doc_info['age_days']} days)")
                
            except Exception as e:
                print(f"   ❌ Error removing document {doc_info['id']}: {e}")
        
        print(f"📊 Cleaned up {cleaned_count} stale documents from {len(collections_affected)} collections")
        return cleaned_count
    
    def clean_duplicate_documents(self, duplicates, confirm=True):
        """Clean up duplicate documents"""
        if not duplicates:
            print("✅ No duplicate documents found")
            return 0
        
        if confirm:
            print(f"⚠️  Found {len(duplicates)} duplicate documents")
            response = input("Do you want to remove duplicates? (y/N): ")
            if response.lower() != 'y':
                print("Cleanup cancelled")
                return 0
        
        cleaned_count = 0
        collections_affected = {}
        
        print(f"🧹 Cleaning {len(duplicates)} duplicate documents...")
        
        for dup_info in duplicates:
            try:
                collection = self.client.get_collection(dup_info['collection'])
                collection.delete(ids=[dup_info['duplicate_id']])
                
                cleaned_count += 1
                collections_affected[dup_info['collection']] = collections_affected.get(dup_info['collection'], 0) + 1
                
                print(f"   🗑️  Removed duplicate: {dup_info['duplicate_id']} (kept: {dup_info['original_id']})")
                
            except Exception as e:
                print(f"   ❌ Error removing duplicate {dup_info['duplicate_id']}: {e}")
        
        print(f"📊 Cleaned up {cleaned_count} duplicate documents from {len(collections_affected)} collections")
        return cleaned_count
    
    def clean_old_backups(self, retention_days=30):
        """Clean up old backup files"""
        if not os.path.exists(self.backup_dir):
            print("✅ No backup directory found")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        cleaned_count = 0
        total_size_mb = 0
        
        print(f"🧹 Cleaning backups older than {retention_days} days...")
        
        for backup_file in Path(self.backup_dir).glob("*"):
            try:
                # Check file modification time
                file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                
                if file_mtime < cutoff_date:
                    file_size = backup_file.stat().st_size / (1024 * 1024)  # MB
                    total_size_mb += file_size
                    
                    backup_file.unlink()
                    cleaned_count += 1
                    
                    print(f"   🗑️  Removed old backup: {backup_file.name} ({file_size:.2f} MB)")
                    
            except Exception as e:
                print(f"   ❌ Error removing {backup_file}: {e}")
        
        print(f"📊 Cleaned up {cleaned_count} old backups, freed {total_size_mb:.2f} MB")
        return cleaned_count
    
    def generate_cleanup_report(self):
        """Generate a cleanup analysis report"""
        print("📊 Generating cleanup analysis report...")
        
        try:
            # Find all cleanup candidates
            orphaned = self.find_orphaned_embeddings()
            stale = self.find_stale_documents()
            duplicates = self.find_duplicate_documents()
            
            report = {
                "timestamp": datetime.now().isoformat(),
                "analysis": {
                    "orphaned_embeddings": {
                        "count": len(orphaned),
                        "files": [os.path.basename(f) for f in orphaned[:10]]  # First 10
                    },
                    "stale_documents": {
                        "count": len(stale),
                        "threshold_days": 90,
                        "oldest_age": max([d.get('age_days', 0) for d in stale] + [0])
                    },
                    "duplicate_documents": {
                        "count": len(duplicates),
                        "affected_collections": len(set(d['collection'] for d in duplicates))
                    }
                },
                "recommendations": []
            }
            
            # Add recommendations
            if orphaned:
                report["recommendations"].append(f"Remove {len(orphaned)} orphaned embedding files")
            if stale:
                report["recommendations"].append(f"Clean up {len(stale)} stale documents")
            if duplicates:
                report["recommendations"].append(f"Remove {len(duplicates)} duplicate documents")
            
            if not (orphaned or stale or duplicates):
                report["recommendations"].append("No cleanup needed - database is optimized")
            
            # Save report
            report_path = Path(self.embeddings_dir) / f"cleanup_report_{int(time.time())}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"📋 Cleanup report saved: {report_path}")
            
            # Display summary
            print("\n🎯 Cleanup Summary:")
            print(f"   Orphaned embeddings: {len(orphaned)}")
            print(f"   Stale documents: {len(stale)}")
            print(f"   Duplicate documents: {len(duplicates)}")
            
            return report
            
        except Exception as e:
            print(f"❌ Error generating cleanup report: {e}")
            return None
    
    def run_full_cleanup(self, auto_confirm=False):
        """Run complete cleanup process"""
        print("🧹 Starting full vector database cleanup...")
        
        try:
            # Generate analysis report
            print("\n📊 Analyzing database for cleanup opportunities...")
            report = self.generate_cleanup_report()
            
            if not report:
                print("❌ Could not generate cleanup report")
                return
            
            total_cleaned = 0
            
            # Clean orphaned embeddings
            print("\n🗑️  Cleaning orphaned embedding files...")
            orphaned = self.find_orphaned_embeddings()
            total_cleaned += self.clean_orphaned_embeddings(orphaned)
            
            # Clean stale documents
            print("\n📅 Cleaning stale documents...")
            stale = self.find_stale_documents()
            total_cleaned += self.clean_stale_documents(stale, confirm=not auto_confirm)
            
            # Clean duplicates
            print("\n🔄 Cleaning duplicate documents...")
            duplicates = self.find_duplicate_documents()
            total_cleaned += self.clean_duplicate_documents(duplicates, confirm=not auto_confirm)
            
            # Clean old backups
            print("\n💾 Cleaning old backups...")
            total_cleaned += self.clean_old_backups()
            
            print(f"\n🎉 Cleanup completed! Total items cleaned: {total_cleaned}")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='JARVIS Vector Database Cleaner')
    parser.add_argument('action', choices=['cleanup', 'report', 'orphaned', 'stale', 'duplicates'], 
                       help='Action to perform')
    parser.add_argument('--auto-confirm', action='store_true', 
                       help='Automatically confirm cleanup actions')
    parser.add_argument('--days', type=int, default=90, 
                       help='Age threshold in days for stale documents')
    
    args = parser.parse_args()
    
    cleaner = VectorCleaner()
    
    if args.action == 'cleanup':
        cleaner.run_full_cleanup(auto_confirm=args.auto_confirm)
    elif args.action == 'report':
        cleaner.generate_cleanup_report()
    elif args.action == 'orphaned':
        orphaned = cleaner.find_orphaned_embeddings()
        cleaner.clean_orphaned_embeddings(orphaned)
    elif args.action == 'stale':
        stale = cleaner.find_stale_documents(days_threshold=args.days)
        cleaner.clean_stale_documents(stale, confirm=not args.auto_confirm)
    elif args.action == 'duplicates':
        duplicates = cleaner.find_duplicate_documents()
        cleaner.clean_duplicate_documents(duplicates, confirm=not args.auto_confirm)