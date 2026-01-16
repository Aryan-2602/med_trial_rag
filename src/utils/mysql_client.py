"""MySQL client for SAS data queries."""

import os
from contextlib import contextmanager
from typing import Any

try:
    import mysql.connector
    from mysql.connector import Error
    from mysql.connector.cursor import MySQLCursorDict
except ImportError:
    mysql = None
    Error = None
    MySQLCursorDict = None

from src.utils.config import Config
from src.utils.logging import get_logger

logger = get_logger(__name__)


class MySQLClient:
    """MySQL client for querying SAS data."""

    def __init__(self, config: Config | None = None):
        """
        Initialize MySQL client.

        Args:
            config: Config instance (uses Config.from_env() if None)
        """
        self.config = config or Config.from_env()
        self._connection: Any | None = None
        
        if mysql is None:
            raise ImportError("mysql-connector-python not installed. Install with: pip install mysql-connector-python")

    def _get_connection_params(self) -> dict[str, Any]:
        """Get connection parameters from config/environment."""
        return {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "database": os.getenv("MYSQL_DB", "cotrial_rag"),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
        }

    @contextmanager
    def get_connection(self):
        """
        Get a database connection (context manager).

        Yields:
            mysql.connector.connection: Database connection
        """
        params = self._get_connection_params()
        
        if not all([params["host"], params["database"], params["user"]]):
            raise ValueError("MySQL connection parameters not configured")

        conn = None
        try:
            conn = mysql.connector.connect(**params)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error("mysql_connection_error", error=str(e))
            raise
        finally:
            if conn and conn.is_connected():
                conn.close()

    def execute_query(self, query: str, params: tuple | None = None) -> list[dict[str, Any]]:
        """
        Execute a SQL query and return results as list of dicts.

        Args:
            query: SQL query string
            params: Query parameters (for parameterized queries)

        Returns:
            List of result rows as dictionaries
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params)
                results = cursor.fetchall()
                return results
            finally:
                cursor.close()

    def execute_query_with_limit(
        self, query: str, limit: int = 10, params: tuple | None = None
    ) -> list[dict[str, Any]]:
        """
        Execute a query with a limit.

        Args:
            query: SQL query string
            limit: Maximum number of results
            params: Query parameters

        Returns:
            List of result rows as dictionaries
        """
        # Add LIMIT if not already present
        query_upper = query.upper().strip()
        if "LIMIT" not in query_upper:
            query = f"{query.rstrip(';')} LIMIT {limit}"

        return self.execute_query(query, params)

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchall()  # Consume result
                cursor.close()
                return True
        except Exception as e:
            logger.error("mysql_connection_test_failed", error=str(e))
            return False

