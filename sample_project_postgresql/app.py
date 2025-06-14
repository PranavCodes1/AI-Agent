import psycopg2

def connect():
    connection = psycopg2.connect(
        host="localhost",
        user="postgres", 
        password="postgres123",
        database="testdb"
    )
    return connection
