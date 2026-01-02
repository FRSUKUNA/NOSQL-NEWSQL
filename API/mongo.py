from pymongo import MongoClient

MONGO_URI = "mongodb+srv://omarmesid_db_user:VEILLE123!@vt.2ed0h6t.mongodb.net/"

# ou Atlas :
# MONGO_URI = "mongodb+srv://user:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(MONGO_URI)
db = client["VT"]
collection = db["tables"]
collection_version = db["versions"]
