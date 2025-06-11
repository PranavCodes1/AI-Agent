import mysql.connector

def connect():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="your_password",
        database="testdb"
    )
    return connection

