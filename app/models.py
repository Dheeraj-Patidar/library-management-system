from pydantic import BaseModel, Field,EmailStr
from datetime import datetime
from typing import List
from enum import Enum

# Base Book model
class BookCreate(BaseModel):
    book_name: str
    author_id: str  
    category_id: str 


# Used for creating an author
class AuthorCreate(BaseModel):
    author_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
 

# Full author with books nested inside
class BookInAuthor(BaseModel):
    id : str
    books : List[BookCreate]


# Author for DB response (no books)
class AuthorDB(AuthorCreate):
    id: str 

    class Config:
        populate_by_name = True

BookInAuthor.update_forward_refs()

class Category(BaseModel):
    category_name: str
    
    class Config:
        populate_by_name = True
        

class CategoryDb(Category):
    id:str 

    class Config:
        populate_by_name = True


class BookResponse(BookCreate):
    id: str 

    class Config:
        populate_by_name = True


# Base IssuedBook model
class IssuedBook(BaseModel):
    book_id: str
    student_id: str
    issued_date: datetime = Field(default_factory=datetime.utcnow)
    return_date: datetime
    is_returned: bool = False

# Response model with _id
class IssuedBookResponse(IssuedBook):
    id: str

    class Config:
        populate_by_name = True

# Student base model
class Student(BaseModel):
    id: str
    student_name: str
    email: str

# Student create model
class StudentCreate(BaseModel):
    student_name: str
    email: str

# Response model with issued books
class StudentWithIssuedBooks(StudentCreate):
    id: str
    issued_books: List[IssuedBookResponse]

StudentWithIssuedBooks.update_forward_refs()


#  issued book model
class IssuedBook(BaseModel):
    book_id: str
    student_id: str
    issued_date: datetime = Field(default_factory=datetime.utcnow)
    return_date: datetime
    is_returned: bool = False


# issued book response
class IssuedBookResponse(IssuedBook):
    id: str 

    class Config:
        populate_by_name = True

# user roles model
class UserRole(str, Enum):
    student = "student"
    librarian = "librarian"
    author = "author"
    admin = "admin"


# user base model
class User(BaseModel):
    username: str
    email:EmailStr
    password: str
    role:UserRole

# user create model
class CreateUser(User):
    pass

# user response model
class UserResponse(User):
    id: str

    class Config:
        populate_by_name = True

# user update model
class UpdateUser(User):
    pass

