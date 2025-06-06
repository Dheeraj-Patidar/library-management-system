from fastapi import APIRouter, HTTPException,Depends,Query
from app.models import BookCreate,BookResponse,UserRole,BookUpdate
from bson import ObjectId, errors as bson_errors
from app.database.db import get_db
from app.routers.user import require_roles

router = APIRouter(prefix="/books",tags=['books'])


def parse_mongo_document(doc: dict) -> dict:
    doc = doc.copy()
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.post("/", response_model=BookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def create_book(book: BookCreate, db=Depends(get_db)):
    book_collection = db["book_collection"]
    book_dict = book.dict()
    new_book = await book_collection.insert_one(book_dict)
    created = await book_collection.find_one({"_id": new_book.inserted_id})
    return BookResponse(**parse_mongo_document(created))


@router.get("/", response_model=list[BookResponse], dependencies=[Depends(require_roles(UserRole.librarian))])
async def get_books(page: int = Query(1, ge=1),size: int = Query(10, ge=1, le=100), db=Depends(get_db)):
    book_collection = db["book_collection"]
    skip = (page - 1) * size
    limit = size
    books = []
    async for book in book_collection.find().skip(skip).limit(limit):
        books.append(BookResponse(**parse_mongo_document(book)))
    return books


@router.get("/{book_id}", response_model=BookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def get_book(book_id: str, db=Depends(get_db)):
    book_collection = db["book_collection"]
    book = await book_collection.find_one({"_id": ObjectId(book_id)})
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return BookResponse(**parse_mongo_document(book))


@router.put("/{book_id}", response_model=BookResponse, dependencies=[Depends(require_roles(UserRole.librarian))])
async def update_book(book_id: str, book_data: BookUpdate, db=Depends(get_db)):
    book_collection = db["book_collection"]
    update = book_data.dict()
    result = await book_collection.update_one(
        {"_id": ObjectId(book_id)},
        {"$set": update}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Book not updated")
    updated_book = await book_collection.find_one({"_id": ObjectId(book_id)})
    return BookResponse(**parse_mongo_document(updated_book))


@router.delete("/{book_id}", dependencies=[Depends(require_roles(UserRole.librarian))])
async def delete_book(book_id: str, db=Depends(get_db)):
    try:
        book_id = ObjectId(book_id)
    except bson_errors.InvalidId:
        raise HTTPException(status_code=400, detail="Invalid book ID")
    
    book_collection = db["book_collection"]
    result = await book_collection.delete_one({"_id": ObjectId(book_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted"}
