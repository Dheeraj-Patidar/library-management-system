from datetime import datetime

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.database.db import get_db  # make sure these are your MongoDB collections
from app.models import AuthorCreate, AuthorDB, BookCreate, BookInAuthor

router = APIRouter()


def author_helper(author) -> dict:
    return {
        "id": str(author["_id"]),
        "author_name": author["author_name"],
        "created_at": author["created_at"],
        "updated_at": author["updated_at"],
    }


#  Create Author
@router.post("/", response_model=AuthorDB)
async def create_author(author: AuthorCreate, db=Depends(get_db)):
    author_collection = db["author_collection"]
    author_dict = author.dict()
    new_author = await author_collection.insert_one(author_dict)
    created = await author_collection.find_one({"_id": new_author.inserted_id})
    return author_helper(created)


#  Get All Authors
@router.get("/", response_model=list[BookInAuthor])
async def get_all_authors(
    page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db=Depends(get_db)
):

    skip = (page - 1) * size

    authors_with_books = []
    author_collection = db["author_collection"]
    book_collection = db["book_collection"]
    async for author in author_collection.find().skip(skip).limit(size):
        author_id_str = str(author["_id"])

        # Fetch books for this author
        books_cursor = book_collection.find({"author_id": author_id_str})
        books = []
        async for book in books_cursor:
            books.append(
                BookCreate(
                    book_name=book["book_name"],
                    author_id=book["author_id"],
                    category_id=book["category_id"],
                )
            )

        # Build the full author-with-books response
        authors_with_books.append(
            BookInAuthor(
                id=author_id_str,
                author_name=author["author_name"],
                created_at=author["created_at"],
                updated_at=author["updated_at"],
                books=books,
            )
        )

    return authors_with_books


#  Get Single Author by ID


@router.get("/authors/{author_id}", response_model=BookInAuthor)
async def get_author_with_books(author_id: str, db=Depends(get_db)):
    author_collection = db["author_collection"]
    book_collection = db["book_collection"]
    try:
        author_obj_id = ObjectId(author_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid author ID")

    author = await author_collection.find_one({"_id": author_obj_id})
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    books_cursor = book_collection.find({"author_id": author_id})
    books = [
        BookCreate(
            book_name=book["book_name"],
            author_id=book["author_id"],
            category_id=book["category_id"],
        )
        async for book in books_cursor
    ]

    return BookInAuthor(
        id=str(author["_id"]),
        author_name=author["author_name"],
        created_at=author["created_at"],
        updated_at=author["updated_at"],
        books=books,
    )


#  Update Author
@router.put("/{author_id}", response_model=AuthorDB)
async def update_author(author_id: str, author_data: AuthorCreate, db=Depends(get_db)):
    author_collection = db["author_collection"]
    author_dict = author_data.dict()
    author_dict["updated_at"] = datetime.utcnow()
    result = await author_collection.update_one(
        {"_id": ObjectId(author_id)}, {"$set": author_dict}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Author not updated")
    updated_author = await author_collection.find_one({"_id": ObjectId(author_id)})
    return author_helper(updated_author)


#  Delete Author
@router.delete("/{author_id}")
async def delete_author(author_id: str, db=Depends(get_db)):
    author_collection = db["author_collection"]
    result = await author_collection.delete_one({"_id": ObjectId(author_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Author not found")
    return {"message": "Author deleted"}
