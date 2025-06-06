from fastapi import APIRouter, HTTPException, Query, Depends
from bson import ObjectId
from bson.errors import InvalidId
from app.database.db import get_db
from typing import List
from app.models import (
    Student,
    StudentCreate,
    StudentWithIssuedBooks,
    IssuedBookResponse,
)

router = APIRouter(prefix="/students", tags=["Students"])

# Helpers
def student_helper(student) -> Student:
    return Student(
        id=str(student["_id"]),
        student_name=student["student_name"],
        email=student["email"]
    )

def issued_book_helper(doc) -> dict:
    return {
        "id": str(doc["_id"]),
        "book_id": doc["book_id"],
        "student_id": doc["student_id"],
        "issued_date": doc["issued_date"],
        "return_date": doc["return_date"],
        "is_returned": doc["is_returned"]
    }


# Create Student
@router.post("/", response_model=Student)
async def create_student(student: StudentCreate , db=Depends(get_db)):
    student_collection = db["student_collection"]
    result = await student_collection.insert_one(student.dict())
    created = await student_collection.find_one({"_id": result.inserted_id})
    return student_helper(created)


# Get All Students
@router.get("/", response_model=List[StudentWithIssuedBooks])
async def get_all_students(page: int = Query(1, ge=1),size: int = Query(10, ge=1, le=100), db=Depends(get_db)):
    student_collection = db["student_collection"]
    issued_collection = db["issued_collection"]
    skip = (page - 1) * size
    limit = size
    students_with_books = []

    async for student in student_collection.find().skip(skip).limit(limit):
        student_id_str = str(student["_id"])

        # Fetch issued books for this student
        issued_books = []
        async for doc in issued_collection.find({"student_id": student_id_str}):
            issued_books.append({
                "id": str(doc["_id"]),
                "book_id": doc["book_id"],
                "student_id": doc["student_id"],
                "issued_date": doc["issued_date"],
                "return_date": doc["return_date"],
                "is_returned": doc["is_returned"]
            })

        # Append student with books
        students_with_books.append(StudentWithIssuedBooks(
            id=student_id_str,
            student_name=student["student_name"],
            email=student["email"],
            issued_books=issued_books
        ))

    return students_with_books


# Get Student by ID with Issued Books
@router.get("/{student_id}", response_model=StudentWithIssuedBooks)
async def get_student_with_issued_books(student_id: str, db=Depends(get_db)):
    student_collection = db["student_collection"]
    issued_collection = db["issued_collection"]
    try:
        obj_id = ObjectId(student_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid student ID")

    student = await student_collection.find_one({"_id": obj_id})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get issued books
    books = []
    async for doc in issued_collection.find({"student_id": student_id}):
        books.append(issued_book_helper(doc))

    return StudentWithIssuedBooks(
        id=str(student["_id"]),
        student_name=student["student_name"],
        email=student["email"],
        issued_books=books
    )


# Update Student
@router.put("/{student_id}", response_model=Student)
async def update_student(student_id: str, data: StudentCreate, db=Depends(get_db)):
    student_collection = db["student_collection"]
    try:
        obj_id = ObjectId(student_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid student ID")

    result = await student_collection.update_one(
        {"_id": obj_id}, {"$set": data.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Student not updated")

    updated = await student_collection.find_one({"_id": obj_id})
    return student_helper(updated)


# Delete Student
@router.delete("/{student_id}")
async def delete_student(student_id: str, db=Depends(get_db)):
    student_collection = db["student_collection"]
    try:
        obj_id = ObjectId(student_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid student ID")
    
    result = await student_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Student not found")

    return {"message": "Student deleted"}


