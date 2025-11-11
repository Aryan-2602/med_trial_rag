#!/usr/bin/env python3
"""
Check if dummy clinical trial tables exist, and create them if they don't.

This script is designed to be called automatically during app startup
to ensure tables exist for new users cloning the repository.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.config import Config

try:
    import mysql.connector
except ImportError:
    print("⚠️  mysql-connector-python not installed. Skipping table check.")
    print("   Install with: pip install mysql-connector-python")
    sys.exit(0)  # Exit gracefully, don't block startup


def check_tables_exist(cursor) -> bool:
    """Check if dummy clinical trial tables exist."""
    required_tables = [
        'sites', 'patients', 'comorbidities', 'prior_therapies',
        'treatment_cycles', 'visits', 'adverse_events', 'lab_results',
        'vitals', 'physician_notes', 'behavioral_adherence',
        'sae_reconciliation', 'documentation_metadata', 'pk_data',
        'fda_audit_risk_scores'
    ]
    
    cursor.execute("SHOW TABLES")
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    # Check if at least the core tables exist
    core_tables = ['sites', 'patients', 'adverse_events', 'visits']
    has_core_tables = any(table in existing_tables for table in core_tables)
    
    return has_core_tables


def check_has_data(cursor) -> bool:
    """Check if tables have data."""
    try:
        cursor.execute("SELECT COUNT(*) FROM patients LIMIT 1")
        patient_count = cursor.fetchone()[0]
        return patient_count > 0
    except Exception:
        return False


def main() -> int:
    """
    Check if dummy tables exist and create them if needed.
    
    Returns:
        0 if tables exist or were created successfully
        1 if there was an error
    """
    try:
        # Get MySQL connection parameters from environment
        import os
        mysql_host = os.getenv("MYSQL_HOST", "localhost")
        mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
        mysql_user = os.getenv("MYSQL_USER", "root")
        mysql_password = os.getenv("MYSQL_PASSWORD") or os.getenv("MYSQL_PWD", "")
        mysql_db = os.getenv("MYSQL_DB", "cotrial_rag")
        
        if not mysql_password:
            print("⚠️  MYSQL_PASSWORD not set. Skipping table check.")
            return 0  # Exit gracefully
        
        # Connect to MySQL
        conn = mysql.connector.connect(
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db,
        )
        cursor = conn.cursor()
        
        # Check if tables exist
        tables_exist = check_tables_exist(cursor)
        has_data = False
        
        if tables_exist:
            has_data = check_has_data(cursor)
        
        cursor.close()
        conn.close()
        
        if tables_exist and has_data:
            print("✅ Dummy clinical trial tables exist and contain data")
            return 0
        elif tables_exist and not has_data:
            print("⚠️  Dummy clinical trial tables exist but are empty")
            print("   Run: make create-dummy-data")
            return 1  # Return 1 to indicate tables need data
        else:
            print("⚠️  Dummy clinical trial tables not found")
            print("   Run: make create-dummy-data")
            return 1  # Return 1 to indicate tables need to be created
            
    except mysql.connector.Error as e:
        print(f"❌ MySQL error: {e}")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

