import mysql.connector
from mysql.connector import Error
import os
from .config import DB_CONFIG

class Database:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=DB_CONFIG['host'],
                user=DB_CONFIG['user'],
                password=DB_CONFIG['password'],
                database=DB_CONFIG['database'],
                port=DB_CONFIG['port']
            )
            print("Successfully connected to MySQL database")
        except Error as e:
            print(f"Error connecting to MySQL database: {e}")

    def execute_query(self, query, params=None):
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor
        except Error as e:
            print(f"Error executing query: {e}")
            return None

    def fetch_all(self, query, params=None):
        cursor = self.execute_query(query, params)
        if cursor:
            result = cursor.fetchall()
            cursor.close()
            return result
        return None

    def fetch_one(self, query, params=None):
        cursor = self.execute_query(query, params)
        if cursor:
            result = cursor.fetchone()
            cursor.close()
            return result
        return None

    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")

    def initialize_database(self):
        """Initialize the database with schema from schema.sql file"""
        try:
            # Updated path for schema.sql in the Db folder
            current_dir = os.path.dirname(os.path.abspath(__file__))
            schema_path = os.path.join(current_dir, 'schema.sql')
            
            # Read the schema.sql file
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            # Execute each statement individually with error handling
            for statement in schema_sql.split(';'):
                if statement.strip():
                    try:
                        self.execute_query(statement)
                    except Error as e:
                        print(f"Error executing statement: {e}")
                        print(f"Problematic statement: {statement}")
                        # Continue with next statement rather than stopping completely
                        continue
            
            print("Database initialization complete")
            return True
        except Error as e:
            print(f"Error initializing database: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error initializing database: {e}")
            return False