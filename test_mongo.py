import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

uri = os.getenv("MONGODB_URI")
database_name = os.getenv("MONGODB_DATABASE", "story_creator")

client = MongoClient(uri)
db = client[database_name]

print("Databases:", client.list_database_names())
print("Connected to:", db.name)