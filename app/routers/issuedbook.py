from fastapi import APIRouter, HTTPException,Depends,Query
from bson import ObjectId
from bson.errors import InvalidId
from app.models import IssuedBook, IssuedBookResponse,UserRole
from app.database.db import issued_collection
from app.routers.user import require_roles

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
    new_issue = await issued_collection.insert_one(issue_dict)
    created = await issued_collection.find_one({"_id": new_issue.inserted_id})
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

# Update
@router.put("/{issued_id}", response_model=IssuedBookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def update_issued_book(issued_id: str, update_data: IssuedBook):
    try:
        obj_id = ObjectId(issued_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid ID")

    update_dict = update_data.dict()
    result = await issued_collection.update_one({"_id": obj_id}, {"$set": update_dict})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No changes made or record not found")

    updated = await issued_collection.find_one({"_id": obj_id})
    return issued_book_helper(updated)

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
