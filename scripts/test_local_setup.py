"""Test the local setup end-to-end."""

import os
import sys
from pathlib import Path

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.config import Config
from src.utils.mysql_client import MySQLClient

def test_mysql():
    """Test MySQL connection."""
    print("🔍 Testing MySQL connection...")
    try:
        config = Config.from_env()
        client = MySQLClient(config)
        if client.test_connection():
            print("✅ MySQL connection successful")
            
            # Check if tables exist
            result = client.execute_query("SHOW TABLES")
            tables = [list(row.values())[0] for row in result] if result else []
            print(f"   Found {len(tables)} tables: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
            return True
        else:
            print("❌ MySQL connection failed")
            return False
    except Exception as e:
        print(f"❌ MySQL error: {e}")
        return False


def test_pdf_indices():
    """Test if PDF indices exist."""
    print("\n🔍 Testing PDF indices...")
    try:
        config = Config.from_env()
        indices_path = Path(config.local_indices_path)
        manifest_path = Path(config.local_manifest_path)
        
        if not manifest_path.exists():
            print(f"❌ Manifest not found at {manifest_path}")
            return False
        
        print(f"✅ Manifest found at {manifest_path}")
        
        # Check if indices directory exists
        if not indices_path.exists():
            print(f"❌ Indices directory not found at {indices_path}")
            return False
        
        print(f"✅ Indices directory found at {indices_path}")
        
        # Check for PDF index
        pdf_indices = list(indices_path.glob("pdf_index/*/index.faiss"))
        if pdf_indices:
            print(f"✅ Found {len(pdf_indices)} PDF index(es)")
            for idx in pdf_indices:
                size_mb = idx.stat().st_size / (1024 * 1024)
                print(f"   - {idx.parent.name}: {size_mb:.2f} MB")
            return True
        else:
            print("❌ No PDF indices found")
            return False
    except Exception as e:
        print(f"❌ PDF indices error: {e}")
        return False


def test_api():
    """Test API endpoint."""
    print("\n🔍 Testing API...")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    try:
        # Test status endpoint
        response = requests.get(f"{api_url}/v1/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print("✅ API is running")
            print(f"   Retriever: {status.get('retriever', 'unknown')}")
            print(f"   Loaded: {status.get('loaded', False)}")
            print(f"   Corpora: {status.get('corpora', {})}")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {api_url}")
        print("   Make sure the API is running: make run")
        return False
    except Exception as e:
        print(f"❌ API error: {e}")
        return False


def test_chat():
    """Test chat endpoint."""
    print("\n🔍 Testing chat endpoint...")
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    try:
        response = requests.post(
            f"{api_url}/v1/chat",
            json={"query": "What are the inclusion criteria?", "top_k": 3},
            timeout=30,
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ Chat endpoint working")
            print(f"   Answer length: {len(result.get('answer', ''))} chars")
            print(f"   Sources: {len(result.get('sources', []))}")
            return True
        else:
            print(f"❌ Chat returned status {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Chat error: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Testing Local Setup\n")
    print("=" * 50)
    
    # Check environment
    use_local = os.getenv("USE_LOCAL_MODE", "0") == "1"
    if not use_local:
        print("⚠️  USE_LOCAL_MODE is not set to '1'")
        print("   Set it with: export USE_LOCAL_MODE=1")
        print()
    
    results = []
    
    # Test MySQL
    results.append(("MySQL", test_mysql()))
    
    # Test PDF indices
    results.append(("PDF Indices", test_pdf_indices()))
    
    # Test API
    results.append(("API", test_api()))
    
    # Test chat (only if API is up)
    if results[-1][1]:  # If API test passed
        results.append(("Chat", test_chat()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {status}: {name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 All tests passed! Your local setup is ready.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\nNext steps:")
        if not results[0][1]:  # MySQL failed
            print("   1. Make sure MySQL is running on your local machine")
            print("   2. Create database: mysql -u root -p -e 'CREATE DATABASE cotrial_rag;'")
            print("   3. Set MYSQL_PASSWORD environment variable")
            print("   4. Migrate SAS data: make migrate-sas")
        if not results[1][1]:  # PDF indices failed
            print("   3. Build PDF indices: make build-pdf-indices")
        if not results[2][1]:  # API failed
            print("   4. Start API: make run")


if __name__ == "__main__":
    main()

