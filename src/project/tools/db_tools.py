from crewai.tools import BaseTool
from typing import Type, Optional, Tuple
from pydantic import BaseModel, Field
import os
import random
import string
import re
import mysql.connector
import psycopg2
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from dotenv import load_dotenv

load_dotenv()
# === Credential Parsing Functions ===
def parse_credentials_from_text(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse username and password from generated credentials text"""
    try:
        # Pattern to match "Username: user_abc123, Password: MyPass123!"
        pattern = r"Username:\s*([^,\s]+).*?Password:\s*([^\s,\n]+)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        
        if match:
            username = match.group(1).strip()
            password = match.group(2).strip()
            return username, password
        
        # Alternative patterns for different formats
        patterns = [
            r"user[:\s]*([^,\s\n]+).*?pass[word]*[:\s]*([^\s,\n]+)",
            r"([a-zA-Z0-9_]+).*?([a-zA-Z0-9!@#$%^&*]{8,})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match and len(match.group(1)) > 3 and len(match.group(2)) > 6:
                return match.group(1).strip(), match.group(2).strip()
        
        return None, None
    except Exception:
        return None, None

def parse_database_type_from_text(text: str) -> Optional[str]:
    """Parse database type from detection text"""
    try:
        # Look for database type mentions
        db_types = ["mysql", "postgresql", "mongodb"]
        text_lower = text.lower()
        
        for db_type in db_types:
            if db_type in text_lower:
                return db_type
        
        return None
    except Exception:
        return None

# === Shared Core Functions ===
def detect_database(project_path: str) -> str:
    """Detect database type used in the project"""
    if not os.path.exists(project_path):
        return f"Error: Path does not exist - {project_path}"
    
    db_patterns = {
    "mysql": re.compile(r"mysql\.|MySQL|pymysql|mysql-connector|MySQLdb", re.IGNORECASE),
    "postgresql": re.compile(r"psycopg2|postgresql|pg_|postgres|PostgreSQL", re.IGNORECASE),
    "mongodb": re.compile(r"pymongo|mongodb|mongo|MongoDB|MongoClient", re.IGNORECASE),
}
    try:
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.json', '.env', '.txt')):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for db, pattern in db_patterns.items():
                                if pattern.search(content):
                                    return db
                    except Exception:
                        continue
        
        print(f"No known DB pattern found in {project_path}")
        return "unknown"
    except Exception as e:
        return f"Error scanning directory: {str(e)}"

def generate_secure_credentials():
    """Generate secure random username and password"""
    user = 'user_' + ''.join(random.choices(string.ascii_lowercase, k=6))
    password = ''.join(random.choices(string.ascii_letters + string.digits + '!@#$%^&*', k=12))
    return user, password

def get_db_connection_params(db_type: str):
    """Get database connection parameters from environment or defaults"""
    if db_type == "mysql":
        # DEBUG LINES - Remove after testing
        print("=== DEBUG: Environment Variables ===")
        print(f"MYSQL_ROOT_USER: '{os.getenv('MYSQL_ROOT_USER')}'")
        print(f"MYSQL_ROOT_PASSWORD: '{os.getenv('MYSQL_ROOT_PASSWORD')}'")
        print(f"MYSQL_HOST: '{os.getenv('MYSQL_HOST')}'")
        print(f"MYSQL_PORT: '{os.getenv('MYSQL_PORT')}'")
        print("===================================")
        
        return {
            "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_ROOT_USER", "ai_admin"),
            "password": os.getenv("MYSQL_ROOT_PASSWORD", "AIagent123!"),  # REPLACE THIS
        }
    elif db_type == "postgresql":
        return {
            "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),
            "port": int(os.getenv("POSTGRES_PORT", "5432")),
            "user": os.getenv("POSTGRES_ROOT_USER", "ai_admin"),
            "password": os.getenv("POSTGRES_ROOT_PASSWORD", "AIagent123!"),
            "dbname": os.getenv("POSTGRES_DB", "postgres")
        }
    elif db_type == "mongodb":
        return {
            "host": os.getenv("MONGO_HOST", "127.0.0.1"),
            "port": int(os.getenv("MONGO_PORT", "27017")),
            "username": os.getenv("MONGO_ROOT_USER", "ai_admin"),
            "password": os.getenv("MONGO_ROOT_PASSWORD", "AIagent123!"),
        }
    else:
        return {}

def create_local_db_user(db_type: str, user: str, password: str):
    """Create a user in local database instance with better error handling"""
    try:
        if db_type == "mysql":
            connection_params = get_db_connection_params(db_type)
            
            # Try different password scenarios for MySQL root
            connection_attempts = [
                connection_params,  # Environment password
                {**connection_params, "password": ""},  # Empty password
                {**connection_params, "password": "root"},  # Common default
                {**connection_params, "password": "AIagent123!"}, # Added by me
            ]
            
            conn = None
            last_error = None
            
            for params in connection_attempts:
                try:
                    conn = mysql.connector.connect(**params)
                    break
                except mysql.connector.Error as e:
                    last_error = e
                    continue
            
            if not conn:
                return f"Failed to connect to MySQL. Last error: {last_error}. Try setting MYSQL_ROOT_PASSWORD environment variable or ensure MySQL root access is configured."
            
            cursor = conn.cursor()
            
            # Check if user already exists and drop if necessary
            cursor.execute("SELECT User FROM mysql.user WHERE User = %s AND Host = 'localhost'", (user,))
            if cursor.fetchone():
                cursor.execute(f"DROP USER '{user}'@'localhost';")
            
            cursor.execute(f"CREATE USER '{user}'@'localhost' IDENTIFIED BY '{password}';")
            cursor.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{user}'@'localhost';")
            cursor.execute("FLUSH PRIVILEGES;")
            conn.commit()
            cursor.close()
            conn.close()
            return True
            
        elif db_type == "postgresql":
            connection_params = get_db_connection_params(db_type)
            
            connection_attempts = [
                connection_params,
                {**connection_params, "password": ""},
                {**connection_params, "password": "postgres"},
            ]
            
            conn = None
            last_error = None
            
            for params in connection_attempts:
                try:
                    conn = psycopg2.connect(**params)
                    break
                except psycopg2.Error as e:
                    last_error = e
                    continue
            
            if not conn:
                return f"Failed to connect to PostgreSQL. Last error: {last_error}. Try setting POSTGRES_ROOT_PASSWORD environment variable."
            
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if user exists and drop if necessary
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (user,))
            if cursor.fetchone():
                cursor.execute(f"DROP ROLE {user};")
            
            cursor.execute(f"CREATE ROLE {user} LOGIN PASSWORD '{password}';")
            cursor.execute(f"ALTER ROLE {user} CREATEDB;")
            cursor.close()
            conn.close()
            return True
            
        elif db_type == "mongodb":
            connection_params = get_db_connection_params(db_type)
            
            if connection_params.get("username") and connection_params.get("password"):
                connection_string = f"mongodb://{connection_params['username']}:{connection_params['password']}@{connection_params['host']}:{connection_params['port']}/"
            else:
                connection_string = f"mongodb://{connection_params['host']}:{connection_params['port']}/"
            
            try:
                client = MongoClient(connection_string)
                # Test connection
                client.admin.command('ping')
                
                db = client.admin
                try:
                    db.command("createUser", user, pwd=password, roles=[{"role": "readWriteAnyDatabase", "db": "admin"}])
                except OperationFailure as e:
                    if "already exists" in str(e):
                        # Drop and recreate user
                        db.command("dropUser", user)
                        db.command("createUser", user, pwd=password, roles=[{"role": "readWriteAnyDatabase", "db": "admin"}])
                    else:
                        raise
                client.close()
                return True
            except Exception as e:
                return f"MongoDB connection/operation failed: {str(e)}"
            
        return False
    except Exception as e:
        return f"Unexpected error: {str(e)}"

def inject_credentials(project_path: str, db_type: str, user: str, password: str):
    """Inject credentials into project configuration files"""
    try:
        env_path = os.path.join(project_path, ".env")
        
        # Create .env file with credentials
        env_content = f"""# Database Configuration - Auto Generated
DB_TYPE={db_type}
DB_HOST=localhost
DB_USER={user}
DB_PASSWORD={password}
"""
        
        # Append to existing .env or create new one
        if os.path.exists(env_path):
            with open(env_path, "a", encoding='utf-8') as f:
                f.write(f"\n{env_content}")
        else:
            with open(env_path, "w", encoding='utf-8') as f:
                f.write(env_content)
        
        # Inject into settings files
        injected_files = []
        for root, _, files in os.walk(project_path):
            for file in files:
                if file in ["settings.py", "config.py", "config.js"]:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "a", encoding='utf-8') as f:
                            if file.endswith(".py"):
                                f.write(f"\n# Auto-generated database credentials\nDB_USER = '{user}'\nDB_PASSWORD = '{password}'\nDB_TYPE = '{db_type}'\nDB_HOST = 'localhost'\n")
                            elif file.endswith(".js"):
                                f.write(f"\n// Auto-generated database credentials\nmodule.exports.DB_USER = '{user}';\nmodule.exports.DB_PASSWORD = '{password}';\nmodule.exports.DB_TYPE = '{db_type}';\n")
                        injected_files.append(file)
                    except Exception as e:
                        print(f"Warning: Could not write to {file_path}: {e}")
        
        return f"Successfully injected credentials into .env and {len(injected_files)} config files: {injected_files}"
    except Exception as e:
        return str(e)

# === Pydantic Schemas ===
class ProjectPathInput(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project source code folder")

class EmptyInput(BaseModel):
    """Schema for tools that don't require input parameters"""
    pass

class CredentialsInput(BaseModel):
    db_type: str = Field(..., description="The type of database (mysql, postgresql, mongodb)")

class InjectInput(BaseModel):
    project_path: str = Field(..., description="Project path")
    db_type: str = Field(..., description="Database type")
    user: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class CreateDBUserInput(BaseModel):
    db_type: str = Field(..., description="Database type")
    user: str = Field(..., description="Username")
    password: str = Field(..., description="Password")

class CreateDBUserFromContextInput(BaseModel):
    context_text: str = Field(..., description="Context text containing database type and credentials from previous tasks")

class InjectFromContextInput(BaseModel):
    project_path: str = Field(..., description="Project path")
    context_text: str = Field(..., description="Context text containing database type and credentials from previous tasks")

# === Tool Classes ===
class DetectDatabaseTool(BaseTool):
    name: str = "detect_database"
    description: str = "Detect the database used in the project source code (MySQL, PostgreSQL, or MongoDB)"
    args_schema: Type[BaseModel] = ProjectPathInput
    
    def _run(self, project_path: str) -> str:
        return detect_database(project_path)

class GenerateSecureCredentialsTool(BaseTool):
    name: str = "generate_secure_credentials"
    description: str = "Generate secure random username and password for database"
    args_schema: Type[BaseModel] = EmptyInput
    
    def _run(self, **kwargs) -> str:
        user, password = generate_secure_credentials()
        return f"Username: {user}, Password: {password}"

class CreateLocalDBUserTool(BaseTool):
    name: str = "create_local_db_user"
    description: str = "Create a user in the local MySQL/PostgreSQL/MongoDB instance"
    args_schema: Type[BaseModel] = CreateDBUserInput
    
    def _run(self, db_type: str, user: str, password: str) -> str:
        result = create_local_db_user(db_type, user, password)
        if result is True:
            return f"Successfully created user '{user}' for {db_type} database"
        else:
            return f"Error creating user: {result}"

class CreateLocalDBUserFromContextTool(BaseTool):
    name: str = "create_local_db_user_from_context"
    description: str = "Create a database user by parsing database type and credentials from previous task outputs"
    args_schema: Type[BaseModel] = CreateDBUserFromContextInput
    
    def _run(self, context_text: str) -> str:
        # Parse database type
        db_type = parse_database_type_from_text(context_text)
        if not db_type:
            return f"Error: Could not parse database type from context: {context_text[:200]}..."
        
        # Parse credentials
        user, password = parse_credentials_from_text(context_text)
        if not user or not password:
            return f"Error: Could not parse credentials from context. Expected format: 'Username: user_name, Password: password'"
        
        result = create_local_db_user(db_type, user, password)
        if result is True:
            return f"Successfully created user '{user}' for {db_type} database using context data"
        else:
            return f"Error creating user '{user}': {result}"

class InjectCredentialsTool(BaseTool):
    name: str = "inject_credentials"
    description: str = "Injects credentials into project files and .env"
    args_schema: Type[BaseModel] = InjectInput
    
    def _run(self, project_path: str, db_type: str, user: str, password: str) -> str:
        result = inject_credentials(project_path, db_type, user, password)
        if isinstance(result, str) and result.startswith("Successfully"):
            return result
        else:
            return f"Error injecting credentials: {result}"

class InjectCredentialsFromContextTool(BaseTool):
    name: str = "inject_credentials_from_context"
    description: str = "Inject credentials into project files by parsing database type and credentials from previous task outputs"
    args_schema: Type[BaseModel] = InjectFromContextInput
    
    def _run(self, project_path: str, context_text: str) -> str:
        # Parse database type
        db_type = parse_database_type_from_text(context_text)
        if not db_type:
            return f"Error: Could not parse database type from context"
        
        # Parse credentials
        user, password = parse_credentials_from_text(context_text)
        if not user or not password:
            return f"Error: Could not parse credentials from context"
        
        result = inject_credentials(project_path, db_type, user, password)
        if isinstance(result, str) and result.startswith("Successfully"):
            return f"Injected credentials for user '{user}' - {result}"
        else:
            return f"Error injecting credentials: {result}"
