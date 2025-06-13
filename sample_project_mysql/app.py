import mysql.connector

def connect():
    connection = mysql.connector.connect(
        host="localhost",
        user="admin",
        password="tester",
        database="testdb"
    )
    return connection

