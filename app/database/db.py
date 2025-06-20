import os

from motor.motor_asyncio import AsyncIOMotorClient

# MONGO_URL = "mongodb://localhost:27017/library"
MONGO_URL = os.getenv("MONGODB_URI", "mongodb://localhost:27017/library")
client = AsyncIOMotorClient(MONGO_URL)
db = client.library  # database name
author_collection = db.get_collection("authors")
category_collection = db.get_collection("categories")
book_collection = db.get_collection("books")
issued_collection = db.get_collection("issuedbooks")
student_collection = db.get_collection("students")
user_collection = db.get_collection("users")
student_fine_collection = db.get_collection("student_fines")


async def get_db():
    print(
        "Connecting to the database........................................................................................."
    )
    return db
