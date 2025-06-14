import mysql.connector

def connect():
    connection = mysql.connector.connect(
        host="localhost",
        user="ai_admin",
        password="AIagent123!",
        database="testdb"
    )
    return connection

