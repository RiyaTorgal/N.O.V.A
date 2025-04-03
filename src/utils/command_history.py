import mysql.connector
from datetime import datetime
from typing import List, Optional, Dict
from dataclasses import asdict
from src.dB.models import CommandEntry

class DatabaseCommandHistory:
    def __init__(self, db_config,db=None):
        """
        Initialize database-backed command history functionality.
        
        Args:
            db_config (dict): Database connection configuration
        """
        self.db_config = db_config
        self.connection = None
        self.cursor = None
        self.db = db
        self.is_recording = True 
        
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            self.cursor = self.connection.cursor(dictionary=True)
            return True
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}")
            return False
            
    def disconnect(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def start_recording(self):
        """Start recording command history"""
        self.is_recording = True
        return True
        
    def stop_recording(self):
        """Stop recording command history"""
        self.is_recording = False
        return True

    def add_command(self, command: str, status: str = "completed", context: Optional[Dict] = None) -> bool:
        """
        Add a command to history in the database.
        
        Args:
            command (str): Command to add to history
            status (str): Execution status (completed, failed, etc.)
            context (dict): Additional context information (will be stored as JSON)
            
        Returns:
            bool: Success status
        """
        if not command.strip():  # Don't add empty commands
            return False
            
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
                
            # Convert context to JSON string if provided
            context_json = None
            if context:
                import json
                context_json = json.dumps(context)
                
            query = """
            INSERT INTO command_history 
            (command, execution_status, context) 
            VALUES (%s, %s, %s)
            """
            
            self.cursor.execute(query, (command, status, context_json))
            self.connection.commit()
            return True
            
        except mysql.connector.Error as err:
            print(f"Error adding command to history: {err}")
            return False
            
    def get_history(self, limit: int = 10) -> List[CommandEntry]:
        """
        Get the most recent commands from history.
        
        Args:
            limit (int): Number of history items to retrieve
            
        Returns:
            List[CommandEntry]: List of recent commands
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
                
            query = """
            SELECT history_id, command, timestamp, execution_status, context
            FROM command_history
            ORDER BY timestamp DESC
            LIMIT %s
            """
            
            self.cursor.execute(query, (limit,))
            results = self.cursor.fetchall()
            
            # Convert dictionary results to CommandEntry objects
            entries = []
            for row in results:
                # Parse context JSON if it exists
                context = None
                if row['context']:
                    import json
                    context = json.loads(row['context'])
                
                entries.append(CommandEntry(
                    history_id=row['history_id'],
                    command=row['command'],
                    timestamp=row['timestamp'],
                    execution_status=row['execution_status'],
                    context=context
                ))
            
            return entries
            
        except mysql.connector.Error as err:
            print(f"Error retrieving command history: {err}")
            return []
            
    def search_history(self, search_term: str) -> List[CommandEntry]:
        """
        Search command history for a specific term.
        
        Args:
            search_term (str): Term to search for in commands
            
        Returns:
            List[CommandEntry]: List of matching commands
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
                
            query = """
            SELECT history_id, command, timestamp, execution_status, context
            FROM command_history
            WHERE command LIKE %s
            ORDER BY timestamp DESC
            """
            
            self.cursor.execute(query, (f"%{search_term}%",))
            results = self.cursor.fetchall()
            
            # Convert to CommandEntry objects
            entries = []
            for row in results:
                # Parse context JSON if it exists
                context = None
                if row['context']:
                    import json
                    context = json.loads(row['context'])
                
                entries.append(CommandEntry(
                    history_id=row['history_id'],
                    command=row['command'],
                    timestamp=row['timestamp'],
                    execution_status=row['execution_status'],
                    context=context
                ))
            
            return entries
            
        except mysql.connector.Error as err:
            print(f"Error searching command history: {err}")
            return []
    


    def get_command_by_id(self, history_id: int) -> Optional[CommandEntry]:
        """
        Get a specific command by its ID.
        
        Args:
            history_id (int): The ID of the command to retrieve
            
        Returns:
            Optional[CommandEntry]: The command entry if found, None otherwise
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
                
            query = """
            SELECT history_id, command, timestamp, execution_status, context
            FROM command_history
            WHERE history_id = %s
            """
            
            self.cursor.execute(query, (history_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
                
            # Parse context JSON if it exists
            context = None
            if row['context']:
                import json
                context = json.loads(row['context'])
            
            return CommandEntry(
                history_id=row['history_id'],
                command=row['command'],
                timestamp=row['timestamp'],
                execution_status=row['execution_status'],
                context=context
            )
            
        except mysql.connector.Error as err:
            print(f"Error retrieving command by ID: {err}")
            return None

    def update_command_status(self, command, status):
        """Update the status of a command in the history"""
        if not self.is_recording:
            return
            
        query = """
        UPDATE command_history 
        SET execution_status = %s 
        WHERE command = %s 
        ORDER BY timestamp DESC 
        LIMIT 1
        """
        self.db.execute_query(query, (status, command))

    def clear_history(self) -> bool:
        """
        Clear all command history.
        
        Returns:
            bool: Success status
        """
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
                
            query = "DELETE FROM command_history"
            self.cursor.execute(query)
            self.connection.commit()
            return True
            
        except mysql.connector.Error as err:
            print(f"Error clearing command history: {err}")
            return False