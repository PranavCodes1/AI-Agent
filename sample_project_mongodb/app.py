from pymongo import MongoClient

def connect():
    client = MongoClient("mongodb://localhost:27017/")
    db = client["testdb"]
    return db
