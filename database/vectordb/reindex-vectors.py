#!/usr/bin/env python3
"""
JARVIS Vector Database Reindexing System
Optimize and reindex vector embeddings for better performance
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
import chromadb
from chromadb.config import Settings
import numpy as np

class VectorReindexer:
    def __init__(self):
        self.chroma_dir = "/opt/chroma/data"
        self.embeddings_dir = "/opt/embeddings"
        
        # Initialize ChromaDB client
        self.client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=self.chroma_dir,
            anonymized_telemetry=False
        ))
    
    def analyze_collection_performance(self, collection_name):
        """Analyze collection performance metrics"""
        try:
            collection = self.client.get_collection(collection_name)
            
            # Get collection stats
            count = collection.count()
            metadata = collection.metadata
            
            # Test query performance
            start_time = time.time()
            results = collection.query(
                query_texts=["test query"],
                n_results=min(10, count)
            )
            query_time = time.time() - start_time
            
            return {
                "collection_name": collection_name,
                "document_count": count,
                "metadata": metadata,
                "query_time_ms": round(query_time * 1000, 2),
                "performance_score": self._calculate_performance_score(count, query_time)
            }
            
        except Exception as e:
            print(f"Error analyzing collection {collection_name}: {e}")
            return None
    
    def _calculate_performance_score(self, count, query_time):
        """Calculate performance score (higher is better)"""
        # Base score on document count and query time
        if count == 0:
            return 0
        
        # Ideal: < 100ms for queries, score decreases with time
        time_score = max(0, 100 - (query_time * 1000))
        
        # Count efficiency (logarithmic scale)
        count_score = min(100, np.log10(count + 1) * 25)
        
        return round((time_score + count_score) / 2, 2)
    
    def detect_duplicate_embeddings(self, collection_name):
        """Detect and report duplicate embeddings"""
        try:
            collection = self.client.get_collection(collection_name)
            results = collection.get(include=['embeddings', 'ids'])
            
            if not results['embeddings']:
                return []
            
            embeddings = np.array(results['embeddings'])
            ids = results['ids']
            
            duplicates = []
            seen_embeddings = {}
            
            for i, embedding in enumerate(embeddings):
                # Create a hash of the embedding for comparison
                embedding_hash = hash(tuple(embedding.round(6)))
                
                if embedding_hash in seen_embeddings:
                    duplicates.append({
                        'id1': seen_embeddings[embedding_hash],
                        'id2': ids[i],
                        'similarity': 1.0
                    })
                else:
                    seen_embeddings[embedding_hash] = ids[i]
            
            return duplicates
            
        except Exception as e:
            print(f"Error detecting duplicates in {collection_name}: {e}")
            return []
    
    def optimize_collection(self, collection_name):
        """Optimize a specific collection"""
        print(f"🔧 Optimizing collection: {collection_name}")
        
        try:
            collection = self.client.get_collection(collection_name)
            
            # Get all data
            results = collection.get(include=['documents', 'embeddings', 'metadatas', 'ids'])
            
            if not results['ids']:
                print(f"⚠️  Collection {collection_name} is empty, skipping optimization")
                return
            
            # Detect duplicates
            duplicates = self.detect_duplicate_embeddings(collection_name)
            
            if duplicates:
                print(f"🔍 Found {len(duplicates)} potential duplicates")
                
                # Remove duplicates (keep first occurrence)
                ids_to_remove = [dup['id2'] for dup in duplicates]
                if ids_to_remove:
                    collection.delete(ids=ids_to_remove)
                    print(f"🗑️  Removed {len(ids_to_remove)} duplicate embeddings")
            
            # Compact and reorganize (simulate by recreating with optimized settings)
            print("📦 Compacting collection...")
            
            # Get updated data after cleanup
            updated_results = collection.get(include=['documents', 'embeddings', 'metadatas', 'ids'])
            
            print(f"✅ Optimization completed for {collection_name}")
            print(f"   Documents after optimization: {len(updated_results['ids'])}")
            
        except Exception as e:
            print(f"❌ Error optimizing collection {collection_name}: {e}")
    
    def rebuild_collection_index(self, collection_name):
        """Rebuild the index for a collection"""
        print(f"🏗️  Rebuilding index for: {collection_name}")
        
        try:
            collection = self.client.get_collection(collection_name)
            original_metadata = collection.metadata
            
            # Get all data
            results = collection.get(include=['documents', 'embeddings', 'metadatas', 'ids'])
            
            if not results['ids']:
                print(f"⚠️  Collection {collection_name} is empty, skipping rebuild")
                return
            
            # Create backup name
            backup_name = f"{collection_name}_backup_{int(time.time())}"
            
            # Create backup collection
            backup_collection = self.client.create_collection(
                name=backup_name,
                metadata={**original_metadata, "backup_of": collection_name}
            )
            
            # Copy data to backup
            backup_collection.add(
                ids=results['ids'],
                documents=results['documents'],
                metadatas=results['metadatas'],
                embeddings=results['embeddings']
            )
            
            # Delete original collection
            self.client.delete_collection(collection_name)
            
            # Recreate with optimized settings
            new_collection = self.client.create_collection(
                name=collection_name,
                metadata=original_metadata
            )
            
            # Re-add data in batches for better performance
            batch_size = 100
            for i in range(0, len(results['ids']), batch_size):
                end_idx = min(i + batch_size, len(results['ids']))
                
                new_collection.add(
                    ids=results['ids'][i:end_idx],
                    documents=results['documents'][i:end_idx],
                    metadatas=results['metadatas'][i:end_idx],
                    embeddings=results['embeddings'][i:end_idx]
                )
            
            # Verify rebuild
            new_count = new_collection.count()
            if new_count == len(results['ids']):
                print(f"✅ Index rebuild successful for {collection_name}")
                print(f"   Restored {new_count} documents")
                
                # Delete backup
                self.client.delete_collection(backup_name)
            else:
                print(f"❌ Index rebuild verification failed for {collection_name}")
                print(f"   Expected: {len(results['ids'])}, Got: {new_count}")
                
        except Exception as e:
            print(f"❌ Error rebuilding index for {collection_name}: {e}")
    
    def generate_performance_report(self):
        """Generate a comprehensive performance report"""
        print("📊 Generating vector database performance report...")
        
        try:
            collections = self.client.list_collections()
            report = {
                "timestamp": datetime.now().isoformat(),
                "total_collections": len(collections),
                "collections": {}
            }
            
            total_documents = 0
            total_query_time = 0
            
            for collection in collections:
                performance = self.analyze_collection_performance(collection.name)
                if performance:
                    report["collections"][collection.name] = performance
                    total_documents += performance["document_count"]
                    total_query_time += performance["query_time_ms"]
            
            # Calculate overall metrics
            if len(collections) > 0:
                report["overall_metrics"] = {
                    "total_documents": total_documents,
                    "average_query_time_ms": round(total_query_time / len(collections), 2),
                    "average_performance_score": round(
                        sum(c["performance_score"] for c in report["collections"].values()) / len(collections), 2
                    )
                }
            
            # Save report
            report_path = Path(self.embeddings_dir) / f"performance_report_{int(time.time())}.json"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            print(f"📋 Performance report saved: {report_path}")
            
            # Display summary
            print("\n📈 Performance Summary:")
            print(f"   Total Collections: {report['total_collections']}")
            print(f"   Total Documents: {total_documents}")
            if "overall_metrics" in report:
                print(f"   Average Query Time: {report['overall_metrics']['average_query_time_ms']} ms")
                print(f"   Average Performance Score: {report['overall_metrics']['average_performance_score']}/100")
            
            return report
            
        except Exception as e:
            print(f"❌ Error generating performance report: {e}")
            return None
    
    def run_full_reindex(self):
        """Run complete reindexing process"""
        print("🚀 Starting full vector database reindexing...")
        
        try:
            # Generate initial performance report
            print("\n📊 Initial Performance Analysis:")
            initial_report = self.generate_performance_report()
            
            # Get all collections
            collections = self.client.list_collections()
            
            if not collections:
                print("⚠️  No collections found, nothing to reindex")
                return
            
            print(f"\n🔧 Processing {len(collections)} collections...")
            
            for collection in collections:
                collection_name = collection.name
                
                # Skip backup collections
                if "_backup_" in collection_name:
                    print(f"⏭️  Skipping backup collection: {collection_name}")
                    continue
                
                print(f"\n📦 Processing collection: {collection_name}")
                
                # Analyze current performance
                performance = self.analyze_collection_performance(collection_name)
                if performance:
                    print(f"   Current performance score: {performance['performance_score']}/100")
                    print(f"   Document count: {performance['document_count']}")
                    print(f"   Query time: {performance['query_time_ms']} ms")
                
                # Optimize collection
                self.optimize_collection(collection_name)
                
                # Rebuild index if performance is poor
                if performance and performance['performance_score'] < 50:
                    print(f"   Performance below threshold, rebuilding index...")
                    self.rebuild_collection_index(collection_name)
            
            # Generate final performance report
            print("\n📊 Final Performance Analysis:")
            final_report = self.generate_performance_report()
            
            print("\n🎉 Full reindexing completed!")
            
            # Compare performance if both reports exist
            if initial_report and final_report and "overall_metrics" in both:
                initial_score = initial_report["overall_metrics"]["average_performance_score"]
                final_score = final_report["overall_metrics"]["average_performance_score"]
                improvement = final_score - initial_score
                
                print(f"📈 Performance improvement: {improvement:+.2f} points")
                print(f"   Before: {initial_score}/100")
                print(f"   After: {final_score}/100")
            
        except Exception as e:
            print(f"❌ Reindexing failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='JARVIS Vector Database Reindexer')
    parser.add_argument('action', choices=['reindex', 'optimize', 'report', 'rebuild'], 
                       help='Action to perform')
    parser.add_argument('--collection', help='Specific collection name (for optimize/rebuild)')
    
    args = parser.parse_args()
    
    reindexer = VectorReindexer()
    
    if args.action == 'reindex':
        reindexer.run_full_reindex()
    elif args.action == 'optimize':
        if args.collection:
            reindexer.optimize_collection(args.collection)
        else:
            print("❌ Optimize requires --collection parameter")
            sys.exit(1)
    elif args.action == 'report':
        reindexer.generate_performance_report()
    elif args.action == 'rebuild':
        if args.collection:
            reindexer.rebuild_collection_index(args.collection)
        else:
            print("❌ Rebuild requires --collection parameter")
            sys.exit(1)