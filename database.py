"""
Database utilities for the Universal API server.

This module provides thread-safe SQLite database access.
"""

import sqlite3
import threading
import os
from contextlib import contextmanager

# Thread-local storage for database connections
local = threading.local()

class Database:
    """Thread-safe SQLite database manager."""
    
    def __init__(self, db_path):
        """Initialize the database manager."""
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema."""
        # Ensure the directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS instances (
                id TEXT PRIMARY KEY,
                created_at TIMESTAMP,
                last_used TIMESTAMP,
                message_count INTEGER,
                history_size INTEGER,
                tool_names TEXT
            )
            ''')
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Get a thread-local database connection."""
        if not hasattr(local, 'conn') or local.conn is None:
            local.conn = sqlite3.connect(self.db_path)
            local.conn.row_factory = sqlite3.Row
        
        try:
            yield local.conn
        except Exception as e:
            local.conn.rollback()
            raise e
    
    def close(self):
        """Close all database connections."""
        if hasattr(local, 'conn') and local.conn is not None:
            local.conn.close()
            local.conn = None

# Global database instance
_db_instance = None

def init_db(db_path):
    """Initialize the database."""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path)
    return _db_instance

def get_db():
    """Get the database instance."""
    global _db_instance
    if _db_instance is None:
        # Default fallback for tests/development - use an in-memory database
        # This ensures we never raise the RuntimeError
        _db_instance = Database(":memory:")
    return _db_instance 