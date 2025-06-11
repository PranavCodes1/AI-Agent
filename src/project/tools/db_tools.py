import random
import string
import os
import re
import mysql.connector
import psycopg2
from pymongo import MongoClient

def generate_secure_credentials():
    user = 'user_' + ''.join(random.choices(string.ascii_lowercase, k=6))
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    return user, password

def create_local_db_user(db_type: str, user: str, password: str):
    try:
        if db_type == "mysql":
            conn = mysql.connector.connect(host="localhost", user="root", password="root")
            cursor = conn.cursor()
            cursor.execute(f"CREATE USER IF NOT EXISTS '{user}'@'%' IDENTIFIED BY '{password}';")
            cursor.execute(f"GRANT ALL PRIVILEGES ON *.* TO '{user}'@'%';")
            conn.commit()
            cursor.close()
            conn.close()
            return True

        elif db_type == "postgresql":
            conn = psycopg2.connect(host="localhost", user="postgres", password="root", dbname="postgres")
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{user}') THEN
                        CREATE ROLE {user} LOGIN PASSWORD '{password}';
                    END IF;
                END
                $$;
            """)
            cursor.close()
            conn.close()
            return True

        elif db_type == "mongodb":
            client = MongoClient("mongodb://localhost:27017/")
            db = client.admin
            db.command("createUser", user, pwd=password, roles=[{"role": "readWriteAnyDatabase", "db": "admin"}])
            return True

        return False
    except Exception as e:
        return str(e)

def inject_credentials(project_path: str, db_type: str, user: str, password: str):
    env_path = os.path.join(project_path, ".env")
    with open(env_path, "w") as f:
        f.write(f"DB_TYPE={db_type}\nDB_HOST=localhost\nDB_USER={user}\nDB_PASSWORD={password}\n")

    for root, _, files in os.walk(project_path):
        for file in files:
            if file in ["settings.py", "config.js"]:
                file_path = os.path.join(root, file)
                with open(file_path, "a") as f:
                    if file.endswith(".py"):
                        f.write(f"\nDB_USER = '{user}'\nDB_PASSWORD = '{password}'\n")
                    elif file.endswith(".js"):
                        f.write(f"\nmodule.exports.DB_USER = '{user}';\nmodule.exports.DB_PASSWORD = '{password}';\n")

def detect_database(project_path: str) -> str:
    db_patterns = {
        "mysql": re.compile(r"mysql\.|MySQL|pymysql", re.IGNORECASE),
        "postgresql": re.compile(r"psycopg2|postgresql|pg_", re.IGNORECASE),
        "mongodb": re.compile(r"pymongo|mongodb", re.IGNORECASE),
    }

    for root, _, files in os.walk(project_path):
        for file in files:
            if file.endswith(('.py', '.js', '.ts', '.json', '.env')):
                try:
                    with open(os.path.join(root, file), 'r') as f:
                        content = f.read()
                        for db, pattern in db_patterns.items():
                            if pattern.search(content):
                                return db
                except Exception:
                    continue

    return "unknown"

