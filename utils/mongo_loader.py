from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()
more_mongo_uri = os.getenv("MORE_MONGO_URI")

def connect_mongo():
    mongo_uri = more_mongo_uri
    client = MongoClient(mongo_uri)
    db = client["monoh-dev"]
    return db
