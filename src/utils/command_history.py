from datetime import datetime
import json
from typing import List, Dict, Optional, Any

from src.dB.models import CommandEntry

class DatabaseCommandHistory:
    def __init__(self, db_config, db_connection=None):
        """
        Initialize database-backed command history functionality.
        
        Args:
            db_config (dict): Database connection configuration
        """
        self.db_config = db_config
        self.db = db_connection
        self.connection = None
        self.recording = True

    def connect(self):
        """Establish database connection"""
        if self.db is not None:
            self.connection = self.db.connection
            return True
        
        try:
            import mysql.connector
            self.connection = mysql.connector.connect(
                host=self.db_config['host'],
                user=self.db_config['user'],
                password=self.db_config['password'],
                database=self.db_config['database'],
                port=self.db_config['port']
            )
            return True
        except Exception as e:
            print(f"Error connecting to database: {e}")
            return False

    def start_recording(self):
        """Start recording command history"""
        self.recording = True
        print("Command history recording started")

    def stop_recording(self):
        """Stop recording command history"""
        self.recording = False
        print("Command history recording stopped")

    def add_command(self, command: str, status: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Add command to history with its execution status"""
        if not self.recording:
            return False
            
        if not self.connection:
            if not self.connect():
                return False
                
        try:
            cursor = self.connection.cursor()
            
            # Convert dictionary to JSON string
            context_json = json.dumps(context) if context else None
            
            query = """
            INSERT INTO command_history (command, execution_status, context)
            VALUES (%s, %s, %s)
            """
            cursor.execute(query, (command, status, context_json))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error adding command to history: {e}")
            return False

    def save_response(self, command: str, response: str) -> bool:
        """Save response for the most recent matching command"""
        if not self.connection:
            if not self.connect():
                return False
                
        try:
            cursor = self.connection.cursor()
            
            # Find the most recent command entry that matches
            find_query = """
            SELECT history_id FROM command_history
            WHERE command = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """
            cursor.execute(find_query, (command,))
            result = cursor.fetchone()
            
            if result:
                cmd_id = result[0]
                # Update the response for this command
                update_query = """
                UPDATE command_history
                SET response = %s
                WHERE history_id = %s
                """
                cursor.execute(update_query, (response, cmd_id))
                self.connection.commit()
                cursor.close()
                return True
            else:
                cursor.close()
                return False
        except Exception as e:
            print(f"Error saving response: {e}")
            return False

    def update_command_status(self, command: str, status: str) -> bool:
        """Update status of the most recent matching command"""
        if not self.connection:
            if not self.connect():
                return False
                
        try:
            cursor = self.connection.cursor()
            
            # Find the most recent command entry that matches
            find_query = """
            SELECT history_id FROM command_history
            WHERE command = %s
            ORDER BY timestamp DESC
            LIMIT 1
            """
            cursor.execute(find_query, (command,))
            result = cursor.fetchone()
            
            if result:
                cmd_id = result[0]
                # Update the status for this command
                update_query = """
                UPDATE command_history
                SET execution_status = %s
                WHERE history_id = %s
                """
                cursor.execute(update_query, (status, cmd_id))
                self.connection.commit()
                cursor.close()
                return True
            else:
                cursor.close()
                return False
        except Exception as e:
            print(f"Error updating command status: {e}")
            return False

    def get_history(self, limit: int = 20) -> List[CommandEntry]:
        """Get command history"""
        if not self.connection:
            if not self.connect():
                return []
                
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT history_id, command, response, timestamp, execution_status, context
            FROM command_history
            ORDER BY timestamp DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            
            history = []
            for row in results:
                history_id, command, response, timestamp, status, context_json = row
                
                # Parse context JSON if available
                context = None
                if context_json:
                    try:
                        context = json.loads(context_json)
                    except:
                        pass
                
                entry = CommandEntry(
                    history_id=history_id,
                    command=command,
                    response=response,
                    timestamp=timestamp,
                    execution_status=status,
                    context=context
                )
                history.append(entry)
            
            return history
        except Exception as e:
            print(f"Error getting command history: {e}")
            return []

    def search_history(self, search_term: str, limit: int = 20) -> List[CommandEntry]:
        """Search command history"""
        if not self.connection:
            if not self.connect():
                return []
                
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT history_id, command, response, timestamp, execution_status, context
            FROM command_history
            WHERE command LIKE %s OR response LIKE %s
            ORDER BY timestamp DESC
            LIMIT %s
            """
            search_pattern = f"%{search_term}%"
            cursor.execute(query, (search_pattern, search_pattern, limit))
            results = cursor.fetchall()
            cursor.close()
            
            history = []
            for row in results:
                history_id, command, response, timestamp, status, context_json = row
                
                # Parse context JSON if available
                context = None
                if context_json:
                    try:
                        context = json.loads(context_json)
                    except:
                        pass
                
                entry = CommandEntry(
                    history_id=history_id,
                    command=command,
                    response=response,
                    timestamp=timestamp,
                    execution_status=status,
                    context=context
                )
                history.append(entry)
            
            return history
        except Exception as e:
            print(f"Error searching command history: {e}")
            return []

    def clear_history(self) -> bool:
        """Clear command history"""
        if not self.connection:
            if not self.connect():
                return False
                
        try:
            cursor = self.connection.cursor()
            query = "TRUNCATE TABLE command_history"
            cursor.execute(query)
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"Error clearing command history: {e}")
            return False