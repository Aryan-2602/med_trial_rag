#!/usr/bin/env python3
"""Diagnostic script to check vector DB status and test search."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.vector_db import VectorDBClient
from src.utils.config import Config
from src.retrieval.vector_db_retriever import VectorDBRetriever

def main():
    print("🔍 Vector DB Diagnostic Tool\n")
    
    # Check environment
    os.environ["USE_LOCAL_MODE"] = "1"
    config = Config.from_env()
    
    if not config.openai_api_key:
        print("❌ OPENAI_API_KEY not set!")
        print("   Set it with: export OPENAI_API_KEY=sk-your-key-here")
        return 1
    
    print(f"✅ OpenAI API key: {config.openai_api_key[:10]}...")
    print(f"✅ Embedding model: {config.embed_model}")
    print()
    
    # Check vector DB
    try:
        client = VectorDBClient(config)
        collection = client.get_or_create_collection()
        count = collection.count()
        
        print(f"📊 Vector DB Status:")
        print(f"   Collection: {client.collection_name}")
        print(f"   Document count: {count}")
        print()
        
        if count == 0:
            print("❌ Vector DB is EMPTY!")
            print("   You need to build PDF indices first:")
            print("   make build-pdf-indices-local")
            return 1
        
        # Get sample documents
        print("📄 Sample documents:")
        sample = collection.get(limit=3)
        for i, (doc_id, doc_text) in enumerate(zip(sample["ids"], sample["documents"]), 1):
            print(f"   {i}. ID: {doc_id}")
            print(f"      Text: {doc_text[:100]}...")
        print()
        
        # Test search
        print("🔍 Testing search...")
        test_queries = [
            "inclusion criteria",
            "exclusion criteria",
            "study design",
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=3
                )
                
                if results["ids"] and len(results["ids"][0]) > 0:
                    print(f"   ✅ Found {len(results['ids'][0])} results")
                    print(f"      Top distance: {results['distances'][0][0]:.4f}")
                    print(f"      Top similarity: {1.0 - results['distances'][0][0]:.4f}")
                    print(f"      Top result: {results['documents'][0][0][:80]}...")
                else:
                    print(f"   ❌ No results found")
            except Exception as e:
                print(f"   ❌ Search failed: {e}")
        
        print()
        
        # Test retriever
        print("🧪 Testing VectorDBRetriever...")
        retriever = VectorDBRetriever(config)
        retriever.load()
        
        test_query = "what are the inclusion criteria"
        results = retriever.search(test_query, top_k=3)
        
        print(f"   Query: '{test_query}'")
        print(f"   Results: {len(results)}")
        if results:
            print(f"   ✅ Top result score: {results[0]['score']:.4f}")
            print(f"      Top result text: {results[0]['text'][:100]}...")
        else:
            print(f"   ❌ No results returned")
        
        print()
        print("✅ Diagnostic complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

