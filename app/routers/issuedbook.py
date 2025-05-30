from fastapi import APIRouter, HTTPException,Depends,Query
from bson import ObjectId
from bson.errors import InvalidId
from app.models import IssuedBook, IssuedBookResponse,UserRole,IssuedBookUpdate
from app.database.db import issued_collection, book_collection
from app.routers.user import require_roles
from datetime import datetime,timedelta

router = APIRouter(prefix="/issued", tags=["IssuedBooks"])

# Helper to convert MongoDB doc to Pydantic
def issued_book_helper(doc) -> IssuedBookResponse:
    return IssuedBookResponse(
        id=str(doc["_id"]),
        book_id=doc["book_id"],
        student_id=doc["student_id"],
        issued_date=doc["issued_date"],
        return_date=doc["return_date"],
        is_returned=doc["is_returned"]
    )

# Create

@router.post("/", response_model=IssuedBookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def issue_book(issue_data: IssuedBook):
    issue_dict = issue_data.dict()
    issue_dict["issued_date"] = datetime.now()
    # Validate book_id
    try:
        book_obj_id = ObjectId(issue_dict["book_id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid book ID")

    # Check if book exists and is available
    book = await book_collection.find_one({"_id": book_obj_id})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not book.get("is_available", True):
        raise HTTPException(status_code=400, detail="Book is not available for issuing")

    # Set return date 7 days from now
    issue_dict["return_date"] = datetime.now() + timedelta(days=7)

    # Save issued book
    new_issue = await issued_collection.insert_one(issue_dict)
    created = await issued_collection.find_one({"_id": new_issue.inserted_id})

    # Mark book as unavailable
    await book_collection.update_one(
        {"_id": book_obj_id},
        {"$set": {"is_available": False}}
    )

    # Return response
    return issued_book_helper(created)

# Get All
@router.get("/", response_model=list[IssuedBookResponse], dependencies=[Depends(require_roles(UserRole.librarian))])
async def get_all_issued_books(page: int = Query(1, ge=1),size: int = Query(10, ge=1, le=100)):
    skip = (page - 1) * size
    limit = size
    books = []
    async for doc in issued_collection.find().skip(skip).limit(limit):
        books.append(issued_book_helper(doc))
    return books

# Get One
@router.get("/{issued_id}", response_model=IssuedBookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def get_issued_book(issued_id: str):
    try:
        obj_id = ObjectId(issued_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    doc = await issued_collection.find_one({"_id": obj_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Issued record not found")
    return issued_book_helper(doc)

#update
@router.put("/{issued_id}", response_model=IssuedBookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def update_issued_book(issued_id: str, update_data: IssuedBookUpdate):
    try:
        obj_id = ObjectId(issued_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid issued book ID")

    update_dict = update_data.dict(exclude_unset=True)

    result = await issued_collection.update_one({"_id": obj_id}, {"$set": update_dict})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Issued book not found")
    elif result.modified_count == 0:
        raise HTTPException(status_code=400, detail="No changes made")

    # Re-fetch the updated issued book record
    book = await issued_collection.find_one({"_id": obj_id})
    if not book:
        raise HTTPException(status_code=404, detail="Issued book not found after update")

    # Optionally update the book availability
    
    book_obj_id = ObjectId(book["book_id"])
    if update_dict.get("is_returned") == True:
        await book_collection.update_one(
            {"_id": book_obj_id},
            {"$set": {"is_available": True}}
            )
    else:
        await book_collection.update_one(
            {"_id": book_obj_id},
            {"$set": {"is_available": False}}
            )

    return issued_book_helper(book)

# Delete
@router.delete("/{issued_id}", dependencies=[Depends(require_roles(UserRole.librarian))])
async def delete_issued_book(issued_id: str):
    try:
        obj_id = ObjectId(issued_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    result = await issued_collection.delete_one({"_id": obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Issued record not found")
    return {"message": "Issued record deleted"}
