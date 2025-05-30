from fastapi import FastAPI
from app.routers import author, category, book, student, issuedbook,user, student_fine

app = FastAPI()

app.include_router(user.router)
app.include_router(author.router, prefix='/author', tags=['author'])
app.include_router(category.router)
app.include_router(book.router)
app.include_router(student.router)
app.include_router(issuedbook.router)
app.include_router(student_fine.router)