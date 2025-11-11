"""Database initialization utilities."""

import mysql.connector
from typing import Any

from src.utils.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


def check_dummy_tables_exist(config: Config) -> tuple[bool, bool]:
    """
    Check if dummy clinical trial tables exist and have data.
    
    Args:
        config: Config instance
        
    Returns:
        Tuple of (tables_exist, has_data)
    """
    try:
        conn = mysql.connector.connect(
            host=config.mysql_host,
            port=config.mysql_port,
            user=config.mysql_user,
            password=config.mysql_password,
            database=config.mysql_db,
        )
        cursor = conn.cursor()
        
        # Check if core tables exist
        cursor.execute("SHOW TABLES LIKE 'patients'")
        tables_exist = cursor.fetchone() is not None
        
        has_data = False
        if tables_exist:
            try:
                cursor.execute("SELECT COUNT(*) FROM patients")
                patient_count = cursor.fetchone()[0]
                has_data = patient_count > 0
            except Exception:
                has_data = False
        
        cursor.close()
        conn.close()
        
        return tables_exist, has_data
        
    except Exception as e:
        logger.warning("check_dummy_tables_failed", error=str(e))
        return False, False


def auto_create_dummy_tables_if_needed(config: Config, auto_create: bool = False) -> bool:
    """
    Automatically create dummy tables if they don't exist.
    
    Args:
        config: Config instance
        auto_create: If True, create tables without prompting
        
    Returns:
        True if tables exist or were created, False otherwise
    """
    tables_exist, has_data = check_dummy_tables_exist(config)
    
    if tables_exist and has_data:
        logger.info("dummy_tables_exist_with_data")
        return True
    
    if tables_exist and not has_data:
        logger.info("dummy_tables_exist_but_empty")
        if auto_create:
            return _create_dummy_data(config)
        return False
    
    # Tables don't exist
    logger.info("dummy_tables_not_found")
    if auto_create:
        return _create_dummy_data(config)
    return False


def _create_dummy_data(config: Config) -> bool:
    """Create dummy tables and data."""
    try:
        import subprocess
        import sys
        import os
        
        script_path = "scripts/create_dummy_clinical_trial_data.py"
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=".",
            env=env,
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info("dummy_tables_created_successfully")
            return True
        else:
            logger.error("dummy_tables_creation_failed", error=result.stderr)
            return False
            
    except Exception as e:
        logger.error("dummy_tables_creation_exception", error=str(e))
        return False

