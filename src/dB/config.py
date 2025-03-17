from dotenv import load_dotenv
import os

project_root = os.path.dirname(os.path.dirname(__file__))

dotenv_path = os.path.join(project_root, 'config', '.env')

load_dotenv(dotenv_path)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),      
    'user': os.getenv('DB_USER', 'root'),         
    'password': os.getenv('DB_PASSWORD', ''),     
    'database': os.getenv('DB_DATABASE', 'nova'), 
    'port': int(os.getenv('DB_PORT', '3306'))
}