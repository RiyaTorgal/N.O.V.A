# The import needs to be updated to import from the Db package
from src.dB.database import Database

def main():
    # Create a database connection
    db = Database()
    
    # Initialize the database with the schema
    success = db.initialize_database()
    
    if success:
        print("Database initialization complete!")
    else:
        print("Failed to initialize database.")
    
    # Close the connection
    db.close()

if __name__ == "__main__":
    main()